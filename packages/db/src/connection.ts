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

export type { DatabaseConfig, Pool };
