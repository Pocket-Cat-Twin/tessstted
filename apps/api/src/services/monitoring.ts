import { createMetricsLogger, createJobLogger } from "./logger";
import { db } from "@lolita-fashion/db";

// In-memory metrics storage (for production, use proper metrics store like Prometheus)
interface MetricStore {
  requests: {
    total: number;
    byStatus: Map<number, number>;
    byPath: Map<string, number>;
    byMethod: Map<string, number>;
  };
  performance: {
    averageResponseTime: number;
    slowRequests: number;
    totalRequestTime: number;
    requestCount: number;
  };
  errors: {
    total: number;
    byType: Map<string, number>;
    recent: Array<{ timestamp: Date; error: string; path: string }>;
  };
  database: {
    connections: number;
    queries: number;
    slowQueries: number;
  };
  auth: {
    logins: number;
    failures: number;
    registrations: number;
  };
  business: {
    orders: number;
    subscriptions: number;
    revenue: number;
  };
}

const metrics: MetricStore = {
  requests: {
    total: 0,
    byStatus: new Map(),
    byPath: new Map(),
    byMethod: new Map(),
  },
  performance: {
    averageResponseTime: 0,
    slowRequests: 0,
    totalRequestTime: 0,
    requestCount: 0,
  },
  errors: {
    total: 0,
    byType: new Map(),
    recent: [],
  },
  database: {
    connections: 0,
    queries: 0,
    slowQueries: 0,
  },
  auth: {
    logins: 0,
    failures: 0,
    registrations: 0,
  },
  business: {
    orders: 0,
    subscriptions: 0,
    revenue: 0,
  },
};

const metricsLogger = createMetricsLogger();

// Request metrics
export const recordRequest = (
  method: string,
  path: string,
  statusCode: number,
  duration: number,
) => {
  metrics.requests.total++;

  // Update status code metrics
  const currentStatusCount = metrics.requests.byStatus.get(statusCode) || 0;
  metrics.requests.byStatus.set(statusCode, currentStatusCount + 1);

  // Update path metrics
  const currentPathCount = metrics.requests.byPath.get(path) || 0;
  metrics.requests.byPath.set(path, currentPathCount + 1);

  // Update method metrics
  const currentMethodCount = metrics.requests.byMethod.get(method) || 0;
  metrics.requests.byMethod.set(method, currentMethodCount + 1);

  // Update performance metrics
  metrics.performance.totalRequestTime += duration;
  metrics.performance.requestCount++;
  metrics.performance.averageResponseTime =
    metrics.performance.totalRequestTime / metrics.performance.requestCount;

  if (duration > 1000) {
    metrics.performance.slowRequests++;
  }
};

// Error metrics
export const recordError = (errorType: string, path: string, error: string) => {
  metrics.errors.total++;

  const currentErrorCount = metrics.errors.byType.get(errorType) || 0;
  metrics.errors.byType.set(errorType, currentErrorCount + 1);

  // Keep only last 100 errors
  metrics.errors.recent.push({
    timestamp: new Date(),
    error,
    path,
  });

  if (metrics.errors.recent.length > 100) {
    metrics.errors.recent.shift();
  }
};

// Database metrics
export const recordDatabaseQuery = (duration: number) => {
  metrics.database.queries++;

  if (duration > 100) {
    // Slow query threshold: 100ms
    metrics.database.slowQueries++;
  }
};

// Auth metrics
export const recordLogin = (success: boolean) => {
  if (success) {
    metrics.auth.logins++;
  } else {
    metrics.auth.failures++;
  }
};

export const recordRegistration = () => {
  metrics.auth.registrations++;
};

// Business metrics
export const recordOrder = (amount: number) => {
  metrics.business.orders++;
  metrics.business.revenue += amount;
};

export const recordSubscription = () => {
  metrics.business.subscriptions++;
};

// Get current metrics
export const getMetrics = () => {
  return {
    timestamp: new Date().toISOString(),
    requests: {
      total: metrics.requests.total,
      byStatus: Object.fromEntries(metrics.requests.byStatus),
      byPath: Object.fromEntries(metrics.requests.byPath),
      byMethod: Object.fromEntries(metrics.requests.byMethod),
    },
    performance: {
      averageResponseTime: Math.round(metrics.performance.averageResponseTime),
      slowRequests: metrics.performance.slowRequests,
      slowRequestPercentage:
        metrics.performance.requestCount > 0
          ? Math.round(
              (metrics.performance.slowRequests /
                metrics.performance.requestCount) *
                100,
            )
          : 0,
    },
    errors: {
      total: metrics.errors.total,
      byType: Object.fromEntries(metrics.errors.byType),
      errorRate:
        metrics.requests.total > 0
          ? Math.round((metrics.errors.total / metrics.requests.total) * 100)
          : 0,
      recent: metrics.errors.recent.slice(-10), // Last 10 errors
    },
    database: {
      queries: metrics.database.queries,
      slowQueries: metrics.database.slowQueries,
      slowQueryPercentage:
        metrics.database.queries > 0
          ? Math.round(
              (metrics.database.slowQueries / metrics.database.queries) * 100,
            )
          : 0,
    },
    auth: {
      logins: metrics.auth.logins,
      failures: metrics.auth.failures,
      registrations: metrics.auth.registrations,
      failureRate:
        metrics.auth.logins + metrics.auth.failures > 0
          ? Math.round(
              (metrics.auth.failures /
                (metrics.auth.logins + metrics.auth.failures)) *
                100,
            )
          : 0,
    },
    business: {
      orders: metrics.business.orders,
      subscriptions: metrics.business.subscriptions,
      revenue: metrics.business.revenue,
    },
  };
};

