// Windows-specific database initialization script
import { migrate } from "drizzle-orm/postgres-js/migrator";
import { migrationClient, db, testConnection } from "./connection";
import postgres from "postgres";

const isWindows = process.platform === "win32";

// Default PostgreSQL settings for Windows
const WINDOWS_PG_DEFAULTS = {
  host: "localhost",
  port: 5432,
  user: "postgres",
  database: "postgres", // Connect to default database first
  password: "password"
};

async function createDatabaseIfNotExists() {
  console.log("[DB] Checking if database exists...");
  
  // Connect to default postgres database to create our database
  const adminConnectionString = `postgresql://${WINDOWS_PG_DEFAULTS.user}:${WINDOWS_PG_DEFAULTS.password}@${WINDOWS_PG_DEFAULTS.host}:${WINDOWS_PG_DEFAULTS.port}/${WINDOWS_PG_DEFAULTS.database}`;
  const adminClient = postgres(adminConnectionString, { max: 1 });
  
  try {
    // Check if our database exists
    const result = await adminClient`
      SELECT 1 FROM pg_database WHERE datname = 'yuyu_lolita'
    `;
    
    if (result.length === 0) {
      console.log("[INFO] Creating yuyu_lolita database...");
      await adminClient`CREATE DATABASE yuyu_lolita`;
      console.log("[SUCCESS] Database yuyu_lolita created successfully");
    } else {
      console.log("[SUCCESS] Database yuyu_lolita already exists");
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("[ERROR] Error checking/creating database:", errorMessage);
    throw error;
  } finally {
    await adminClient.end();
  }
}

async function checkPostgreSQLService() {
  if (!isWindows) {
    console.log("[INFO] Not running on Windows, skipping service check");
    return true;
  }
  
  console.log("[SERVICE] Checking PostgreSQL service on Windows...");
  
  try {
    // Try to import child_process for Windows service check
    const { exec } = await import("child_process");
    const { promisify } = await import("util");
    const execAsync = promisify(exec);
    
    // Check if PostgreSQL service is running
    const { stdout } = await execAsync('sc query postgresql*');
    
    if (stdout.includes("RUNNING")) {
      console.log("[SUCCESS] PostgreSQL service is running");
      return true;
    } else if (stdout.includes("STOPPED")) {
      console.log("[WARNING] PostgreSQL service is stopped, attempting to start...");
      
      try {
        await execAsync('net start postgresql*');
        console.log("[SUCCESS] PostgreSQL service started");
        return true;
      } catch (startError) {
        console.log("[ERROR] Failed to start PostgreSQL service automatically");
        console.log("        Please start it manually: net start postgresql-x64-16");
        return false;
      }
    }
  } catch (error) {
    console.log("[WARNING] Could not check PostgreSQL service status");
    console.log("          This is normal if PostgreSQL was installed differently");
  }
  
  return true;
}

async function testDatabaseConnection() {
  console.log("[DB] Testing database connection...");
  
  const maxRetries = 3;
  let retries = 0;
  
  let lastError: string | null = null;
  
  while (retries < maxRetries) {
    try {
      const isConnected = await testConnection();
      if (isConnected) {
        console.log("[SUCCESS] Database connection successful");
        return true;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      lastError = errorMessage;
      console.log(`[ERROR] Connection attempt ${retries + 1} failed: ${errorMessage}`);
      
      // Check for specific error codes
      if (errorMessage.includes("28P01")) {
        console.log("[INFO] Authentication failed - incorrect password");
        console.log("       Please ensure PostgreSQL user 'postgres' has password 'password'");
        console.log("       Or update DATABASE_URL in .env with correct credentials");
        break; // Don't retry authentication errors
      } else if (errorMessage.includes("ECONNREFUSED")) {
        console.log("[INFO] PostgreSQL server is not running or not accessible");
      }
    }
    
    retries++;
    if (retries < maxRetries && !lastError?.includes("28P01")) {
      console.log(`[INFO] Retrying in 2 seconds... (${retries}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  console.log("[ERROR] Could not establish database connection after all retries");
  console.log("");
  console.log("[HELP] Database connection troubleshooting:");
  console.log("       1. Ensure PostgreSQL is running: net start postgresql-x64-16");
  console.log("       2. Set PostgreSQL password:");
  console.log("          psql -U postgres -c \"ALTER USER postgres PASSWORD 'password';\"");
  console.log("       3. Or update DATABASE_URL in .env with your actual credentials");
  console.log("       4. Verify PostgreSQL is listening on localhost:5432");
  
  return false;
}

async function runMigrations() {
  console.log("[DB] Running database migrations...");
  
  try {
    await migrate(db, { migrationsFolder: "./migrations" });
    console.log("[SUCCESS] Database migrations completed successfully");
    return true;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("[ERROR] Migration failed:", errorMessage);
    return false;
  }
}

async function setupWindows() {
  console.log("[SETUP] Starting Windows database setup...");
  console.log("================================");
  
  try {
    // Step 1: Check PostgreSQL service
    const serviceOk = await checkPostgreSQLService();
    if (!serviceOk) {
      console.log("");
      console.log("📋 Manual steps required:");
      console.log("1. Install PostgreSQL from: https://www.postgresql.org/download/windows/");
      console.log("2. Start PostgreSQL service: net start postgresql-x64-15");
      console.log("3. Run this script again");
      process.exit(1);
    }
    
    // Step 2: Test connection
    const connectionOk = await testDatabaseConnection();
    if (!connectionOk) {
      console.log("");
      console.log("📋 Database connection troubleshooting:");
      console.log("1. Verify PostgreSQL is installed and running");
      console.log("2. Check that the password is 'password' or update DATABASE_URL in .env");
      console.log("3. Ensure PostgreSQL is listening on localhost:5432");
      process.exit(1);
    }
    
    // Step 3: Create database if needed
    await createDatabaseIfNotExists();
    
    // Step 4: Run migrations
    const migrationsOk = await runMigrations();
    if (!migrationsOk) {
      console.log("❌ Setup failed during migrations");
      process.exit(1);
    }
    
    console.log("");
    console.log("🎉 Windows database setup completed successfully!");
    console.log("===============================================");
    console.log("");
    console.log("🔗 Next steps:");
    console.log("   • Start development: bun run dev:windows");
    console.log("   • Or use setup script: .\\scripts\\start-dev.ps1");
    console.log("");
    console.log("🗄️  Database info:");
    console.log("   • Host: localhost:5432");
    console.log("   • Database: yuyu_lolita");
    console.log("   • User: postgres");
    
  } catch (error) {
    console.error("❌ Setup failed:", error);
    process.exit(1);
  } finally {
    // Clean up connections
    try {
      await migrationClient.end();
    } catch (error) {
      // Ignore cleanup errors
    }
  }
}

// Run setup if this file is executed directly
if (import.meta.main) {
  setupWindows();
}

export { setupWindows };