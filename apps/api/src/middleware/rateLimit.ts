import { Elysia } from "elysia";
import { logRateLimitViolation } from "./logging";

// Simple in-memory rate limiter
// Production-ready in-memory rate limiting
class RateLimiter {
  private requests: Map<string, { count: number; resetTime: number }> =
    new Map();
  private windowMs: number;
  private maxRequests: number;

  constructor(windowMs: number = 15 * 60 * 1000, maxRequests: number = 100) {
    this.windowMs = windowMs;
    this.maxRequests = maxRequests;

    // Cleanup expired entries every minute
    setInterval(() => this.cleanup(), 60 * 1000);
  }

  check(key: string): {
    allowed: boolean;
    remaining: number;
    resetTime: number;
  } {
    const now = Date.now();
    const resetTime = now + this.windowMs;
    const entry = this.requests.get(key);

    if (!entry || now > entry.resetTime) {
      // First request or window expired
      this.requests.set(key, { count: 1, resetTime });
      return {
        allowed: true,
        remaining: this.maxRequests - 1,
        resetTime,
      };
    }

    if (entry.count >= this.maxRequests) {
      // Rate limit exceeded
      return {
        allowed: false,
        remaining: 0,
        resetTime: entry.resetTime,
      };
    }

    // Increment count
    entry.count++;
    this.requests.set(key, entry);

    return {
      allowed: true,
      remaining: this.maxRequests - entry.count,
      resetTime: entry.resetTime,
    };
  }

  private cleanup() {
    const now = Date.now();
    for (const [key, entry] of this.requests.entries()) {
      if (now > entry.resetTime) {
        this.requests.delete(key);
      }
    }
  }
}

// Different rate limiters for different endpoints
const generalLimiter = new RateLimiter(15 * 60 * 1000, 100); // 100 requests per 15 minutes
const authLimiter = new RateLimiter(15 * 60 * 1000, 10); // 10 auth requests per 15 minutes
const uploadLimiter = new RateLimiter(60 * 60 * 1000, 20); // 20 uploads per hour
const orderCreationLimiter = new RateLimiter(60 * 60 * 1000, 30); // 30 order creations per hour
const adminLimiter = new RateLimiter(5 * 60 * 1000, 200); // 200 admin requests per 5 minutes
const passwordResetLimiter = new RateLimiter(60 * 60 * 1000, 3); // 3 password resets per hour
const bulkOperationLimiter = new RateLimiter(15 * 60 * 1000, 10); // 10 bulk operations per 15 minutes
const emailLimiter = new RateLimiter(60 * 60 * 1000, 10); // 10 email sends per hour

function getRateLimiter(path: string): RateLimiter {
  // Critical security endpoints - strictest limits
  if (
    path.includes("/auth/reset-password") ||
    path.includes("/auth/forgot-password")
  ) {
    return passwordResetLimiter;
  }

  // Authentication endpoints
  if (
    path.includes("/auth/") ||
    path.includes("/login") ||
    path.includes("/register")
  ) {
    return authLimiter;
  }

  // Order creation endpoints
  if (path.includes("/orders") && path.includes("POST")) {
    return orderCreationLimiter;
  }

  // Bulk operations
  if (path.includes("/bulk/")) {
    return bulkOperationLimiter;
  }

  // Email sending endpoints
  if (path.includes("/notifications/send") || path.includes("/email/")) {
    return emailLimiter;
  }

  // Admin endpoints - higher limits but still controlled
  if (path.includes("/admin/")) {
    return adminLimiter;
  }

  // File uploads
  if (path.includes("/upload")) {
    return uploadLimiter;
  }

  return generalLimiter;
}

export const rateLimiter = new Elysia({ name: "rateLimiter" }).onBeforeHandle(
  ({ request, set, headers }) => {
    // Skip rate limiting in development
    if (process.env.NODE_ENV === "development") {
      return;
    }

    const ip = headers["x-forwarded-for"] || headers["x-real-ip"] || "unknown";
    const path = new URL(request.url).pathname;
    const limiter = getRateLimiter(path);

    const result = limiter.check(ip as string);

    // Add rate limit headers
    set.headers["X-RateLimit-Limit"] = limiter["maxRequests"].toString();
    set.headers["X-RateLimit-Remaining"] = result.remaining.toString();
    set.headers["X-RateLimit-Reset"] = new Date(result.resetTime).toISOString();

    if (!result.allowed) {
      // Log rate limit violation
      logRateLimitViolation(ip as string, path, limiter["maxRequests"]);

      set.status = 429;
      return {
        success: false,
        error: "RATE_LIMIT_ERROR",
        message: "Too many requests, please try again later",
        retryAfter: Math.ceil((result.resetTime - Date.now()) / 1000),
      };
    }
  },
);
