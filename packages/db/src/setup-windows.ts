// Windows-specific database initialization script
// Set UTF-8 encoding for proper Russian text display
if (process.platform === "win32") {
  try {
    process.stdout.setDefaultEncoding('utf8');
  } catch (e) {
    // Ignore encoding errors
  }
}

import { migrate } from "drizzle-orm/postgres-js/migrator";
import { migrationClient, db, ensureDatabaseHealth } from "./connection";

const isWindows = process.platform === "win32";

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

// Enhanced database connection testing with health checks
async function testDatabaseConnection() {
  console.log("[DB] Running comprehensive database health check...");
  
  const maxRetries = 3;
  let retries = 0;
  let lastError: string | null = null;
  
  while (retries < maxRetries) {
    try {
      console.log(`[INFO] Health check attempt ${retries + 1}/${maxRetries}`);
      
      const isHealthy = await ensureDatabaseHealth();
      if (isHealthy) {
        console.log("[SUCCESS] Database is healthy and ready");
        return true;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      lastError = errorMessage;
      console.log(`[ERROR] Health check ${retries + 1} failed: ${errorMessage}`);
      
      // Check for authentication errors - don't retry these
      if (errorMessage.includes("28P01") || errorMessage.includes("authentication")) {
        console.log("[CRITICAL] Authentication failed - cannot retry");
        console.log("           Fix PostgreSQL password or update .env");
        break;
      }
    }
    
    retries++;
    if (retries < maxRetries && !lastError?.includes("28P01")) {
      console.log(`[INFO] Retrying in 3 seconds... (${retries}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }
  
  console.log("[ERROR] Database health check failed after all attempts");
  console.log("");
  console.log("[HELP] Windows PostgreSQL troubleshooting:");
  console.log("       1. Check service: sc query postgresql*");
  console.log("       2. Start service: net start postgresql-x64-*");
  console.log("       3. Test connection: psql -h localhost -U postgres -d postgres");
  console.log("       4. Reset password: psql -U postgres -c \"ALTER USER postgres PASSWORD 'postgres';\"");
  console.log("       5. Update DATABASE_URL in .env if using different credentials");
  console.log("       6. Check firewall: netstat -an | findstr :5432");
  
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
      console.log("2. Check that the password is 'postgres' or update DATABASE_URL in .env");
      console.log("3. Ensure PostgreSQL is listening on localhost:5432");
      process.exit(1);
    }
    
    // Step 3: Database creation is now handled by ensureDatabaseHealth()
    // This ensures proper error handling and encoding setup
    console.log("[INFO] Database creation handled by health check");
    
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