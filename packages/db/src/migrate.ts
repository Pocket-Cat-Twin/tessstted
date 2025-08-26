// MySQL8 Migration System
import { getPool, getSystemPool, createConnection, type DatabaseConfig } from "./connection";
import type { Pool } from "mysql2/promise";

export class MySQLMigrator {
  private pool: Pool;

  constructor(pool: Pool) {
    this.pool = pool;
  }

  async createDatabase(databaseName: string): Promise<void> {
    console.log(`[MIGRATION] 🏗️ Creating database '${databaseName}'...`);
    
    try {
      await this.pool.execute(`CREATE DATABASE IF NOT EXISTS ${databaseName} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`);
      console.log(`[MIGRATION] ✅ Database '${databaseName}' created successfully`);
      
      // Verify database exists
      const [rows] = await this.pool.execute(`SHOW DATABASES LIKE '${databaseName}'`);
      const databases = rows as any[];
      
      if (databases.length > 0) {
        console.log(`[MIGRATION] ✅ Verified database '${databaseName}' exists`);
      } else {
        throw new Error(`Database '${databaseName}' was not created`);
      }
    } catch (error) {
      console.error(`[MIGRATION] ❌ Failed to create database '${databaseName}':`, error);
      throw error;
    }
  }

  async createTables(): Promise<void> {
    console.log(`[MIGRATION] 📋 Creating database tables...`);
    
    const tables = [
      {
        name: 'users',
        sql: `CREATE TABLE IF NOT EXISTS users (
          id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
          email VARCHAR(255) UNIQUE,
          phone VARCHAR(20) UNIQUE,
          password_hash VARCHAR(255) NOT NULL,
          name VARCHAR(100) NOT NULL,
          full_name VARCHAR(200),
          registration_method ENUM("email", "phone") NOT NULL,
          role ENUM("admin", "user") DEFAULT "user",
          status ENUM("pending", "active", "blocked") DEFAULT "pending",
          email_verified BOOLEAN DEFAULT FALSE,
          phone_verified BOOLEAN DEFAULT FALSE,
          avatar TEXT,
          contact_email VARCHAR(255),
          contact_phone VARCHAR(20),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          
          INDEX idx_email (email),
          INDEX idx_phone (phone),
          INDEX idx_status (status)
        ) ENGINE=InnoDB`
      },
      {
        name: 'subscriptions',
        sql: `CREATE TABLE IF NOT EXISTS subscriptions (
          id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
          user_id CHAR(36) NOT NULL,
          tier ENUM("basic", "premium", "vip", "elite") NOT NULL,
          status ENUM("active", "expired", "cancelled") DEFAULT "active",
          expires_at TIMESTAMP NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          INDEX idx_user_id (user_id),
          INDEX idx_status (status),
          INDEX idx_expires_at (expires_at)
        ) ENGINE=InnoDB`
      },
      {
        name: 'orders',
        sql: `CREATE TABLE IF NOT EXISTS orders (
          id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
          user_id CHAR(36) NOT NULL,
          customer_id CHAR(36),
          goods TEXT NOT NULL,
          weight_kg DECIMAL(8,2) NOT NULL,
          volume_cbm DECIMAL(8,3) NOT NULL,
          total_price_cny DECIMAL(10,2) NOT NULL,
          commission_rate DECIMAL(5,4) NOT NULL,
          commission_amount DECIMAL(10,2) NOT NULL,
          final_price DECIMAL(10,2) NOT NULL,
          status ENUM("pending", "processing", "completed", "cancelled") DEFAULT "pending",
          priority_processing BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          INDEX idx_user_id (user_id),
          INDEX idx_status (status),
          INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB`
      },
      {
        name: 'blog_posts',
        sql: `CREATE TABLE IF NOT EXISTS blog_posts (
          id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
          title VARCHAR(500) NOT NULL,
          slug VARCHAR(500) UNIQUE NOT NULL,
          content LONGTEXT NOT NULL,
          excerpt TEXT,
          status ENUM("draft", "published") DEFAULT "draft",
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          
          INDEX idx_slug (slug),
          INDEX idx_status (status)
        ) ENGINE=InnoDB`
      },
      {
        name: 'stories',
        sql: `CREATE TABLE IF NOT EXISTS stories (
          id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
          title VARCHAR(500) NOT NULL,
          link VARCHAR(500) UNIQUE NOT NULL,
          content LONGTEXT NOT NULL,
          status ENUM("draft", "published") DEFAULT "draft",
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          
          INDEX idx_link (link),
          INDEX idx_status (status)
        ) ENGINE=InnoDB`
      }
    ];

    for (const table of tables) {
      try {
        console.log(`[MIGRATION] 🔨 Creating table '${table.name}'...`);
        await this.pool.execute(table.sql);
        console.log(`[MIGRATION] ✅ Table '${table.name}' created successfully`);
      } catch (error) {
        console.error(`[MIGRATION] ❌ Failed to create table '${table.name}':`, error);
        throw error;
      }
    }

    console.log(`[MIGRATION] ✅ All tables created successfully`);
  }
}

