// Export database connection and schema
export * from "./connection";
export * from "./schema";

// Export utilities
export { testConnection, closeConnections, ensureDatabaseHealth, createDatabaseIfNotExists } from "./connection";
export { seedDatabase } from "./seed";

// Export Windows-specific utilities
export * from "./setup-windows";
export * from "./health-monitor";
export * from "./windows-diagnostics";
export * from "./db-logger";

// Export convenience functions
export {
  checkDatabaseHealth,
  startHealthMonitoring,
  stopHealthMonitoring,
  getHealthReport,
  runEmergencyRecovery
} from "./health-monitor";

export {
  runWindowsDiagnostics,
  displayDiagnosticReport,
  autoFixWindowsIssues
} from "./windows-diagnostics";

export { dbLogger, timeOperation } from "./db-logger";

// Re-export Drizzle utilities  
export { eq, ne, gt, gte, lt, lte, and, or, sql, desc, asc, isNull, isNotNull, inArray, notInArray, like, ilike } from "drizzle-orm";
