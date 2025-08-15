import pino from 'pino';

// Environment configuration
const isProduction = process.env.NODE_ENV === 'production';
const isDevelopment = process.env.NODE_ENV === 'development';

// Logger configuration
const pinoConfig = {
  level: process.env.LOG_LEVEL || (isProduction ? 'info' : 'debug'),
  
  // Use pretty printing in development
  ...(isDevelopment && {
    transport: {
      target: 'pino-pretty',
      options: {
        colorize: true,
        ignore: 'pid,hostname',
        translateTime: 'yyyy-mm-dd HH:MM:ss',
        messageFormat: '[{context}] {msg}',
      }
    }
  }),

  // Structured logging for production
  ...(isProduction && {
    formatters: {
      level: (label: string) => ({ level: label }),
    },
    timestamp: pino.stdTimeFunctions.isoTime,
  }),

  // Base metadata
  base: {
    service: 'yuyu-api',
    environment: process.env.NODE_ENV || 'development',
    version: process.env.API_VERSION || '1.0.0',
  },
};

// Create logger instance
export const logger = pino(pinoConfig);

// Request context logger
export const createRequestLogger = (requestId: string, method: string, path: string, userAgent?: string) => {
  return logger.child({
    context: 'request',
    requestId,
    method,
    path,
    userAgent,
  });
};

// Service context logger
export const createServiceLogger = (service: string) => {
  return logger.child({
    context: 'service',
    service,
  });
};

// Database context logger
export const createDbLogger = () => {
  return logger.child({
    context: 'database',
  });
};

// Auth context logger
export const createAuthLogger = () => {
  return logger.child({
    context: 'auth',
  });
};

// Metrics and monitoring logger
export const createMetricsLogger = () => {
  return logger.child({
    context: 'metrics',
  });
};

// Security events logger
export const createSecurityLogger = () => {
  return logger.child({
    context: 'security',
  });
};

// Background job logger
export const createJobLogger = (jobName: string) => {
  return logger.child({
    context: 'job',
    jobName,
  });
};

// Performance monitoring utilities
export const logPerformance = (label: string, startTime: number, metadata?: object) => {
  const duration = Date.now() - startTime;
  logger.info({
    context: 'performance',
    label,
    duration,
    ...metadata,
  }, `Performance: ${label} completed in ${duration}ms`);
};

// Error logging with context
export const logError = (error: Error, context: string, metadata?: object) => {
  logger.error({
    context: 'error',
    errorContext: context,
    errorName: error.name,
    errorMessage: error.message,
    errorStack: error.stack,
    ...metadata,
  }, `Error in ${context}: ${error.message}`);
};

// Security event logging
export const logSecurityEvent = (event: string, userId?: string, ip?: string, metadata?: object) => {
  createSecurityLogger().warn({
    event,
    userId,
    ip,
    timestamp: new Date().toISOString(),
    ...metadata,
  }, `Security event: ${event}`);
};

// API metrics logging
export const logApiMetrics = (method: string, path: string, statusCode: number, duration: number, userId?: string) => {
  createMetricsLogger().info({
    method,
    path,
    statusCode,
    duration,
    userId,
    timestamp: new Date().toISOString(),
  }, `API ${method} ${path} - ${statusCode} (${duration}ms)`);
};

// Business logic logging
export const logBusinessEvent = (event: string, entityType: string, entityId: string, metadata?: object) => {
  logger.info({
    context: 'business',
    event,
    entityType,
    entityId,
    timestamp: new Date().toISOString(),
    ...metadata,
  }, `Business event: ${event} for ${entityType}:${entityId}`);
};

export default logger;