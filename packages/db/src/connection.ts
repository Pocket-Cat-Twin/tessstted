import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema/index.js";

// Windows-only database configuration with enhanced error handling
// This project is designed exclusively for Windows environments
const WINDOWS_DEFAULT_CONNECTION = "postgresql://postgres:postgres@localhost:5432/yuyu_lolita";

// Enhanced connection configuration for Windows
function getConnectionConfig() {
  const connectionString = process.env.DATABASE_URL || WINDOWS_DEFAULT_CONNECTION;
  
  // Parse connection string to extract components
  const url = new URL(connectionString);
  
  return {
    host: url.hostname || 'localhost',
    port: parseInt(url.port) || 5432,
    database: url.pathname.slice(1) || 'yuyu_lolita', // Remove leading slash
    username: url.username || 'postgres',
    password: url.password || 'postgres',
    connectionString
  };
}

const config = getConnectionConfig();

// Validate Windows environment
if (process.platform !== "win32") {
  console.warn("⚠️  This application is optimized for Windows. Some features may not work on other platforms.");
}

// Enhanced Windows PostgreSQL configuration
const postgresConfig = {
  // Connection pooling
  max: 10,
  idle_timeout: 20,
  connect_timeout: 60,
  
  // Windows-specific settings
  ssl: false, // Disable SSL for local Windows connections
  
  // Character encoding for Windows Cyrillic support
  charset: 'utf8',
  
  // Connection options for Windows
  options: 'sslmode=disable',
  
  // Error handling
  onnotice: () => {}, // Suppress PostgreSQL notices
  
  // Transform for consistent encoding
  transform: postgres.camel,
  
  // Debug mode for connection issues
  debug: process.env.NODE_ENV === 'development'
};

// For migrations - single connection
export const migrationClient = postgres(config.connectionString, { 
  ...postgresConfig,
  max: 1,
});

// For queries - connection pool
export const queryClient = postgres(config.connectionString, postgresConfig);
export const db = drizzle(queryClient, { schema });

// Enhanced database connection validator with comprehensive error handling
export async function testConnection(): Promise<boolean> {
  let testClient: postgres.Sql | null = null;
  
  try {
    console.log("🔄 Testing Windows PostgreSQL connection...");
    console.log(`📍 Host: ${config.host}:${config.port}`);
    console.log(`📍 Database: ${config.database}`);
    console.log(`📍 User: ${config.username}`);
    
    // Create dedicated test connection
    testClient = postgres(config.connectionString, {
      ...postgresConfig,
      max: 1,
      connect_timeout: 10 // Shorter timeout for testing
    });
    
    // Test basic connectivity
    await testClient`SELECT 1 as test`;
    console.log("✅ PostgreSQL connection successful");
    
    // Test database existence with proper encoding
    const dbCheck = await testClient`
      SELECT datname, encoding, datcollate, datctype 
      FROM pg_database 
      WHERE datname = ${config.database}
    `;
    
    if (dbCheck.length === 0) {
      console.warn(`⚠️  Database '${config.database}' does not exist`);
      return false;
    }
    
    console.log("✅ Database exists and is accessible");
    console.log(`📊 Encoding: ${dbCheck[0]?.encoding}, Collate: ${dbCheck[0]?.datcollate}`);
    
    return true;
  } catch (error: any) {
    console.error("❌ PostgreSQL connection failed");
    
    // Enhanced error diagnostics for Windows
    const errorCode = error.code || error.errno || '';
    const errorMessage = error.message || '';
    
    console.error(`🔧 Error Code: ${errorCode}`);
    console.error(`🔧 Error Message: ${errorMessage}`);
    
    // Specific error handling
    if (errorCode === 'ENOENT') {
      console.error("🚨 CRITICAL: Unix socket connection attempted on Windows!");
      console.error("   ✅ Fix: Use TCP connection string: postgresql://user:pass@localhost:5432/db");
    } else if (errorCode === 'ECONNREFUSED') {
      console.error("🔌 PostgreSQL service not running");
      console.error("   ✅ Start service: net start postgresql-x64-*");
      console.error("   ✅ Check service: sc query postgresql*");
      console.error("   ✅ Check port: netstat -an | findstr :5432");
    } else if (errorCode === 'ENOTFOUND') {
      console.error("🌐 Hostname resolution failed");
      console.error("   ✅ Check: Ensure 'localhost' resolves correctly");
      console.error("   ✅ Try: Use 127.0.0.1 instead of localhost");
    } else if (errorCode === '28P01' || errorMessage.includes('password authentication')) {
      console.error("🔐 Authentication failed");
      console.error("   ✅ Check password: psql -U postgres -c \"ALTER USER postgres PASSWORD 'postgres';\"");
      console.error("   ✅ Or update DATABASE_URL in .env");
    } else if (errorCode === '3D000' || errorMessage.includes('does not exist') || 
               errorMessage.includes('не существует')) {
      console.error(`🗄️  Database '${config.database}' does not exist`);
      console.error("   ✅ Will attempt to create database automatically");
      console.error("   ✅ Or create manually: createdb -U postgres yuyu_lolita");
    } else if (errorMessage.includes('encoding') || errorMessage.includes('locale')) {
      console.error("🔤 Character encoding/locale issue");
      console.error("   ✅ Check PostgreSQL locale settings");
      console.error("   ✅ Ensure UTF-8 encoding support");
    }
    
    return false;
  } finally {
    // Clean up test connection
    if (testClient) {
      try {
        await testClient.end();
      } catch (_e) {
        // Ignore cleanup errors
      }
    }
  }
}

