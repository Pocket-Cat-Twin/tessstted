import { Elysia } from "elysia";
import {
  createRequestLogger,
  logApiMetrics,
  logSecurityEvent,
} from "../services/logger";
import { recordRequest, recordError } from "../services/monitoring";
import { randomUUID } from "crypto";

// Request logging middleware
export const loggingMiddleware = new Elysia({ name: "logging" })
  .derive(({ request, set }) => {
    // Generate unique request ID
    const requestId = randomUUID();

    // Extract request metadata
    const method = request.method;
    const url = new URL(request.url);
    const path = url.pathname;
    const userAgent = request.headers.get("user-agent") || "unknown";
    const ip =
      request.headers.get("x-forwarded-for") ||
      request.headers.get("x-real-ip") ||
      "unknown";

    // Create request-specific logger
    const requestLogger = createRequestLogger(
      requestId,
      method,
      path,
      userAgent,
    );

    // Log incoming request
    requestLogger.info(
      {
        ip,
        query: Object.fromEntries(url.searchParams),
        headers: {
          contentType: request.headers.get("content-type"),
          authorization: request.headers.get("authorization")
            ? "[REDACTED]"
            : undefined,
          accept: request.headers.get("accept"),
        },
      },
      `Incoming ${method} ${path}`,
    );

    // Store start time for performance measurement
    const startTime = Date.now();

    // Add request ID to response headers for tracing
    set.headers["x-request-id"] = requestId;

    return {
      requestId,
      requestLogger,
      startTime,
      requestIp: ip,
    };
  })
  .onAfterHandle(
    ({ response, requestLogger, startTime, request, requestIp: _requestIp }) => {
      const duration = Date.now() - startTime;
      const method = request.method;
      const url = new URL(request.url);
      const path = url.pathname;

      // Determine status code
      let statusCode = 200;
      if (response && typeof response === "object" && "status" in response) {
        statusCode = response.status as number;
      }

      // Log response
      requestLogger.info(
        {
          statusCode,
          duration,
          responseSize: response ? JSON.stringify(response).length : 0,
        },
        `Response ${method} ${path} - ${statusCode} (${duration}ms)`,
      );

      // Log API metrics
      logApiMetrics(method, path, statusCode, duration);

      // Record metrics for monitoring
      recordRequest(method, path, statusCode, duration);

      // Log slow requests
      if (duration > 1000) {
        requestLogger.warn(
          {
            duration,
            threshold: 1000,
          },
          `Slow request: ${method} ${path} took ${duration}ms`,
        );
      }
    },
  )
  .onError(({ error, code, requestLogger, startTime, request, requestIp }) => {
    const duration = startTime ? Date.now() - startTime : 0;
    const method = request.method;
    const url = new URL(request.url);
    const path = url.pathname;

    // Determine status code from error
    let statusCode = 500;
    switch (code) {
      case "VALIDATION":
      case "PARSE":
        statusCode = 400;
        break;
      case "NOT_FOUND":
        statusCode = 404;
        break;
      case "INVALID_COOKIE_SIGNATURE":
        statusCode = 401;
        break;
      case "INVALID_FILE_TYPE":
        statusCode = 403;
        break;
    }

    // Log error with full context
    const errorMessage = error && typeof error === 'object' && 'message' in error ? error.message : String(error);
    const errorStack = error && typeof error === 'object' && 'stack' in error ? error.stack : undefined;
    
    if (requestLogger) {
      requestLogger.error(
        {
          errorCode: code,
          errorMessage,
          errorStack,
          statusCode,
          duration,
        },
        `Error in ${method} ${path}: ${errorMessage}`,
      );
    }

    // Log API metrics for errors
    logApiMetrics(method, path, statusCode, duration);

    // Record error metrics for monitoring
    recordError(String(code), path, errorMessage);
    recordRequest(method, path, statusCode, duration);

    // Log security events for suspicious patterns
    if (statusCode === 401 || statusCode === 403) {
      logSecurityEvent("authentication_failure", undefined, requestIp, {
        method,
        path,
        errorMessage,
      });
    }

    // Log potential attacks
    if (
      path.includes("..") ||
      path.includes("<script>") ||
      path.includes("union select")
    ) {
      logSecurityEvent("suspicious_request", undefined, requestIp, {
        method,
        path,
        reason: "potential_attack_pattern",
      });
    }
  });

// Rate limit violation logging
export const logRateLimitViolation = (
  ip: string,
  path: string,
  limit: number,
) => {
  logSecurityEvent("rate_limit_violation", undefined, ip, {
    path,
    limit,
    reason: "too_many_requests",
  });
};

export default loggingMiddleware;
