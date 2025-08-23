// Database health monitoring system for Windows PostgreSQL
// Provides continuous monitoring, automatic recovery, and detailed health reports

import { testConnection, createDatabaseIfNotExists } from './connection';
import { runWindowsDiagnostics, displayDiagnosticReport, autoFixWindowsIssues } from './windows-diagnostics';
import { dbLogger, timeOperation } from './db-logger';

export interface HealthStatus {
  overall: 'healthy' | 'degraded' | 'critical';
  database: 'connected' | 'disconnected' | 'missing';
  service: 'running' | 'stopped' | 'unknown';
  performance: 'good' | 'slow' | 'critical';
  lastCheck: Date;
  issues: string[];
  recommendations: string[];
}

export interface HealthCheckOptions {
  timeout: number; // milliseconds
  retries: number;
  autoFix: boolean;
  detailed: boolean;
}

class DatabaseHealthMonitor {
  private isMonitoring = false;
  private monitoringInterval: ReturnType<typeof setTimeout> | null = null;
  private lastHealthStatus: HealthStatus | null = null;
  private checkInterval = 60000; // 1 minute default

  // Run comprehensive health check
  async checkHealth(options: Partial<HealthCheckOptions> = {}): Promise<HealthStatus> {
    const opts: HealthCheckOptions = {
      timeout: 10000,
      retries: 3,
      autoFix: true,
      detailed: false,
      ...options
    };

    dbLogger.info('health', 'Starting database health check', { options: opts });
    
    const status: HealthStatus = {
      overall: 'healthy',
      database: 'disconnected',
      service: 'unknown',
      performance: 'good',
      lastCheck: new Date(),
      issues: [],
      recommendations: []
    };

    try {
      // 1. Check database connection
      await this.checkDatabaseConnection(status, opts);
      
      // 2. Check Windows service status
      if (opts.detailed) {
        await this.checkServiceStatus(status);
      }
      
      // 3. Check performance
      await this.checkPerformance(status);
      
      // 4. Auto-fix issues if requested
      if (opts.autoFix && status.issues.length > 0) {
        await this.attemptAutoFix(status);
      }
      
      // 5. Determine overall status
      this.determineOverallStatus(status);
      
      this.lastHealthStatus = status;
      dbLogger.trackHealthCheck(status.overall === 'healthy', {
        status: status.overall,
        issues: status.issues.length,
        recommendations: status.recommendations.length
      });
      
      return status;
    } catch (error) {
      status.overall = 'critical';
      status.issues.push(`Health check failed: ${error instanceof Error ? error.message : error}`);
      
      dbLogger.trackHealthCheck(false, {
        error: error instanceof Error ? error.message : error,
        status: 'critical'
      });
      
      return status;
    }
  }

  // Check database connection with retries
  private async checkDatabaseConnection(status: HealthStatus, options: HealthCheckOptions): Promise<void> {
    let attempts = 0;
    let lastError: Error | null = null;

    while (attempts < options.retries) {
      try {
        const timedResult = await timeOperation(async () => {
          return await testConnection();
        });

        if (timedResult.result) {
          status.database = 'connected';
          
          if (timedResult.duration > 5000) {
            status.performance = 'slow';
            status.issues.push(`Slow database connection: ${timedResult.duration}ms`);
            status.recommendations.push('Check PostgreSQL performance settings');
          } else if (timedResult.duration > 2000) {
            status.performance = 'slow';
            status.recommendations.push('Monitor database performance');
          }
          
          dbLogger.info('health', 'Database connection check passed', { 
            duration: timedResult.duration, 
            attempt: attempts + 1 
          });
          return;
        }
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        attempts++;
        
        dbLogger.warn('health', `Database connection attempt ${attempts} failed`, {
          error: lastError.message,
          attempt: attempts,
          maxRetries: options.retries
        });

        if (attempts < options.retries) {
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second between retries
        }
      }
    }

    // All attempts failed
    status.database = 'disconnected';
    if (lastError) {
      if (lastError.message.includes('does not exist') || lastError.message.includes('не существует')) {
        status.database = 'missing';
        status.issues.push('Database does not exist');
        status.recommendations.push('Run database setup: bun run db:setup');
      } else {
        status.issues.push(`Database connection failed: ${lastError.message}`);
        status.recommendations.push('Check PostgreSQL service and credentials');
      }
    }
  }

