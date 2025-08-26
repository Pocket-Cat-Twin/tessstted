import { Elysia } from "elysia";

// Request/Response logging middleware for debugging and monitoring
export const requestLogger = new Elysia({ name: "requestLogger" })
  .onRequest(({ request, set }) => {
    const startTime = Date.now();
    const requestId = Math.random().toString(36).substring(7);
    const url = new URL(request.url);
    
    // Store request metadata
    set.headers["x-request-id"] = requestId;
    
    // Log incoming request
    console.log(`🌐 [${requestId}] ${request.method} ${url.pathname}`, {
      query: url.search,
      userAgent: request.headers.get('user-agent')?.substring(0, 100),
      contentType: request.headers.get('content-type'),
      timestamp: new Date().toISOString(),
    });
    
    // Store start time for response timing
    (request as any).__startTime = startTime;
    (request as any).__requestId = requestId;
  })
  .onAfterHandle(({ request, response, set }) => {
    const requestId = (request as any).__requestId;
    const startTime = (request as any).__startTime;
    const duration = Date.now() - startTime;
    const url = new URL(request.url);
    
    // Determine response type and size
    let responseInfo: any = {};
    
    try {
      if (response && typeof response === 'object') {
        responseInfo.success = (response as any).success;
        responseInfo.hasData = !!(response as any).data;
        responseInfo.error = (response as any).error;
        
        // Don't log sensitive data
        if (url.pathname.includes('/auth/') || url.pathname.includes('/login')) {
          responseInfo.note = "Auth response - data not logged for security";
        }
      }
    } catch (e) {
      responseInfo.note = "Could not parse response for logging";
    }
    
    console.log(`✅ [${requestId}] ${request.method} ${url.pathname} - ${set.status || 200} (${duration}ms)`, {
      duration,
      status: set.status || 200,
      ...responseInfo,
    });
  })
  .onError(({ request, error, code }) => {
    const requestId = (request as any).__requestId;
    const startTime = (request as any).__startTime;
    const duration = startTime ? Date.now() - startTime : 0;
    const url = new URL(request.url);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    console.error(`❌ [${requestId}] ${request.method} ${url.pathname} - ERROR (${duration}ms)`, {
      error: errorMessage,
      code,
      duration,
    });
  });

// Health monitoring helper
export class ApiHealthMonitor {
  private static requests: Map<string, { count: number; errors: number; avgResponseTime: number }> = new Map();
  private static startTime = Date.now();
  
  static recordRequest(endpoint: string, responseTime: number, isError: boolean = false) {
    const current = this.requests.get(endpoint) || { count: 0, errors: 0, avgResponseTime: 0 };
    
    current.count++;
    if (isError) current.errors++;
    current.avgResponseTime = ((current.avgResponseTime * (current.count - 1)) + responseTime) / current.count;
    
    this.requests.set(endpoint, current);
  }
  
  static getHealthStats() {
    const uptime = Date.now() - this.startTime;
    const endpoints: any[] = [];
    
    for (const [endpoint, stats] of this.requests) {
      endpoints.push({
        endpoint,
        requests: stats.count,
        errors: stats.errors,
        errorRate: stats.count > 0 ? (stats.errors / stats.count) * 100 : 0,
        avgResponseTime: Math.round(stats.avgResponseTime),
        healthStatus: stats.errors / stats.count > 0.05 ? 'warning' : 'healthy',
      });
    }
    
    return {
      uptime,
      totalRequests: Array.from(this.requests.values()).reduce((sum, s) => sum + s.count, 0),
      totalErrors: Array.from(this.requests.values()).reduce((sum, s) => sum + s.errors, 0),
      endpoints,
      memory: process.memoryUsage(),
      timestamp: new Date().toISOString(),
    };
  }
  
  static reset() {
    this.requests.clear();
    this.startTime = Date.now();
  }
}

// Enhanced request logger with monitoring
export const enhancedRequestLogger = new Elysia({ name: "enhancedRequestLogger" })
  .use(requestLogger)
  .onAfterHandle(({ request, set }) => {
    const startTime = (request as any).__startTime;
    const duration = startTime ? Date.now() - startTime : 0;
    const url = new URL(request.url);
    const statusCode = typeof set.status === 'number' ? set.status : 200;
    const isError = statusCode >= 400;
    
    // Record for health monitoring
    ApiHealthMonitor.recordRequest(url.pathname, duration, isError);
  });