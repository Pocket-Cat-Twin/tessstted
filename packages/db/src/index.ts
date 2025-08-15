// Export database connection and schema
export * from "./connection";
export * from "./schema";

// Export utilities
export { testConnection, closeConnections } from "./connection";
export { seedDatabase } from "./seed";

// Re-export Drizzle utilities  
export { eq, ne, gt, gte, lt, lte, and, or, sql, desc, asc, isNull, isNotNull, inArray, notInArray, like, ilike } from "drizzle-orm";