// Database health check with auto-recovery
export async function ensureDatabaseHealth(): Promise<boolean> {
  try {
    // First test if we can connect
    const connected = await testConnection();
    
    if (!connected) {
      console.log("🔄 Attempting database auto-recovery...");
      
      // Try to create database if it doesn't exist
      const created = await createDatabaseIfNotExists();
      if (created) {
        // Test again after creation
        return await testConnection();
      }
    }
    
    return connected;
  } catch (error) {
    console.error("❌ Database health check failed:", error);
    return false;
  }
}

// Auto-create database with proper Windows configuration
export async function createDatabaseIfNotExists(): Promise<boolean> {
  let adminClient: postgres.Sql | null = null;
  
  try {
    console.log("🔄 Checking if database needs to be created...");
    
    // Connect to 'postgres' database for admin operations
    const adminConnectionString = config.connectionString.replace(
      `/${config.database}`, '/postgres'
    );
    
    console.log(`📍 Admin connection: ${adminConnectionString.replace(/password=[^&;]*/gi, 'password=***')}`);
    
    adminClient = postgres(adminConnectionString, {
      ...postgresConfig,
      max: 1,
      connect_timeout: 10
    });
    
    // Check if database exists
    const result = await adminClient`
      SELECT 1 FROM pg_database WHERE datname = ${config.database}
    `;
    
    if (result.length === 0) {
      console.log(`🔨 Creating database '${config.database}' with UTF-8 encoding...`);
      
      // Create database with explicit UTF-8 encoding for Windows
      await adminClient.unsafe(`
        CREATE DATABASE ${config.database} 
        WITH 
        ENCODING = 'UTF8'
        LC_COLLATE = 'en_US.UTF-8'
        LC_CTYPE = 'en_US.UTF-8'
        TEMPLATE = template0
      `);
      
      console.log(`✅ Database '${config.database}' created successfully`);
      return true;
    } else {
      console.log(`✅ Database '${config.database}' already exists`);
      return true;
    }
  } catch (error: any) {
    console.error("❌ Failed to create database:", error.message);
    
    // If locale-specific creation fails, try simple creation
    if (error.message?.includes('locale') || error.message?.includes('template')) {
      try {
        console.log("🔄 Retrying with simple database creation...");
        if (adminClient) {
          await adminClient.unsafe(`CREATE DATABASE ${config.database}`);
          console.log(`✅ Database '${config.database}' created with default settings`);
          return true;
        }
      } catch (retryError) {
        console.error("❌ Simple database creation also failed:", retryError);
      }
    }
    
    return false;
  } finally {
    if (adminClient) {
      try {
        await adminClient.end();
      } catch (_e) {
        // Ignore cleanup errors
      }
    }
  }
}

// Close connections
export async function closeConnections() {
  await queryClient.end();
  await migrationClient.end();
}

// Export types
export type Database = typeof db;
