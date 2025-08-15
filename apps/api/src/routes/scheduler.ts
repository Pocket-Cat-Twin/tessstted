import { Elysia, t } from "elysia";
import { requireAdmin } from "../middleware/auth";
import { NotFoundError, ValidationError } from "../middleware/error";
import { schedulerService } from "../services/scheduler";

export const schedulerRoutes = new Elysia({ prefix: "/scheduler" })

  // Admin-only routes
  .use(requireAdmin)

  // Get scheduler status and job information
  .get(
    "/status",
    async () => {
      const jobs = schedulerService.getJobsStatus();

      return {
        success: true,
        data: {
          scheduler: {
            status: "running",
            totalJobs: jobs.length,
            jobs,
          },
          systemInfo: {
            uptime: process.uptime(),
            environment: process.env.NODE_ENV || "development",
            timestamp: new Date().toISOString(),
          },
        },
      };
    },
    {
      detail: {
        summary: "Get scheduler status (Admin)",
        description: "Get current status of scheduler and all registered jobs",
        tags: ["Scheduler"],
      },
    },
  )

  // Manually trigger storage expiration processing
  .post(
    "/jobs/storage-expirations",
    async () => {
      const result = await schedulerService.processStorageExpirations();

      return {
        success: true,
        message: "Storage expiration processing completed",
        data: { result },
      };
    },
    {
      detail: {
        summary: "Process storage expirations (Admin)",
        description:
          "Manually trigger storage expiration processing and notifications",
        tags: ["Scheduler"],
      },
    },
  )

  // Manually trigger subscription renewals
  .post(
    "/jobs/subscription-renewals",
    async () => {
      const result = await schedulerService.processSubscriptionRenewals();

      return {
        success: true,
        message: "Subscription renewal processing completed",
        data: { result },
      };
    },
    {
      detail: {
        summary: "Process subscription renewals (Admin)",
        description:
          "Manually trigger auto-renewal processing for subscriptions",
        tags: ["Scheduler"],
      },
    },
  )

  // Manually trigger data cleanup
  .post(
    "/jobs/cleanup",
    async () => {
      const result = await schedulerService.cleanupExpiredData();

      return {
        success: true,
        message: "Data cleanup completed",
        data: { result },
      };
    },
    {
      detail: {
        summary: "Cleanup expired data (Admin)",
        description:
          "Manually trigger cleanup of expired verification codes and sessions",
        tags: ["Scheduler"],
      },
    },
  )

  // Run any job by name
  .post(
    "/jobs/:jobName/run",
    async ({ params: { jobName } }) => {
      try {
        const result = await schedulerService.runJob(jobName);

        return {
          success: true,
          message: `Job "${jobName}" completed successfully`,
          data: { result },
        };
      } catch (error) {
        if (error instanceof Error && error.message.includes("not found")) {
          throw new NotFoundError(`Job "${jobName}" not found`);
        }
        throw error;
      }
    },
    {
      params: t.Object({
        jobName: t.String(),
      }),
      detail: {
        summary: "Run specific job (Admin)",
        description: "Manually execute a specific scheduled job by name",
        tags: ["Scheduler"],
      },
    },
  )

  // Get job execution history (mock implementation)
  .get(
    "/jobs/:jobName/history",
    async ({ params: { jobName }, query }) => {
      const limit = parseInt(query.limit) || 10;

      // In a real implementation, you would store job execution history in database
      // For now, return mock data
      const mockHistory = Array.from(
        { length: Math.min(limit, 5) },
        (_, i) => ({
          id: `exec_${Date.now()}_${i}`,
          jobName,
          status: Math.random() > 0.8 ? "error" : "success",
          message:
            Math.random() > 0.8
              ? "Job failed due to network error"
              : "Job completed successfully",
          executedAt: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
          duration: Math.floor(Math.random() * 5000) + 1000,
          data: {
            processed: Math.floor(Math.random() * 50),
            errors: Math.floor(Math.random() * 3),
          },
        }),
      );

      return {
        success: true,
        data: {
          history: mockHistory,
          pagination: {
            limit,
            total: mockHistory.length,
            hasMore: false,
          },
        },
      };
    },
    {
      params: t.Object({
        jobName: t.String(),
      }),
      query: t.Object({
        limit: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get job execution history (Admin)",
        description: "Get execution history for a specific scheduled job",
        tags: ["Scheduler"],
      },
    },
  )

  // Get system health metrics related to scheduled jobs
  .get(
    "/health",
    async () => {
      const jobs = schedulerService.getJobsStatus();
      const now = new Date();

      // Check if any jobs are overdue
      const overdueJobs = jobs.filter(
        (job) => job.nextRun && job.nextRun < now,
      );

      // Calculate system health score
      const healthScore =
        overdueJobs.length === 0
          ? 100
          : Math.max(0, 100 - (overdueJobs.length / jobs.length) * 50);

      return {
        success: true,
        data: {
          health: {
            score: healthScore,
            status:
              healthScore >= 90
                ? "excellent"
                : healthScore >= 70
                  ? "good"
                  : healthScore >= 50
                    ? "warning"
                    : "critical",
            totalJobs: jobs.length,
            overdueJobs: overdueJobs.length,
            lastChecked: now.toISOString(),
          },
          jobs: jobs.map((job) => ({
            name: job.name,
            status: job.nextRun && job.nextRun < now ? "overdue" : "scheduled",
            lastRun: job.lastRun,
            nextRun: job.nextRun,
          })),
          recommendations:
            overdueJobs.length > 0
              ? [
                  `${overdueJobs.length} job(s) are overdue and should be investigated`,
                  "Consider checking system resources and job performance",
                ]
              : [
                  "All jobs are running on schedule",
                  "System is operating normally",
                ],
        },
      };
    },
    {
      detail: {
        summary: "Get scheduler health status (Admin)",
        description: "Get health metrics and status of the scheduler system",
        tags: ["Scheduler"],
      },
    },
  )

  // Emergency stop all scheduled jobs (for maintenance)
  .post(
    "/emergency-stop",
    async () => {
      schedulerService.stop();

      return {
        success: true,
        message: "Scheduler stopped for emergency maintenance",
        data: {
          stoppedAt: new Date().toISOString(),
          warning: "Scheduled jobs will not run until scheduler is restarted",
        },
      };
    },
    {
      detail: {
        summary: "Emergency stop scheduler (Admin)",
        description: "Stop all scheduled jobs for emergency maintenance",
        tags: ["Scheduler"],
      },
    },
  )

  // Restart scheduler after maintenance
  .post(
    "/restart",
    async () => {
      schedulerService.stop();
      schedulerService.start();

      return {
        success: true,
        message: "Scheduler restarted successfully",
        data: {
          restartedAt: new Date().toISOString(),
          jobs: schedulerService.getJobsStatus(),
        },
      };
    },
    {
      detail: {
        summary: "Restart scheduler (Admin)",
        description: "Restart the scheduler service and all jobs",
        tags: ["Scheduler"],
      },
    },
  );