  // Check Windows PostgreSQL service status
  private async checkServiceStatus(status: HealthStatus): Promise<void> {
    try {
      const diagnostics = await runWindowsDiagnostics();
      const runningServices = diagnostics.services.filter(s => s.state === 'RUNNING');
      const stoppedServices = diagnostics.services.filter(s => s.state === 'STOPPED');

      if (runningServices.length > 0) {
        status.service = 'running';
        dbLogger.info('health', `PostgreSQL service running: ${runningServices[0]?.name}`);
      } else if (stoppedServices.length > 0) {
        status.service = 'stopped';
        status.issues.push(`PostgreSQL service stopped: ${stoppedServices[0]?.name}`);
        status.recommendations.push(`Start service: net start "${stoppedServices[0]?.name}"`);
      } else {
        status.service = 'unknown';
        status.issues.push('No PostgreSQL services found');
        status.recommendations.push('Install PostgreSQL: https://www.postgresql.org/download/windows/');
      }

      // Check network configuration
      if (!diagnostics.port5432Open) {
        status.issues.push('Port 5432 is not open');
        status.recommendations.push('Check PostgreSQL configuration and firewall');
      }

      if (!diagnostics.localhostResolvable) {
        status.issues.push('Localhost resolution failed');
        status.recommendations.push('Use 127.0.0.1 instead of localhost or fix DNS');
      }

    } catch (error) {
      dbLogger.warn('health', 'Could not check service status', { 
        error: error instanceof Error ? error.message : error 
      });
      status.service = 'unknown';
    }
  }

  // Check database performance
  private async checkPerformance(status: HealthStatus): Promise<void> {
    const metrics = dbLogger.getMetrics();
    
    // Check connection success rate
    const connectionSuccessRate = metrics.totalConnections > 0 
      ? ((metrics.totalConnections - metrics.failedConnections) / metrics.totalConnections) * 100 
      : 100;

    if (connectionSuccessRate < 90) {
      status.performance = 'critical';
      status.issues.push(`Poor connection success rate: ${connectionSuccessRate.toFixed(1)}%`);
      status.recommendations.push('Investigate connection failures');
    } else if (connectionSuccessRate < 95) {
      status.performance = 'slow';
      status.recommendations.push('Monitor connection stability');
    }

    // Check query performance
    if (metrics.averageQueryTime > 1000) {
      status.performance = 'critical';
      status.issues.push(`Slow queries: ${metrics.averageQueryTime.toFixed(0)}ms average`);
      status.recommendations.push('Optimize database queries and indexes');
    } else if (metrics.averageQueryTime > 500) {
      status.performance = 'slow';
      status.recommendations.push('Monitor query performance');
    }

    dbLogger.debug('health', 'Performance check completed', {
      connectionSuccessRate,
      averageQueryTime: metrics.averageQueryTime,
      totalConnections: metrics.totalConnections,
      performance: status.performance
    });
  }

  // Attempt automatic fixes
  private async attemptAutoFix(status: HealthStatus): Promise<void> {
    dbLogger.info('health', 'Attempting automatic issue resolution', { issues: status.issues });

    try {
      // Try to fix common Windows issues
      const fixes = await autoFixWindowsIssues();
      
      if (fixes.fixed.length > 0) {
        status.recommendations.push(`Auto-fixed: ${fixes.fixed.join(', ')}`);
        dbLogger.info('health', 'Auto-fix successful', { fixes: fixes.fixed });
      }

      if (fixes.failed.length > 0) {
        status.issues.push(`Auto-fix failed: ${fixes.failed.join(', ')}`);
        dbLogger.warn('health', 'Some auto-fixes failed', { failed: fixes.failed });
      }

      // Try to create database if missing
      if (status.database === 'missing') {
        dbLogger.info('health', 'Attempting to create missing database');
        const created = await createDatabaseIfNotExists();
        if (created) {
          status.recommendations.push('Auto-created missing database');
          // Re-test connection
          const connected = await testConnection();
          if (connected) {
            status.database = 'connected';
          }
        }
      }

    } catch (error) {
      dbLogger.error('health', 'Auto-fix attempt failed', {
        error: error instanceof Error ? error.message : error
      });
      status.issues.push('Auto-fix failed');
    }
  }

  // Determine overall health status
  private determineOverallStatus(status: HealthStatus): void {
    if (status.database === 'disconnected' || status.service === 'stopped') {
      status.overall = 'critical';
    } else if (status.database === 'missing' || status.performance === 'critical' || status.issues.length > 2) {
      status.overall = 'critical';
    } else if (status.performance === 'slow' || status.issues.length > 0) {
      status.overall = 'degraded';
    } else {
      status.overall = 'healthy';
    }

    dbLogger.info('health', `Health status determined: ${status.overall}`, {
      database: status.database,
      service: status.service,
      performance: status.performance,
      issueCount: status.issues.length
    });
  }

