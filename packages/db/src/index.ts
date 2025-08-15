// Export database connection and schema
export * from './connection';
export * from './schema';

// Export utilities
export { testConnection, closeConnections } from './connection';
export { seedDatabase } from './seed';

// Re-export Drizzle utilities
export { eq, and, or, desc, asc, sql } from 'drizzle-orm';