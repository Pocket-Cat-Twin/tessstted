// Comprehensive database logging system for Windows PostgreSQL
// Provides detailed logging for database operations, errors, and performance

export interface LogEntry {
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'debug';
  category: 'connection' | 'query' | 'migration' | 'health' | 'diagnostic';
  message: string;
  details?: any;
  duration?: number;
}

export interface DatabaseMetrics {
  totalConnections: number;
  failedConnections: number;
  successfulQueries: number;
  failedQueries: number;
  averageQueryTime: number;
  lastHealthCheck: Date | null;
  uptime: number;
}

class DatabaseLogger {
  private logs: LogEntry[] = [];
  private metrics: DatabaseMetrics = {
    totalConnections: 0,
    failedConnections: 0,
    successfulQueries: 0,
    failedQueries: 0,
    averageQueryTime: 0,
    lastHealthCheck: null,
    uptime: Date.now()
  };
  private maxLogs = 1000; // Keep last 1000 log entries
  private queryTimes: number[] = [];
  private maxQueryTimes = 100; // Keep last 100 query times for average calculation

  // Add log entry
  private addLog(level: LogEntry['level'], category: LogEntry['category'], message: string, details?: any, duration?: number): void {
    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      category,
      message,
      ...(details && { details }),
      ...(duration && { duration })
    };

    this.logs.push(entry);
    
    // Trim logs if exceeding max
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // Console output with colors (Windows Command Prompt compatible)
    const timestamp = entry.timestamp.toISOString();
    const levelIcon = this.getLevelIcon(level);
    const categoryIcon = this.getCategoryIcon(category);
    
    let output = `[${timestamp}] ${levelIcon} ${categoryIcon} ${message}`;
    if (duration) {
      output += ` (${duration}ms)`;
    }
    
    switch (level) {
      case 'error':
        console.error(output);
        break;
      case 'warn':
        console.warn(output);
        break;
      case 'debug':
        if (process.env.NODE_ENV === 'development') {
          console.debug(output);
        }
        break;
      default:
        console.log(output);
    }

