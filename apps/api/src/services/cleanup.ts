import { db } from '@yuyu/db';
import { verificationTokens, smsLogs, emailLogs, verificationRateLimit } from '@yuyu/db/schema/verification';
import { lt, and, or, eq } from 'drizzle-orm';
import { createJobLogger, logBusinessEvent } from './logger';

const cleanupLogger = createJobLogger('cleanup-service');

// Configuration for cleanup retention periods
const RETENTION_CONFIG = {
  // Verification tokens - keep for 7 days after expiration
  verificationTokens: {
    expiredDays: 7,
    completedDays: 30, // Keep verified tokens for 30 days for audit
  },
  
  // SMS logs - keep for 90 days
  smsLogs: {
    retentionDays: 90,
  },
  
  // Email logs - keep for 90 days
  emailLogs: {
    retentionDays: 90,
  },
  
  // Rate limit entries - keep for 1 day after expiration
  rateLimitEntries: {
    retentionDays: 1,
  },
};

// Cleanup expired verification tokens
export const cleanupVerificationTokens = async (): Promise<number> => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - RETENTION_CONFIG.verificationTokens.expiredDays);
  
  const completedCutoffDate = new Date();
  completedCutoffDate.setDate(completedCutoffDate.getDate() - RETENTION_CONFIG.verificationTokens.completedDays);
  
  try {
    cleanupLogger.info('Starting verification tokens cleanup', {
      expiredCutoff: cutoffDate.toISOString(),
      completedCutoff: completedCutoffDate.toISOString(),
    });
    
    // Delete tokens that are:
    // 1. Expired and older than retention period, OR
    // 2. Verified/failed and older than completed retention period
    const result = await db
      .delete(verificationTokens)
      .where(
        or(
          // Expired tokens older than cutoff
          and(
            lt(verificationTokens.expiresAt, cutoffDate),
            eq(verificationTokens.status, 'expired')
          ),
          // Verified tokens older than completed cutoff
          and(
            lt(verificationTokens.createdAt, completedCutoffDate),
            or(
              eq(verificationTokens.status, 'verified'),
              eq(verificationTokens.status, 'failed')
            )
          )
        )
      );
    
    const deletedCount = result.rowCount || 0;
    
    cleanupLogger.info('Verification tokens cleanup completed', {
      deletedCount,
      expiredCutoff: cutoffDate.toISOString(),
      completedCutoff: completedCutoffDate.toISOString(),
    });
    
    if (deletedCount > 0) {
      logBusinessEvent(
        'verification_tokens_cleanup',
        'system',
        'cleanup-service',
        { deletedCount }
      );
    }
    
    return deletedCount;
  } catch (error) {
    cleanupLogger.error('Failed to cleanup verification tokens', { error });
    throw error;
  }
};

// Cleanup old SMS logs
export const cleanupSmsLogs = async (): Promise<number> => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - RETENTION_CONFIG.smsLogs.retentionDays);
  
  try {
    cleanupLogger.info('Starting SMS logs cleanup', {
      cutoff: cutoffDate.toISOString(),
    });
    
    const result = await db
      .delete(smsLogs)
      .where(lt(smsLogs.sentAt, cutoffDate));
    
    const deletedCount = result.rowCount || 0;
    
    cleanupLogger.info('SMS logs cleanup completed', {
      deletedCount,
      cutoff: cutoffDate.toISOString(),
    });
    
    if (deletedCount > 0) {
      logBusinessEvent(
        'sms_logs_cleanup',
        'system',
        'cleanup-service',
        { deletedCount }
      );
    }
    
    return deletedCount;
  } catch (error) {
    cleanupLogger.error('Failed to cleanup SMS logs', { error });
    throw error;
  }
};

