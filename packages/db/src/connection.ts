// Native MySQL8 Connection Pool
import mysql from "mysql2/promise";
import type { PoolOptions, Pool } from "mysql2/promise";

interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
}

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

    const poolOptions: PoolOptions = {
      host: this.config.host,
      port: this.config.port,
      database: this.config.database,
      user: this.config.user,
      password: this.config.password,
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
      charset: "utf8mb4"
    };

    this.pool = mysql.createPool(poolOptions);
    return this.pool;
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

export const createConnection = (config: DatabaseConfig): MySQLConnection => {
  dbConnection = new MySQLConnection(config);
  return dbConnection;
};

export const getConnection = (): MySQLConnection | null => {
  return dbConnection;
};

export const getPool = async (): Promise<Pool> => {
  if (!dbConnection) {
    throw new Error("Database connection not initialized");
  }
  return await dbConnection.connect();
};

// System-level MySQL connection (without database specified) for migrations
export const getSystemPool = async (config: Omit<DatabaseConfig, 'database'>): Promise<Pool> => {
  console.log("[DB] 🔌 Connecting to MySQL server...");
  console.log(`[DB] 📍 Host: ${config.host}:${config.port}`);
  console.log(`[DB] 👤 User: ${config.user}`);
  
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
    multipleStatements: true // Enable multiple SQL statements for migrations
  };

  try {
    const pool = mysql.createPool(poolOptions);
    
    // Test the connection
    console.log("[DB] 🧪 Testing MySQL server connection...");
    const connection = await pool.getConnection();
    const [rows] = await connection.execute('SELECT VERSION() as version, DATABASE() as current_db');
    const versionInfo = rows as any[];
    
    console.log(`[DB] ✅ Connected to MySQL server successfully!`);
    console.log(`[DB] 🗄️ MySQL Version: ${versionInfo[0].version}`);
    console.log(`[DB] 📂 Current Database: ${versionInfo[0].current_db || 'none (system level)'}`);
    
    connection.release();
    return pool;
  } catch (error) {
    console.error("[DB] ❌ Failed to connect to MySQL server:", error);
    throw new Error(`System database connection failed: ${error instanceof Error ? error.message : String(error)}`);
  }
};

export type { DatabaseConfig, Pool };