// Health check
export const getHealthMetrics = async () => {
  const startTime = Date.now();

  try {
    // Test database connection
    const dbHealth = await testDatabaseHealth();
    const dbResponseTime = Date.now() - startTime;

    // Memory usage
    const memoryUsage = process.memoryUsage();

    // Uptime
    const uptime = process.uptime();

    return {
      status: "healthy",
      timestamp: new Date().toISOString(),
      uptime: Math.round(uptime),
      database: {
        status: dbHealth ? "connected" : "disconnected",
        responseTime: dbResponseTime,
      },
      memory: {
        used: Math.round(memoryUsage.heapUsed / 1024 / 1024), // MB
        total: Math.round(memoryUsage.heapTotal / 1024 / 1024), // MB
        external: Math.round(memoryUsage.external / 1024 / 1024), // MB
      },
      performance: {
        averageResponseTime: Math.round(
          metrics.performance.averageResponseTime,
        ),
        errorRate:
          metrics.requests.total > 0
            ? Math.round((metrics.errors.total / metrics.requests.total) * 100)
            : 0,
      },
    };
  } catch (error) {
    return {
      status: "unhealthy",
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
};

// Test database health
const testDatabaseHealth = async (): Promise<boolean> => {
  try {
    // Simple query to test database
    await db.query.users.findFirst();
    return true;
  } catch (error) {
    metricsLogger.error("Database health check failed", { error });
    return false;
  }
};

// Periodic metrics logging
const logMetricsSummary = () => {
  const currentMetrics = getMetrics();

  metricsLogger.info(
    {
      summary: {
        requests: currentMetrics.requests.total,
        errors: currentMetrics.errors.total,
        averageResponseTime: currentMetrics.performance.averageResponseTime,
        errorRate: currentMetrics.errors.errorRate,
        slowRequestPercentage: currentMetrics.performance.slowRequestPercentage,
      },
    },
    "Metrics summary",
  );

  // Alert on high error rates
  if (currentMetrics.errors.errorRate > 5) {
    metricsLogger.warn(
      {
        errorRate: currentMetrics.errors.errorRate,
        totalErrors: currentMetrics.errors.total,
        totalRequests: currentMetrics.requests.total,
      },
      "High error rate detected",
    );
  }

  // Alert on slow response times
  if (currentMetrics.performance.averageResponseTime > 1000) {
    metricsLogger.warn(
      {
        averageResponseTime: currentMetrics.performance.averageResponseTime,
        slowRequestPercentage: currentMetrics.performance.slowRequestPercentage,
      },
      "Slow response times detected",
    );
  }
};

// Start periodic monitoring
export const startMetricsMonitoring = () => {
  const jobLogger = createJobLogger("metrics-monitoring");

  jobLogger.info("Starting metrics monitoring");

  // Log metrics every 5 minutes
  setInterval(
    () => {
      logMetricsSummary();
    },
    5 * 60 * 1000,
  );

  // Reset daily metrics at midnight
  setInterval(() => {
    const now = new Date();
    if (now.getHours() === 0 && now.getMinutes() === 0) {
      resetDailyMetrics();
    }
  }, 60 * 1000); // Check every minute
};

// Reset daily metrics
const resetDailyMetrics = () => {
  const jobLogger = createJobLogger("metrics-reset");
  jobLogger.info("Resetting daily metrics");

  // Archive current metrics before reset
  const currentMetrics = getMetrics();
  metricsLogger.info(currentMetrics, "Daily metrics archive");

  // Reset counters
  metrics.requests.total = 0;
  metrics.requests.byStatus.clear();
  metrics.requests.byPath.clear();
  metrics.requests.byMethod.clear();

  metrics.performance.averageResponseTime = 0;
  metrics.performance.slowRequests = 0;
  metrics.performance.totalRequestTime = 0;
  metrics.performance.requestCount = 0;

  metrics.errors.total = 0;
  metrics.errors.byType.clear();
  metrics.errors.recent = [];

  metrics.database.queries = 0;
  metrics.database.slowQueries = 0;

  metrics.auth.logins = 0;
  metrics.auth.failures = 0;
  metrics.auth.registrations = 0;

  // Keep business metrics as cumulative
};

export default {
  recordRequest,
  recordError,
  recordDatabaseQuery,
  recordLogin,
  recordRegistration,
  recordOrder,
  recordSubscription,
  getMetrics,
  getHealthMetrics,
  startMetricsMonitoring,
};