export const runMigrations = async (): Promise<void> => {
  console.log("[MIGRATION] 🚀 Starting database migration process...");
  
  // Get database configuration from environment
  const dbConfig: DatabaseConfig = {
    host: process.env.DB_HOST || "localhost",
    port: parseInt(process.env.DB_PORT || "3306"),
    database: process.env.DB_NAME || "yuyu_lolita",
    user: process.env.DB_USER || "root",
    password: process.env.DB_PASSWORD || ""
  };
  
  console.log(`[MIGRATION] 🔧 Database config:`);
  console.log(`[MIGRATION] 📍 Host: ${dbConfig.host}:${dbConfig.port}`);
  console.log(`[MIGRATION] 📂 Database: ${dbConfig.database}`);
  console.log(`[MIGRATION] 👤 User: ${dbConfig.user}`);
  
  let systemPool: Pool | null = null;
  let databasePool: Pool | null = null;
  
  try {
    // Step 1: Connect to MySQL server without specifying database
    console.log("[MIGRATION] 🔌 Phase 1: Connecting to MySQL server...");
    systemPool = await getSystemPool({
      host: dbConfig.host,
      port: dbConfig.port,
      user: dbConfig.user,
      password: dbConfig.password
    });
    
    // Step 2: Create database using system connection
    console.log("[MIGRATION] 🔌 Phase 2: Creating database...");
    const systemMigrator = new MySQLMigrator(systemPool);
    await systemMigrator.createDatabase(dbConfig.database);
    
    // Step 3: Connect to specific database
    console.log(`[MIGRATION] 🔌 Phase 3: Connecting to database '${dbConfig.database}'...`);
    
    // Initialize database-specific connection
    createConnection(dbConfig);
    databasePool = await getPool();
    
    console.log(`[MIGRATION] ✅ Connected to database '${dbConfig.database}' successfully`);
    
    // Step 4: Create tables using database connection
    console.log("[MIGRATION] 🔌 Phase 4: Creating tables...");
    const databaseMigrator = new MySQLMigrator(databasePool);
    await databaseMigrator.createTables();
    
    console.log("[MIGRATION] 🎉 Migration completed successfully!");
    console.log(`[MIGRATION] 📊 Database '${dbConfig.database}' is ready for use`);
    
  } catch (error) {
    console.error("[MIGRATION] ❌ Migration failed:", error);
    throw error;
  } finally {
    // Cleanup connections
    try {
      if (systemPool) {
        console.log("[MIGRATION] 🧹 Closing system connection...");
        await systemPool.end();
      }
    } catch (error) {
      console.warn("[MIGRATION] ⚠️ Warning: Failed to close system connection:", error);
    }
  }
};
