import { Elysia, t } from "elysia";
import { getMetrics, getHealthMetrics } from "../services/monitoring";
import { authMiddleware } from "../middleware/auth";

export const monitoringRoutes = new Elysia({ prefix: "/monitoring" })
  // Public health check
  .get(
    "/health",
    async () => {
      const health = await getHealthMetrics();

      return {
        success: true,
        data: health,
      };
    },
    {
      detail: {
        tags: ["Monitoring"],
        summary: "Health check endpoint",
        description:
          "Returns system health status including database, memory, and performance metrics",
      },
    },
  )

  // Admin-only metrics endpoint
  .use(authMiddleware)
  .guard(
    {
      beforeHandle: ({ user, set }) => {
        if (!user || user.role !== "admin") {
          set.status = 403;
          return {
            success: false,
            error: "INSUFFICIENT_PERMISSIONS",
            message: "Admin access required",
          };
        }
      },
    },
    (app) =>
      app
        .get(
          "/metrics",
          () => {
            const metrics = getMetrics();

            return {
              success: true,
              data: metrics,
            };
          },
          {
            detail: {
              tags: ["Monitoring"],
              summary: "Application metrics",
              description:
                "Returns detailed application metrics including requests, errors, performance, and business metrics",
            },
          },
        )

        .get(
          "/metrics/summary",
          () => {
            const metrics = getMetrics();

            // Return summarized metrics
            return {
              success: true,
              data: {
                timestamp: metrics.timestamp,
                overview: {
                  totalRequests: metrics.requests.total,
                  totalErrors: metrics.errors.total,
                  errorRate: metrics.errors.errorRate,
                  averageResponseTime: metrics.performance.averageResponseTime,
                  slowRequestPercentage:
                    metrics.performance.slowRequestPercentage,
                },
                status: {
                  healthy:
                    metrics.errors.errorRate < 5 &&
                    metrics.performance.averageResponseTime < 1000,
                  warnings: [],
                },
              },
            };
          },
          {
            detail: {
              tags: ["Monitoring"],
              summary: "Metrics summary",
              description:
                "Returns a summarized view of key application metrics",
            },
          },
        )

        .get(
          "/metrics/performance",
          () => {
            const metrics = getMetrics();

            return {
              success: true,
              data: {
                timestamp: metrics.timestamp,
                performance: metrics.performance,
                requests: {
                  total: metrics.requests.total,
                  byStatus: metrics.requests.byStatus,
                  topPaths: Object.entries(metrics.requests.byPath)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 10)
                    .reduce(
                      (obj, [path, count]) => ({ ...obj, [path]: count }),
                      {},
                    ),
                },
                database: metrics.database,
              },
            };
          },
          {
            detail: {
              tags: ["Monitoring"],
              summary: "Performance metrics",
              description: "Returns detailed performance and database metrics",
            },
          },
        )

        .get(
          "/metrics/errors",
          () => {
            const metrics = getMetrics();

            return {
              success: true,
              data: {
                timestamp: metrics.timestamp,
                errors: metrics.errors,
                topErrorTypes: Object.entries(metrics.errors.byType)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 10)
                  .reduce(
                    (obj, [type, count]) => ({ ...obj, [type]: count }),
                    {},
                  ),
              },
            };
          },
          {
            detail: {
              tags: ["Monitoring"],
              summary: "Error metrics",
              description: "Returns detailed error metrics and recent errors",
            },
          },
        )

        .get(
          "/metrics/business",
          () => {
            const metrics = getMetrics();

            return {
              success: true,
              data: {
                timestamp: metrics.timestamp,
                business: metrics.business,
                auth: metrics.auth,
              },
            };
          },
          {
            detail: {
              tags: ["Monitoring"],
              summary: "Business metrics",
              description:
                "Returns business-related metrics including orders, revenue, and authentication",
            },
          },
        ),
  );

export default monitoringRoutes;
