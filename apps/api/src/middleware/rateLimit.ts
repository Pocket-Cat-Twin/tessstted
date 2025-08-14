import { Elysia } from 'elysia';

// Simple in-memory rate limiter
// In production, you'd want to use Redis or similar
class RateLimiter {
  private requests: Map<string, { count: number; resetTime: number }> = new Map();
  private windowMs: number;
  private maxRequests: number;

  constructor(windowMs: number = 15 * 60 * 1000, maxRequests: number = 100) {
    this.windowMs = windowMs;
    this.maxRequests = maxRequests;
    
    // Cleanup expired entries every minute
    setInterval(() => this.cleanup(), 60 * 1000);
  }

  check(key: string): { allowed: boolean; remaining: number; resetTime: number } {
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

function getRateLimiter(path: string): RateLimiter {
  if (path.includes('/auth/') || path.includes('/login') || path.includes('/register')) {
    return authLimiter;
  }
  if (path.includes('/upload')) {
    return uploadLimiter;
  }
  return generalLimiter;
}

export const rateLimiter = new Elysia({ name: 'rateLimiter' })
  .onBeforeHandle(({ request, set, headers }) => {
    // Skip rate limiting in development
    if (process.env.NODE_ENV === 'development') {
      return;
    }

    const ip = headers['x-forwarded-for'] || headers['x-real-ip'] || 'unknown';
    const path = new URL(request.url).pathname;
    const limiter = getRateLimiter(path);
    
    const result = limiter.check(ip as string);
    
    // Add rate limit headers
    set.headers['X-RateLimit-Limit'] = limiter['maxRequests'].toString();
    set.headers['X-RateLimit-Remaining'] = result.remaining.toString();
    set.headers['X-RateLimit-Reset'] = new Date(result.resetTime).toISOString();

    if (!result.allowed) {
      set.status = 429;
      return {
        success: false,
        error: 'RATE_LIMIT_ERROR',
        message: 'Too many requests, please try again later',
        retryAfter: Math.ceil((result.resetTime - Date.now()) / 1000),
      };
    }
  });