// Cleanup old email logs
export const cleanupEmailLogs = async (): Promise<number> => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - RETENTION_CONFIG.emailLogs.retentionDays);
  
  try {
    cleanupLogger.info('Starting email logs cleanup', {
      cutoff: cutoffDate.toISOString(),
    });
    
    const result = await db
      .delete(emailLogs)
      .where(lt(emailLogs.sentAt, cutoffDate));
    
    const deletedCount = result.rowCount || 0;
    
    cleanupLogger.info('Email logs cleanup completed', {
      deletedCount,
      cutoff: cutoffDate.toISOString(),
    });
    
    if (deletedCount > 0) {
      logBusinessEvent(
        'email_logs_cleanup',
        'system',
        'cleanup-service',
        { deletedCount }
      );
    }
    
    return deletedCount;
  } catch (error) {
    cleanupLogger.error('Failed to cleanup email logs', { error });
    throw error;
  }
};

// Cleanup old rate limit entries
export const cleanupRateLimitEntries = async (): Promise<number> => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - RETENTION_CONFIG.rateLimitEntries.retentionDays);
  
  try {
    cleanupLogger.info('Starting rate limit entries cleanup', {
      cutoff: cutoffDate.toISOString(),
    });
    
    // Delete entries that are old OR have expired blocks
    const result = await db
      .delete(verificationRateLimit)
      .where(
        or(
          lt(verificationRateLimit.createdAt, cutoffDate),
          and(
            verificationRateLimit.blockedUntil !== null,
            lt(verificationRateLimit.blockedUntil, new Date())
          )
        )
      );
    
    const deletedCount = result.rowCount || 0;
    
    cleanupLogger.info('Rate limit entries cleanup completed', {
      deletedCount,
      cutoff: cutoffDate.toISOString(),
    });
    
    if (deletedCount > 0) {
      logBusinessEvent(
        'rate_limit_cleanup',
        'system',
        'cleanup-service',
        { deletedCount }
      );
    }
    
    return deletedCount;
  } catch (error) {
    cleanupLogger.error('Failed to cleanup rate limit entries', { error });
    throw error;
  }
};

// Run all cleanup tasks
export const runFullCleanup = async (): Promise<{
  verificationTokens: number;
  smsLogs: number;
  emailLogs: number;
  rateLimitEntries: number;
  totalDeleted: number;
}> => {
  cleanupLogger.info('Starting full cleanup process');
  
  const startTime = Date.now();
  const results = {
    verificationTokens: 0,
    smsLogs: 0,
    emailLogs: 0,
    rateLimitEntries: 0,
    totalDeleted: 0,
  };
  
  try {
    // Run all cleanup tasks in parallel for better performance
    const [tokensDeleted, smsDeleted, emailDeleted, rateLimitDeleted] = await Promise.all([
      cleanupVerificationTokens(),
      cleanupSmsLogs(),
      cleanupEmailLogs(),
      cleanupRateLimitEntries(),
    ]);
    
    results.verificationTokens = tokensDeleted;
    results.smsLogs = smsDeleted;
    results.emailLogs = emailDeleted;
    results.rateLimitEntries = rateLimitDeleted;
    results.totalDeleted = tokensDeleted + smsDeleted + emailDeleted + rateLimitDeleted;
    
    const duration = Date.now() - startTime;
    
    cleanupLogger.info('Full cleanup process completed', {
      results,
      duration,
    });
    
    logBusinessEvent(
      'full_cleanup_completed',
      'system',
      'cleanup-service',
      { results, duration }
    );
    
    return results;
  } catch (error) {
    const duration = Date.now() - startTime;
    cleanupLogger.error('Full cleanup process failed', { error, duration });
    throw error;
  }
};

