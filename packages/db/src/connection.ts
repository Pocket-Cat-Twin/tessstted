import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

// Windows-only database configuration
// This project is designed exclusively for Windows environments
const WINDOWS_DEFAULT_CONNECTION = "postgresql://postgres:postgres@localhost:5432/yuyu_lolita";

// Create connection with Windows TCP-only handling
const connectionString = process.env.DATABASE_URL || WINDOWS_DEFAULT_CONNECTION;

// Validate Windows environment
if (process.platform !== "win32") {
  console.warn("⚠️  This application is optimized for Windows. Some features may not work on other platforms.");
}

// For migrations
export const migrationClient = postgres(connectionString, { 
  max: 1,
});

// For queries
export const queryClient = postgres(connectionString);
export const db = drizzle(queryClient, { schema });

// Windows-specific connection helper with detailed diagnostics
export async function testConnection() {
  try {
    console.log("🔄 Testing Windows PostgreSQL connection...");
    console.log(`📍 Connection string: ${connectionString.replace(/password=[^&;]*/gi, 'password=***')}`);
    
    await queryClient`SELECT 1`;
    console.log("✅ Windows PostgreSQL connection successful");
    return true;
  } catch (error: any) {
    console.error("❌ Windows PostgreSQL connection failed");
    
    // Windows-specific error handling
    if (error.code === 'ENOENT') {
      console.error("🚨 CRITICAL: Attempting Unix socket connection on Windows!");
      console.error("   This indicates a configuration error.");
      console.error("   ✅ Fix: Ensure DATABASE_URL uses TCP format: postgresql://user:pass@localhost:5432/db");
      console.error("   ✅ Check: Windows PostgreSQL service is running on port 5432");
    } else if (error.code === 'ECONNREFUSED') {
      console.error("🔌 PostgreSQL service is not running or not accessible");
      console.error("   ✅ Start service: net start postgresql-x64-15");
      console.error("   ✅ Check port: netstat -an | findstr :5432");
    } else if (error.code === 'ENOTFOUND') {
      console.error("🌐 Host resolution failed");
      console.error("   ✅ Check: Ensure localhost resolves correctly");
    } else if (error.message?.includes('password authentication failed')) {
      console.error("🔐 Authentication failed");
      console.error("   ✅ Check: PostgreSQL user 'postgres' password");
      console.error("   ✅ Reset: psql -U postgres -c \"ALTER USER postgres PASSWORD 'postgres';\"");
    }
    
    console.error("🔧 Full error details:", error);
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
