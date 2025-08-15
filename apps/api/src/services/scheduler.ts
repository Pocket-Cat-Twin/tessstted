import { storageService } from './storage';
import { subscriptionService } from './subscription';

export interface ScheduledJobResult {
  jobName: string;
  status: 'success' | 'error';
  message: string;
  data?: any;
  executedAt: Date;
  duration: number;
}

class SchedulerService {
  private jobs: Map<string, { 
    fn: () => Promise<any>, 
    interval: number, 
    lastRun?: Date,
    nextRun?: Date 
  }> = new Map();

  /**
   * Register a new scheduled job
   */
  registerJob(
    name: string, 
    jobFunction: () => Promise<any>, 
    intervalMinutes: number
  ): void {
    const intervalMs = intervalMinutes * 60 * 1000;
    this.jobs.set(name, {
      fn: jobFunction,
      interval: intervalMs,
      nextRun: new Date(Date.now() + intervalMs),
    });

    console.log(`📋 Scheduled job "${name}" registered to run every ${intervalMinutes} minutes`);
  }

  /**
   * Process storage expiration notifications and cleanup
   */
  async processStorageExpirations(): Promise<ScheduledJobResult> {
    const startTime = Date.now();
    
    try {
      console.log('🏪 Processing storage expirations...');
      
      const result = await storageService.processStorageExpirations();
      
      // Here you would integrate with actual notification services
      // For now, we'll just log the notifications that should be sent
      if (result.notificationsToSend.length > 0) {
        console.log(`📨 ${result.notificationsToSend.length} storage expiry notifications to send:`);
        result.notificationsToSend.forEach(notification => {
          console.log(`  - Order ${notification.orderNumber} (${notification.tier}) expires in ${notification.daysUntilExpiry} days`);
        });
      }

      if (result.expiredItems.length > 0) {
        console.log(`⚠️ ${result.expiredItems.length} items have expired storage:`);
        result.expiredItems.forEach(item => {
          console.log(`  - Order ${item.orderNumber} (${item.subscriptionTier}) expired ${Math.abs(item.daysUntilExpiry || 0)} days ago`);
        });
      }

      const duration = Date.now() - startTime;
      
      return {
        jobName: 'processStorageExpirations',
        status: 'success',
        message: `Processed ${result.processed} storage items`,
        data: {
          notifications: result.notificationsToSend.length,
          expired: result.expiredItems.length,
          details: result,
        },
        executedAt: new Date(),
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error('❌ Error processing storage expirations:', error);
      
      return {
        jobName: 'processStorageExpirations',
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error',
        executedAt: new Date(),
        duration,
      };
    }
  }

  /**
   * Process subscription auto-renewals
   */
  async processSubscriptionRenewals(): Promise<ScheduledJobResult> {
    const startTime = Date.now();
    
    try {
      console.log('🔄 Processing subscription auto-renewals...');
      
      const result = await subscriptionService.processAutoRenewals();
      
      const duration = Date.now() - startTime;
      
      return {
        jobName: 'processSubscriptionRenewals',
        status: 'success',
        message: `Processed ${result.processed} renewals, ${result.failed} failed`,
        data: result,
        executedAt: new Date(),
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error('❌ Error processing subscription renewals:', error);
      
      return {
        jobName: 'processSubscriptionRenewals',
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error',
        executedAt: new Date(),
        duration,
      };
    }
  }

  /**
   * Clean up old verification codes and expired sessions
   */
  async cleanupExpiredData(): Promise<ScheduledJobResult> {
    const startTime = Date.now();
    
    try {
      console.log('🧹 Cleaning up expired data...');
      
      // This would clean up expired verification codes, sessions, etc.
      // Implementation would depend on your specific cleanup needs
      
      const duration = Date.now() - startTime;
      
      return {
        jobName: 'cleanupExpiredData',
        status: 'success',
        message: 'Cleanup completed successfully',
        data: { cleaned: 0 }, // Placeholder
        executedAt: new Date(),
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error('❌ Error during cleanup:', error);
      
      return {
        jobName: 'cleanupExpiredData',
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error',
        executedAt: new Date(),
        duration,
      };
    }
  }

  /**
   * Run a specific job manually
   */
  async runJob(jobName: string): Promise<ScheduledJobResult> {
    const job = this.jobs.get(jobName);
    if (!job) {
      throw new Error(`Job "${jobName}" not found`);
    }

    console.log(`▶️ Manually running job: ${jobName}`);
    const result = await job.fn();
    
    // Update last run time
    job.lastRun = new Date();
    job.nextRun = new Date(Date.now() + job.interval);
    
    return result;
  }

  /**
   * Get status of all registered jobs
   */
  getJobsStatus(): Array<{
    name: string;
    lastRun: Date | null;
    nextRun: Date | null;
    intervalMinutes: number;
  }> {
    return Array.from(this.jobs.entries()).map(([name, job]) => ({
      name,
      lastRun: job.lastRun || null,
      nextRun: job.nextRun || null,
      intervalMinutes: job.interval / (60 * 1000),
    }));
  }

  /**
   * Start the scheduler (would be enhanced with actual cron-like functionality)
   */
  start(): void {
    console.log('🕐 Starting scheduler service...');
    
    // Register default jobs
    this.registerJob('processStorageExpirations', () => this.processStorageExpirations(), 60); // Every hour
    this.registerJob('processSubscriptionRenewals', () => this.processSubscriptionRenewals(), 360); // Every 6 hours  
    this.registerJob('cleanupExpiredData', () => this.cleanupExpiredData(), 1440); // Daily

    // In a real implementation, you would use a proper job scheduler like node-cron
    // For now, we'll just log that the scheduler is ready
    console.log('📋 Scheduler service started with jobs:');
    this.getJobsStatus().forEach(job => {
      console.log(`  - ${job.name}: every ${job.intervalMinutes} minutes`);
    });
  }

  /**
   * Stop the scheduler
   */
  stop(): void {
    console.log('🛑 Stopping scheduler service...');
    this.jobs.clear();
  }
}

// Export singleton instance
export const schedulerService = new SchedulerService();

// Auto-start scheduler in production
if (process.env.NODE_ENV === 'production') {
  schedulerService.start();
}