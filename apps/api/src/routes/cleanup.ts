import { Elysia, t } from 'elysia';
import { authMiddleware } from '../middleware/auth';
import {
  runFullCleanup,
  cleanupVerificationTokens,
  cleanupSmsLogs,
  cleanupEmailLogs,
  cleanupRateLimitEntries,
  getCleanupStatistics,
} from '../services/cleanup';

export const cleanupRoutes = new Elysia({ prefix: '/cleanup' })
  .use(authMiddleware)
  .guard(
    {
      beforeHandle: ({ user, set }) => {
        if (!user || user.role !== 'admin') {
          set.status = 403;
          return {
            success: false,
            error: 'INSUFFICIENT_PERMISSIONS',
            message: 'Admin access required',
          };
        }
      },
    },
    (app) =>
      app
        // Get cleanup statistics (what would be deleted)
        .get('/statistics', async () => {
          try {
            const stats = await getCleanupStatistics();
            
            return {
              success: true,
              data: stats,
            };
          } catch (error) {
            return {
              success: false,
              error: 'CLEANUP_STATS_ERROR',
              message: 'Failed to get cleanup statistics',
              details: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        }, {
          detail: {
            tags: ['Cleanup'],
            summary: 'Get cleanup statistics',
            description: 'Returns statistics about what records would be deleted by cleanup operations',
          },
        })

        // Run full cleanup
        .post('/run', async () => {
          try {
            const results = await runFullCleanup();
            
            return {
              success: true,
              message: 'Cleanup completed successfully',
              data: results,
            };
          } catch (error) {
            return {
              success: false,
              error: 'CLEANUP_ERROR',
              message: 'Failed to run cleanup',
              details: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        }, {
          detail: {
            tags: ['Cleanup'],
            summary: 'Run full cleanup',
            description: 'Manually trigger cleanup of all old verification data',
          },
        })

        // Cleanup specific data types
        .post('/verification-tokens', async () => {
          try {
            const deletedCount = await cleanupVerificationTokens();
            
            return {
              success: true,
              message: `Cleaned up ${deletedCount} verification tokens`,
              data: { deletedCount },
            };
          } catch (error) {
            return {
              success: false,
              error: 'CLEANUP_ERROR',
              message: 'Failed to cleanup verification tokens',
              details: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        }, {
          detail: {
            tags: ['Cleanup'],
            summary: 'Cleanup verification tokens',
            description: 'Manually cleanup old verification tokens',
          },
        })

        .post('/sms-logs', async () => {
          try {
            const deletedCount = await cleanupSmsLogs();
            
            return {
              success: true,
              message: `Cleaned up ${deletedCount} SMS logs`,
              data: { deletedCount },
            };
          } catch (error) {
            return {
              success: false,
              error: 'CLEANUP_ERROR',
              message: 'Failed to cleanup SMS logs',
              details: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        }, {
          detail: {
            tags: ['Cleanup'],
            summary: 'Cleanup SMS logs',
            description: 'Manually cleanup old SMS logs',
          },
        })

        .post('/email-logs', async () => {
          try {
            const deletedCount = await cleanupEmailLogs();
            
            return {
              success: true,
              message: `Cleaned up ${deletedCount} email logs`,
              data: { deletedCount },
            };
          } catch (error) {
            return {
              success: false,
              error: 'CLEANUP_ERROR',
              message: 'Failed to cleanup email logs',
              details: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        }, {
          detail: {
            tags: ['Cleanup'],
            summary: 'Cleanup email logs',
            description: 'Manually cleanup old email logs',
          },
        })

        .post('/rate-limit-entries', async () => {
          try {
            const deletedCount = await cleanupRateLimitEntries();
            
            return {
              success: true,
              message: `Cleaned up ${deletedCount} rate limit entries`,
              data: { deletedCount },
            };
          } catch (error) {
            return {
              success: false,
              error: 'CLEANUP_ERROR',
              message: 'Failed to cleanup rate limit entries',
              details: error instanceof Error ? error.message : 'Unknown error',
            };
          }
        }, {
          detail: {
            tags: ['Cleanup'],
            summary: 'Cleanup rate limit entries',
            description: 'Manually cleanup old rate limit entries',
          },
        })
  );

export default cleanupRoutes;