// Get cleanup statistics without performing cleanup
export const getCleanupStatistics = async () => {
  const cutoffDates = {
    verificationTokensExpired: new Date(),
    verificationTokensCompleted: new Date(),
    smsLogs: new Date(),
    emailLogs: new Date(),
    rateLimitEntries: new Date(),
  };
  
  cutoffDates.verificationTokensExpired.setDate(
    cutoffDates.verificationTokensExpired.getDate() - RETENTION_CONFIG.verificationTokens.expiredDays
  );
  cutoffDates.verificationTokensCompleted.setDate(
    cutoffDates.verificationTokensCompleted.getDate() - RETENTION_CONFIG.verificationTokens.completedDays
  );
  cutoffDates.smsLogs.setDate(
    cutoffDates.smsLogs.getDate() - RETENTION_CONFIG.smsLogs.retentionDays
  );
  cutoffDates.emailLogs.setDate(
    cutoffDates.emailLogs.getDate() - RETENTION_CONFIG.emailLogs.retentionDays
  );
  cutoffDates.rateLimitEntries.setDate(
    cutoffDates.rateLimitEntries.getDate() - RETENTION_CONFIG.rateLimitEntries.retentionDays
  );
  
  try {
    // Count records that would be deleted
    const [
      expiredTokensCount,
      oldSmsLogsCount,
      oldEmailLogsCount,
      oldRateLimitCount,
    ] = await Promise.all([
      // Count verification tokens to be deleted
      db.select().from(verificationTokens).where(
        or(
          and(
            lt(verificationTokens.expiresAt, cutoffDates.verificationTokensExpired),
            eq(verificationTokens.status, 'expired')
          ),
          and(
            lt(verificationTokens.createdAt, cutoffDates.verificationTokensCompleted),
            or(
              eq(verificationTokens.status, 'verified'),
              eq(verificationTokens.status, 'failed')
            )
          )
        )
      ).then(results => results.length),
      
      // Count SMS logs to be deleted
      db.select().from(smsLogs)
        .where(lt(smsLogs.sentAt, cutoffDates.smsLogs))
        .then(results => results.length),
      
      // Count email logs to be deleted
      db.select().from(emailLogs)
        .where(lt(emailLogs.sentAt, cutoffDates.emailLogs))
        .then(results => results.length),
      
      // Count rate limit entries to be deleted
      db.select().from(verificationRateLimit).where(
        or(
          lt(verificationRateLimit.createdAt, cutoffDates.rateLimitEntries),
          and(
            verificationRateLimit.blockedUntil !== null,
            lt(verificationRateLimit.blockedUntil, new Date())
          )
        )
      ).then(results => results.length),
    ]);
    
    return {
      retentionConfig: RETENTION_CONFIG,
      cutoffDates,
      recordsToDelete: {
        verificationTokens: expiredTokensCount,
        smsLogs: oldSmsLogsCount,
        emailLogs: oldEmailLogsCount,
        rateLimitEntries: oldRateLimitCount,
        total: expiredTokensCount + oldSmsLogsCount + oldEmailLogsCount + oldRateLimitCount,
      },
    };
  } catch (error) {
    cleanupLogger.error('Failed to get cleanup statistics', { error });
    throw error;
  }
};

// Schedule cleanup to run automatically
export const scheduleCleanup = () => {
  cleanupLogger.info('Scheduling automatic cleanup', {
    interval: 'daily at 2:00 AM',
    retentionConfig: RETENTION_CONFIG,
  });
  
  // Run cleanup daily at 2:00 AM
  const runDailyCleanup = () => {
    const now = new Date();
    const targetTime = new Date();
    targetTime.setHours(2, 0, 0, 0); // 2:00 AM
    
    // If 2:00 AM has passed today, schedule for tomorrow
    if (now > targetTime) {
      targetTime.setDate(targetTime.getDate() + 1);
    }
    
    const timeUntilCleanup = targetTime.getTime() - now.getTime();
    
    setTimeout(async () => {
      try {
        cleanupLogger.info('Running scheduled cleanup');
        await runFullCleanup();
        
        // Schedule next cleanup
        setInterval(async () => {
          try {
            cleanupLogger.info('Running scheduled cleanup');
            await runFullCleanup();
          } catch (error) {
            cleanupLogger.error('Scheduled cleanup failed', { error });
          }
        }, 24 * 60 * 60 * 1000); // Every 24 hours
        
      } catch (error) {
        cleanupLogger.error('Initial scheduled cleanup failed', { error });
      }
    }, timeUntilCleanup);
    
    cleanupLogger.info('Next cleanup scheduled', {
      scheduledTime: targetTime.toISOString(),
      timeUntilCleanup: Math.round(timeUntilCleanup / 1000 / 60), // minutes
    });
  };
  
  runDailyCleanup();
};

export default {
  cleanupVerificationTokens,
  cleanupSmsLogs,
  cleanupEmailLogs,
  cleanupRateLimitEntries,
  runFullCleanup,
  getCleanupStatistics,
  scheduleCleanup,
};