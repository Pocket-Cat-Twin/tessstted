// Export database connection and schema
export * from "./connection.js";
export * from "./schema/index.js";

// Export utilities
export { testConnection, closeConnections, ensureDatabaseHealth, createDatabaseIfNotExists } from "./connection.js";
export { seedDatabase } from "./seed.js";

// Export Windows-specific utilities
export * from "./setup-windows.js";
export * from "./health-monitor.js";
export * from "./windows-diagnostics.js";
export * from "./db-logger.js";

// Export enterprise-grade systems
export * from "./environment-diagnostics.js";
export * from "./config-manager.js";
export * from "./database-error-handler.js";
export * from "./startup-validator.js";

// Export convenience functions
export {
  checkDatabaseHealth,
  startHealthMonitoring,
  stopHealthMonitoring,
  getHealthReport,
  runEmergencyRecovery
} from "./health-monitor.js";

export {
  runWindowsDiagnostics,
  displayDiagnosticReport,
  autoFixWindowsIssues
} from "./windows-diagnostics.js";

export { dbLogger, timeOperation } from "./db-logger.js";

// Re-export Drizzle utilities  
export { eq, ne, gt, gte, lt, lte, and, or, sql, desc, asc, isNull, isNotNull, inArray, notInArray, like, ilike } from "drizzle-orm";
