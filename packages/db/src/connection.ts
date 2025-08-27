// Native MySQL8 Connection Pool
import mysql from "mysql2/promise";
import type { PoolOptions, Pool } from "mysql2/promise";
import { 
  getDatabaseConfig, 
  getExtendedDatabaseConfig, 
  getSystemDatabaseConfig, 
  testDatabaseConfig,
  ConfigurationError,
  type DatabaseConfig 
} from "./config.js";

class MySQLConnection {
  private pool: Pool | null = null;
  private config: DatabaseConfig;

  constructor(config: DatabaseConfig) {
    this.config = config;
  }

  async connect(): Promise<Pool> {
    if (this.pool) {
      return this.pool;
    }

    console.log(`[CONNECTION] 🔌 Connecting to MySQL database...`);
    console.log(`[CONNECTION] 📍 Host: ${this.config.host}:${this.config.port}`);
    console.log(`[CONNECTION] 📂 Database: ${this.config.database}`);
    console.log(`[CONNECTION] 👤 User: ${this.config.user}`);

    const extendedConfig = getExtendedDatabaseConfig();
    
    const poolOptions: PoolOptions = {
      host: this.config.host,
      port: this.config.port,
      database: this.config.database,
      user: this.config.user,
      password: this.config.password,
      waitForConnections: extendedConfig.waitForConnections,
      connectionLimit: extendedConfig.connectionLimit,
      queueLimit: extendedConfig.queueLimit,
      charset: extendedConfig.charset,
      multipleStatements: false // Security: disable by default
    };

    try {
      this.pool = mysql.createPool(poolOptions);
      
      // Test the pool with a simple query
      console.log(`[CONNECTION] 🧪 Testing database connection...`);
      const connection = await this.pool.getConnection();
      const [rows] = await connection.execute('SELECT 1 as test, DATABASE() as current_db, USER() as current_user');
      const testResult = (rows as any[])[0];
      
      console.log(`[CONNECTION] ✅ Database connection successful!`);
      console.log(`[CONNECTION] 📂 Current Database: ${testResult.current_db}`);
      console.log(`[CONNECTION] 👤 Current User: ${testResult.current_user}`);
      
      connection.release();
      return this.pool;
      
    } catch (error) {
      console.error(`[CONNECTION] ❌ Database connection failed:`, error);
      
      if (this.pool) {
        await this.pool.end();
        this.pool = null;
      }
      
      // Provide helpful error guidance
      if (error instanceof Error) {
        if (error.message.includes('ENOTFOUND')) {
          throw new ConfigurationError(
            `Database host '${this.config.host}' not found.\n` +
            `Please check:\n` +
            `1. MySQL server is running\n` +
            `2. Host name is correct in .env file (DB_HOST=${this.config.host})\n` +
            `3. Network connectivity to the database server`
          );
        } else if (error.message.includes('ECONNREFUSED')) {
          throw new ConfigurationError(
            `Connection refused to ${this.config.host}:${this.config.port}.\n` +
            `Please check:\n` +
            `1. MySQL server is running\n` +
            `2. MySQL is listening on port ${this.config.port}\n` +
            `3. Windows Firewall is not blocking MySQL port ${this.config.port}`
          );
        } else if (error.message.includes('Access denied')) {
          throw new ConfigurationError(
            `Access denied for user '${this.config.user}'@'${this.config.host}'.\n` +
            `Please check your .env file:\n` +
            `1. DB_USER=${this.config.user} is correct\n` +
            `2. DB_PASSWORD is correct (not empty)\n` +
            `3. MySQL user account exists and has proper permissions`
          );
        } else if (error.message.includes('Unknown database')) {
          throw new ConfigurationError(
            `Database '${this.config.database}' does not exist.\n` +
            `Please:\n` +
            `1. Run: npm run db:migrate:windows\n` +
            `2. Or create manually: CREATE DATABASE ${this.config.database};`
          );
        }
      }
      
      throw new ConfigurationError(`Database connection failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async disconnect(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
      this.pool = null;
    }
  }

  getPool(): Pool | null {
    return this.pool;
  }
}

// Default connection instance
let dbConnection: MySQLConnection | null = null;

/**
 * Creates database connection with provided config
 * @deprecated Use createConnectionWithConfig() for explicit config or initializeConnection() for auto-config
 */
export const createConnection = (config: DatabaseConfig): MySQLConnection => {
  console.log(`[CONNECTION] 🔄 Creating database connection...`);
  dbConnection = new MySQLConnection(config);
  return dbConnection;
};

/**
 * Creates database connection with explicit configuration
 */
export const createConnectionWithConfig = (config: DatabaseConfig): MySQLConnection => {
  console.log(`[CONNECTION] 🔄 Creating database connection with explicit config...`);
  dbConnection = new MySQLConnection(config);
  return dbConnection;
};

/**
 * Initializes database connection using environment configuration
 * This is the preferred method for most use cases
 */
export const initializeConnection = (): MySQLConnection => {
  console.log(`[CONNECTION] 🔄 Initializing database connection from environment...`);
  const config = getDatabaseConfig();
  dbConnection = new MySQLConnection(config);
  return dbConnection;
};

/**
 * Gets the current connection instance
 */
export const getConnection = (): MySQLConnection | null => {
  return dbConnection;
};

/**
 * Gets connection pool, automatically initializing if needed
 */
export const getPool = async (): Promise<Pool> => {
  if (!dbConnection) {
    console.log(`[CONNECTION] ⚠️ Connection not initialized, auto-initializing from environment...`);
    initializeConnection();
  }
  
  if (!dbConnection) {
    throw new ConfigurationError(
      `Database connection initialization failed.\n` +
      `Please check your .env file contains:\n` +
      `DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD`
    );
  }
  
  return await dbConnection.connect();
};

/**
 * System-level MySQL connection (without database specified) for migrations
 * Uses environment configuration automatically
 */
export const getSystemPool = async (): Promise<Pool> => {
  const config = getSystemDatabaseConfig();
  
  console.log("[SYSTEM] 🔌 Connecting to MySQL server (system level)...");
  console.log(`[SYSTEM] 📍 Host: ${config.host}:${config.port}`);
  console.log(`[SYSTEM] 👤 User: ${config.user}`);
  
  const poolOptions: PoolOptions = {
    host: config.host,
    port: config.port,
    // No database specified - connect to MySQL server directly
    user: config.user,
    password: config.password,
    waitForConnections: true,
    connectionLimit: 5, // Smaller pool for system operations
    queueLimit: 0,
    charset: "utf8mb4",
    multipleStatements: true // Enable for migrations
  };

  try {
    const pool = mysql.createPool(poolOptions);
    
    // Test the connection
    console.log("[SYSTEM] 🧪 Testing MySQL server connection...");
    const connection = await pool.getConnection();
    const [rows] = await connection.execute('SELECT VERSION() as version, DATABASE() as current_db, USER() as current_user');
    const versionInfo = (rows as any[])[0];
    
    console.log(`[SYSTEM] ✅ Connected to MySQL server successfully!`);
    console.log(`[SYSTEM] 🗄️ MySQL Version: ${versionInfo.version}`);
    console.log(`[SYSTEM] 📂 Current Database: ${versionInfo.current_db || 'none (system level)'}`);
    console.log(`[SYSTEM] 👤 Current User: ${versionInfo.current_user}`);
    
    connection.release();
    return pool;
  } catch (error) {
    console.error("[SYSTEM] ❌ Failed to connect to MySQL server:", error);
    
    if (error instanceof Error) {
      if (error.message.includes('Access denied')) {
        throw new ConfigurationError(
          `System-level MySQL access denied for user '${config.user}'.\n` +
          `Please check:\n` +
          `1. DB_USER and DB_PASSWORD in .env file\n` +
          `2. MySQL user '${config.user}' has CONNECT privileges\n` +
          `3. User can connect from 'localhost'`
        );
      }
    }
    
    throw new ConfigurationError(`System database connection failed: ${error instanceof Error ? error.message : String(error)}`);
  }
};

/**
 * Legacy system pool function with explicit config
 * @deprecated Use getSystemPool() for automatic environment configuration
 */
export const getSystemPoolWithConfig = async (config: Omit<DatabaseConfig, 'database'>): Promise<Pool> => {
  console.log("[SYSTEM] ⚠️ Using deprecated getSystemPoolWithConfig, consider using getSystemPool() instead");
  
  const poolOptions: PoolOptions = {
    host: config.host,
    port: config.port,
    user: config.user,
    password: config.password,
    waitForConnections: true,
    connectionLimit: 5,
    queueLimit: 0,
    charset: "utf8mb4",
    multipleStatements: true
  };

  try {
    const pool = mysql.createPool(poolOptions);
    const connection = await pool.getConnection();
    const [rows] = await connection.execute('SELECT VERSION() as version');
    const versionInfo = (rows as any[])[0];
    
    console.log(`[SYSTEM] ✅ Legacy system connection successful (MySQL ${versionInfo.version})`);
    connection.release();
    return pool;
  } catch (error) {
    throw new ConfigurationError(`Legacy system connection failed: ${error instanceof Error ? error.message : String(error)}`);
  }
};

/**
 * Tests database connectivity without creating persistent connection
 */
export const testConnection = async (): Promise<void> => {
  console.log(`[CONNECTION] 🧪 Running connection test...`);
  await testDatabaseConfig();
  console.log(`[CONNECTION] ✅ Connection test passed`);
};

/**
 * Closes all database connections
 */
export const closeAllConnections = async (): Promise<void> => {
  if (dbConnection) {
    console.log(`[CONNECTION] 🧹 Closing database connection...`);
    await dbConnection.disconnect();
    dbConnection = null;
  }
};

// Re-export types and configuration functions
export type { DatabaseConfig, Pool };
export { ConfigurationError, getDatabaseConfig, getExtendedDatabaseConfig, testDatabaseConfig };
