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
  console.log("🗄️  Checking if database exists...");
  
  // Connect to default postgres database to create our database
  const adminConnectionString = `postgresql://${WINDOWS_PG_DEFAULTS.user}:${WINDOWS_PG_DEFAULTS.password}@${WINDOWS_PG_DEFAULTS.host}:${WINDOWS_PG_DEFAULTS.port}/${WINDOWS_PG_DEFAULTS.database}`;
  const adminClient = postgres(adminConnectionString, { max: 1 });
  
  try {
    // Check if our database exists
    const result = await adminClient`
      SELECT 1 FROM pg_database WHERE datname = 'yuyu_lolita'
    `;
    
    if (result.length === 0) {
      console.log("🔄 Creating yuyu_lolita database...");
      await adminClient`CREATE DATABASE yuyu_lolita`;
      console.log("✅ Database yuyu_lolita created successfully");
    } else {
      console.log("✅ Database yuyu_lolita already exists");
    }
  } catch (error) {
    console.error("❌ Error checking/creating database:", error);
    throw error;
  } finally {
    await adminClient.end();
  }
}

async function checkPostgreSQLService() {
  if (!isWindows) {
    console.log("ℹ️  Not running on Windows, skipping service check");
    return true;
  }
  
  console.log("🔍 Checking PostgreSQL service on Windows...");
  
  try {
    // Try to import child_process for Windows service check
    const { exec } = await import("child_process");
    const { promisify } = await import("util");
    const execAsync = promisify(exec);
    
    // Check if PostgreSQL service is running
    const { stdout } = await execAsync('sc query postgresql*');
    
    if (stdout.includes("RUNNING")) {
      console.log("✅ PostgreSQL service is running");
      return true;
    } else if (stdout.includes("STOPPED")) {
      console.log("⚠️  PostgreSQL service is stopped, attempting to start...");
      
      try {
        await execAsync('net start postgresql*');
        console.log("✅ PostgreSQL service started");
        return true;
      } catch (startError) {
        console.log("❌ Failed to start PostgreSQL service automatically");
        console.log("   Please start it manually: net start postgresql-x64-15");
        return false;
      }
    }
  } catch (error) {
    console.log("⚠️  Could not check PostgreSQL service status");
    console.log("   This is normal if PostgreSQL was installed differently");
  }
  
  return true;
}

async function testDatabaseConnection() {
  console.log("🔌 Testing database connection...");
  
  const maxRetries = 5;
  let retries = 0;
  
  while (retries < maxRetries) {
    try {
      const isConnected = await testConnection();
      if (isConnected) {
        console.log("✅ Database connection successful");
        return true;
      }
    } catch (error) {
      console.log(`❌ Connection attempt ${retries + 1} failed:`, error.message);
    }
    
    retries++;
    if (retries < maxRetries) {
      console.log(`⏳ Retrying in 2 seconds... (${retries}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  console.log("❌ Could not establish database connection after all retries");
  return false;
}

async function runMigrations() {
  console.log("🔄 Running database migrations...");
  
  try {
    await migrate(db, { migrationsFolder: "./migrations" });
    console.log("✅ Database migrations completed successfully");
    return true;
  } catch (error) {
    console.error("❌ Migration failed:", error);
    return false;
  }
}

async function setupWindows() {
  console.log("🪟 Starting Windows database setup...");
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