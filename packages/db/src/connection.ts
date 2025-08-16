import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

// Windows-specific database configuration
const isWindows = process.platform === "win32";
const defaultWindowsConnectionString = "postgresql://postgres:postgres@localhost:5432/yuyu_lolita";
const defaultUnixConnectionString = "postgresql://postgres:postgres@localhost:5432/yuyu_lolita";

// Create connection with Windows-specific handling
const connectionString = process.env.DATABASE_URL || 
  (isWindows ? defaultWindowsConnectionString : defaultUnixConnectionString);

// For migrations
export const migrationClient = postgres(connectionString, { max: 1 });

// For queries
export const queryClient = postgres(connectionString);
export const db = drizzle(queryClient, { schema });

// Connection helper
export async function testConnection() {
  try {
    await queryClient`SELECT 1`;
    console.log("✅ Database connection successful");
    return true;
  } catch (error) {
    console.error("❌ Database connection failed:", error);
    return false;
  }
}

// Close connections
export async function closeConnections() {
  await queryClient.end();
  await migrationClient.end();
}

// Export types
export type Database = typeof db;