    if (details && (level === 'error' || process.env.NODE_ENV === 'development')) {
      console.log('  Details:', details);
    }
  }

  private getLevelIcon(level: LogEntry['level']): string {
    switch (level) {
      case 'error': return '❌';
      case 'warn': return '⚠️';
      case 'info': return 'ℹ️';
      case 'debug': return '🔍';
      default: return '📝';
    }
  }

  private getCategoryIcon(category: LogEntry['category']): string {
    switch (category) {
      case 'connection': return '🔌';
      case 'query': return '🗃️';
      case 'migration': return '🔄';
      case 'health': return '🏥';
      case 'diagnostic': return '🔍';
      default: return '📊';
    }
  }

  // Public logging methods
  info(category: LogEntry['category'], message: string, details?: any): void {
    this.addLog('info', category, message, details);
  }

  warn(category: LogEntry['category'], message: string, details?: any): void {
    this.addLog('warn', category, message, details);
  }

  error(category: LogEntry['category'], message: string, details?: any): void {
    this.addLog('error', category, message, details);
  }

  debug(category: LogEntry['category'], message: string, details?: any): void {
    this.addLog('debug', category, message, details);
  }

  // Connection tracking
  trackConnection(success: boolean, duration?: number): void {
    this.metrics.totalConnections++;
    if (success) {
      this.info('connection', 'Database connection successful', { duration });
    } else {
      this.metrics.failedConnections++;
      this.error('connection', 'Database connection failed', { duration });
    }
  }

  // Query tracking
  trackQuery(success: boolean, query: string, duration: number, error?: any): void {
    if (success) {
      this.metrics.successfulQueries++;
      this.debug('query', 'Query executed successfully', { 
        query: query.substring(0, 100) + (query.length > 100 ? '...' : ''),
        duration 
      });
    } else {
      this.metrics.failedQueries++;
      this.error('query', 'Query execution failed', { 
        query: query.substring(0, 100) + (query.length > 100 ? '...' : ''),
        duration,
        error: error?.message || error
      });
    }

    // Track query times for average calculation
    this.queryTimes.push(duration);
    if (this.queryTimes.length > this.maxQueryTimes) {
      this.queryTimes = this.queryTimes.slice(-this.maxQueryTimes);
    }
    
    // Update average query time
    this.metrics.averageQueryTime = this.queryTimes.reduce((a, b) => a + b, 0) / this.queryTimes.length;
  }

  // Health check tracking
  trackHealthCheck(success: boolean, details?: any): void {
    this.metrics.lastHealthCheck = new Date();
    if (success) {
      this.info('health', 'Database health check passed', details);
    } else {
      this.error('health', 'Database health check failed', details);
    }
  }

  // Migration tracking
  trackMigration(operation: string, success: boolean, duration?: number, details?: any): void {
    if (success) {
      this.info('migration', `Migration ${operation} completed`, { duration, ...details });
    } else {
      this.error('migration', `Migration ${operation} failed`, { duration, ...details });
    }
  }

  // Diagnostic tracking
  trackDiagnostic(message: string, details?: any): void {
    this.info('diagnostic', message, details);
  }

  // Get metrics
  getMetrics(): DatabaseMetrics {
    return {
      ...this.metrics,
      uptime: Date.now() - this.metrics.uptime
    };
  }

  // Get recent logs
  getRecentLogs(count = 50): LogEntry[] {
    return this.logs.slice(-count);
  }

  // Get logs by category
  getLogsByCategory(category: LogEntry['category'], count = 50): LogEntry[] {
    return this.logs
      .filter(log => log.category === category)
      .slice(-count);
  }

  // Get error logs
  getErrorLogs(count = 20): LogEntry[] {
    return this.logs
      .filter(log => log.level === 'error')
      .slice(-count);
  }

  // Generate performance report
  generatePerformanceReport(): string {
    const metrics = this.getMetrics();
    const upDays = Math.floor(metrics.uptime / (1000 * 60 * 60 * 24));
    const upHours = Math.floor((metrics.uptime % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const upMinutes = Math.floor((metrics.uptime % (1000 * 60 * 60)) / (1000 * 60));

    return `
📊 Database Performance Report
==============================
🔌 Connections: ${metrics.totalConnections} total, ${metrics.failedConnections} failed (${((metrics.totalConnections - metrics.failedConnections) / metrics.totalConnections * 100 || 0).toFixed(1)}% success)
🗃️  Queries: ${metrics.successfulQueries} successful, ${metrics.failedQueries} failed (${(metrics.successfulQueries / (metrics.successfulQueries + metrics.failedQueries) * 100 || 0).toFixed(1)}% success)
⏱️  Average Query Time: ${metrics.averageQueryTime.toFixed(2)}ms
🏥 Last Health Check: ${metrics.lastHealthCheck?.toLocaleString() || 'Never'}
⏰ Uptime: ${upDays}d ${upHours}h ${upMinutes}m
💾 Log Entries: ${this.logs.length}
==============================
`;
  }

  // Clear logs (useful for testing)
  clearLogs(): void {
    this.logs = [];
    this.metrics = {
      totalConnections: 0,
      failedConnections: 0,
      successfulQueries: 0,
      failedQueries: 0,
      averageQueryTime: 0,
      lastHealthCheck: null,
      uptime: Date.now()
    };
    this.queryTimes = [];
  }

  // Export logs to JSON (for debugging)
  exportLogs(): string {
    return JSON.stringify({
      logs: this.logs,
      metrics: this.metrics,
      generatedAt: new Date().toISOString()
    }, null, 2);
  }
}

// Singleton instance
export const dbLogger = new DatabaseLogger();

// Helper function to time database operations
export function timeOperation<T>(operation: () => Promise<T>): Promise<{ result: T; duration: number }> {
  const start = Date.now();
  return operation().then(
    result => ({ result, duration: Date.now() - start }),
    error => {
      const duration = Date.now() - start;
      throw { error, duration };
    }
  );
}

// Decorator for logging database operations
export function loggedOperation(category: LogEntry['category'], operationName: string) {
  return function <T extends (...args: any[]) => Promise<any>>(
    _target: any,
    _propertyName: string,
    descriptor: TypedPropertyDescriptor<T>
  ): TypedPropertyDescriptor<T> {
    const method = descriptor.value!;
    
    descriptor.value = (async function (this: any, ...args: any[]) {
      const start = Date.now();
      try {
        const result = await method.apply(this, args);
        const duration = Date.now() - start;
        dbLogger.info(category, `${operationName} completed successfully`, { duration, args: args.slice(0, 2) });
        return result;
      } catch (error) {
        const duration = Date.now() - start;
        dbLogger.error(category, `${operationName} failed`, { duration, error: error instanceof Error ? error.message : error, args: args.slice(0, 2) });
        throw error;
      }
    } as any) as T;
    
    return descriptor;
  };
}

export default dbLogger;