  // Start continuous monitoring
  startMonitoring(intervalMs = 60000): void {
    if (this.isMonitoring) {
      dbLogger.warn('health', 'Health monitoring is already running');
      return;
    }

    this.checkInterval = intervalMs;
    this.isMonitoring = true;
    
    dbLogger.info('health', `Starting health monitoring with ${intervalMs}ms interval`);

    // Initial check
    this.checkHealth({ detailed: true, autoFix: true });

    // Schedule periodic checks
    this.monitoringInterval = setInterval(async () => {
      try {
        await this.checkHealth({ detailed: false, autoFix: true });
      } catch (error) {
        dbLogger.error('health', 'Monitoring check failed', {
          error: error instanceof Error ? error.message : error
        });
      }
    }, intervalMs);
  }

  // Stop monitoring
  stopMonitoring(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    
    this.isMonitoring = false;
    dbLogger.info('health', 'Health monitoring stopped');
  }

  // Get monitoring status
  isHealthMonitoringActive(): boolean {
    return this.isMonitoring;
  }

  // Get last health status
  getLastHealthStatus(): HealthStatus | null {
    return this.lastHealthStatus;
  }

  // Generate detailed health report
  generateHealthReport(): string {
    const status = this.lastHealthStatus;
    const metrics = dbLogger.getMetrics();
    
    if (!status) {
      return '⚠️  No health data available. Run health check first.';
    }

    const statusIcon = status.overall === 'healthy' ? '✅' : 
                      status.overall === 'degraded' ? '⚠️' : '❌';

    const dbIcon = status.database === 'connected' ? '✅' : '❌';
    const serviceIcon = status.service === 'running' ? '✅' : 
                       status.service === 'stopped' ? '❌' : '❓';
    const perfIcon = status.performance === 'good' ? '✅' : 
                    status.performance === 'slow' ? '⚠️' : '❌';

    return `
🏥 Database Health Report
=========================
${statusIcon} Overall Status: ${status.overall.toUpperCase()}
${dbIcon} Database: ${status.database}
${serviceIcon} Service: ${status.service}
${perfIcon} Performance: ${status.performance}
📅 Last Check: ${status.lastCheck.toLocaleString()}
⏰ Monitoring: ${this.isMonitoring ? `Active (${this.checkInterval}ms)` : 'Stopped'}

${status.issues.length > 0 ? `
❌ Issues (${status.issues.length}):
${status.issues.map(issue => `   • ${issue}`).join('\n')}
` : '✅ No issues detected'}

${status.recommendations.length > 0 ? `
💡 Recommendations (${status.recommendations.length}):
${status.recommendations.map(rec => `   • ${rec}`).join('\n')}
` : ''}

📊 Performance Metrics:
   • Total Connections: ${metrics.totalConnections} (${metrics.failedConnections} failed)
   • Query Success Rate: ${metrics.successfulQueries > 0 ? 
     ((metrics.successfulQueries / (metrics.successfulQueries + metrics.failedQueries)) * 100).toFixed(1) + '%' : 'N/A'}
   • Average Query Time: ${metrics.averageQueryTime.toFixed(2)}ms
   • Last Health Check: ${metrics.lastHealthCheck?.toLocaleString() || 'Never'}

🔧 Quick Actions:
   • Full diagnostic: bun run db:diagnose
   • Service status: sc query postgresql*
   • Start service: net start postgresql-x64-*
   • Test connection: bun run db:test
=========================
`;
  }

  // Run emergency recovery
  async emergencyRecovery(): Promise<boolean> {
    dbLogger.info('health', 'Starting emergency database recovery');
    
    try {
      // Run full diagnostics
      const diagnostics = await runWindowsDiagnostics();
      displayDiagnosticReport(diagnostics);
      
      // Attempt all auto-fixes
      const fixes = await autoFixWindowsIssues();
      
      // Try to create database
      await createDatabaseIfNotExists();
      
      // Final health check
      const status = await this.checkHealth({ retries: 3, autoFix: true, detailed: true });
      
      const recovered = status.overall !== 'critical';
      
      dbLogger.info('health', `Emergency recovery ${recovered ? 'succeeded' : 'failed'}`, {
        finalStatus: status.overall,
        issues: status.issues.length,
        fixes: fixes.fixed.length
      });
      
      return recovered;
    } catch (error) {
      dbLogger.error('health', 'Emergency recovery failed', {
        error: error instanceof Error ? error.message : error
      });
      return false;
    }
  }
}

// Singleton instance
export const healthMonitor = new DatabaseHealthMonitor();

// Convenience functions
export const checkDatabaseHealth = (options?: Partial<HealthCheckOptions>) => 
  healthMonitor.checkHealth(options);

export const startHealthMonitoring = (intervalMs?: number) => 
  healthMonitor.startMonitoring(intervalMs);

export const stopHealthMonitoring = () => 
  healthMonitor.stopMonitoring();

export const getHealthReport = () => 
  healthMonitor.generateHealthReport();

export const runEmergencyRecovery = () => 
  healthMonitor.emergencyRecovery();

export default healthMonitor;