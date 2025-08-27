// Database Configuration Management
// Centralized environment variable loading and validation
import dotenv from 'dotenv';
import { join } from 'path';
import { existsSync } from 'fs';

// Custom error class for configuration issues
export class ConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigurationError';
  }
}

// Database configuration interface
export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
}

// Enhanced database configuration with connection settings
export interface ExtendedDatabaseConfig extends DatabaseConfig {
  connectionLimit: number;
  waitForConnections: boolean;
  queueLimit: number;
  charset: string;
  multipleStatements: boolean;
}

/**
 * Loads environment variables from .env file
 * Searches for .env file starting from project root
 */
export const loadEnvironmentConfig = (): void => {
  // Try to find .env file starting from current directory up to project root
  const possibleEnvPaths = [
    '.env',
    '../.env',
    '../../.env',
    '../../../.env'
  ];

  let envLoaded = false;
  
  for (const envPath of possibleEnvPaths) {
    if (existsSync(envPath)) {
      console.log(`[CONFIG] 📂 Loading environment from: ${envPath}`);
      dotenv.config({ path: envPath });
      envLoaded = true;
      break;
    }
  }

  if (!envLoaded) {
    console.warn('[CONFIG] ⚠️  No .env file found, using system environment variables');
  }
};

/**
 * Validates and returns database configuration
 * Throws ConfigurationError if required variables are missing
 */
export const validateDatabaseConfig = (): DatabaseConfig => {
  // Ensure environment is loaded
  loadEnvironmentConfig();

  const requiredVars = [
    { name: 'DB_HOST', description: 'Database host (e.g., localhost)' },
    { name: 'DB_PORT', description: 'Database port (e.g., 3306)' },
    { name: 'DB_NAME', description: 'Database name (e.g., yuyu_lolita)' },
    { name: 'DB_USER', description: 'Database user (e.g., root)' },
    { name: 'DB_PASSWORD', description: 'Database password' }
  ];

  const missing = requiredVars.filter(variable => {
    const value = process.env[variable.name];
    return !value || value.trim() === '';
  });
  
  if (missing.length > 0) {
    const missingDetails = missing.map(v => `  - ${v.name}: ${v.description}`).join('\n');
    
    throw new ConfigurationError(
      `Missing required database environment variables:\n${missingDetails}\n\n` +
      `Please check your .env file and ensure all required variables are set.\n` +
      `Example .env configuration:\n` +
      `DB_HOST=localhost\n` +
      `DB_PORT=3306\n` +
      `DB_NAME=yuyu_lolita\n` +
      `DB_USER=root\n` +
      `DB_PASSWORD=your_mysql_password`
    );
  }

  // Validate port is a valid number
  const port = parseInt(process.env.DB_PORT!);
  if (isNaN(port) || port < 1 || port > 65535) {
    throw new ConfigurationError(
      `Invalid DB_PORT value: ${process.env.DB_PORT}. Must be a number between 1 and 65535.`
    );
  }

  const config: DatabaseConfig = {
    host: process.env.DB_HOST!.trim(),
    port: port,
    database: process.env.DB_NAME!.trim(),
    user: process.env.DB_USER!.trim(),
    password: process.env.DB_PASSWORD!.trim()
  };

  // Log configuration (without password)
  console.log(`[CONFIG] 🔧 Database configuration validated:`);
  console.log(`[CONFIG] 📍 Host: ${config.host}:${config.port}`);
  console.log(`[CONFIG] 📂 Database: ${config.database}`);
  console.log(`[CONFIG] 👤 User: ${config.user}`);
  console.log(`[CONFIG] 🔐 Password: ${'*'.repeat(config.password.length)} (${config.password.length} chars)`);

  return config;
};

/**
 * Returns extended database configuration with connection pool settings
 */
export const getExtendedDatabaseConfig = (): ExtendedDatabaseConfig => {
  const baseConfig = validateDatabaseConfig();
  
  return {
    ...baseConfig,
    connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT || '10'),
    waitForConnections: process.env.DB_WAIT_FOR_CONNECTIONS !== 'false',
    queueLimit: parseInt(process.env.DB_QUEUE_LIMIT || '0'),
    charset: process.env.DB_CHARSET || 'utf8mb4',
    multipleStatements: process.env.DB_MULTIPLE_STATEMENTS === 'true'
  };
};

/**
 * System-level configuration (no database specified)
 * Used for database creation and system operations
 */
export const getSystemDatabaseConfig = (): Omit<DatabaseConfig, 'database'> => {
  const config = validateDatabaseConfig();
  
  return {
    host: config.host,
    port: config.port,
    user: config.user,
    password: config.password
  };
};

/**
 * Validates that the configuration can connect to MySQL
 * Returns a promise that resolves with connection info or rejects with detailed error
 */
export const testDatabaseConfig = async (): Promise<{ version: string; currentDb: string | null }> => {
  const mysql = await import('mysql2/promise');
  const config = validateDatabaseConfig();
  
  let connection;
  
  try {
    console.log(`[CONFIG] 🧪 Testing database connection...`);
    
    connection = await mysql.createConnection({
      host: config.host,
      port: config.port,
      user: config.user,
      password: config.password,
      // Don't specify database for initial connection test
      connectTimeout: 5000,
      timeout: 5000
    });
    
    const [rows] = await connection.execute('SELECT VERSION() as version, DATABASE() as current_db');
    const result = (rows as any[])[0];
    
    console.log(`[CONFIG] ✅ Database connection test successful`);
    console.log(`[CONFIG] 🗄️  MySQL Version: ${result.version}`);
    console.log(`[CONFIG] 📂 Current Database: ${result.current_db || 'none (system level)'}`);
    
    return {
      version: result.version,
      currentDb: result.current_db
    };
    
  } catch (error) {
    console.error(`[CONFIG] ❌ Database connection test failed`);
    
    if (error instanceof Error) {
      // Provide helpful error messages based on common issues
      if (error.message.includes('ENOTFOUND')) {
        throw new ConfigurationError(
          `Database host '${config.host}' not found.\n` +
          `Please check:\n` +
          `1. MySQL server is running\n` +
          `2. Host name is correct in DB_HOST\n` +
          `3. Network connectivity to the database server`
        );
      } else if (error.message.includes('ECONNREFUSED')) {
        throw new ConfigurationError(
          `Connection refused to ${config.host}:${config.port}.\n` +
          `Please check:\n` +
          `1. MySQL server is running\n` +
          `2. MySQL is listening on port ${config.port}\n` +
          `3. Firewall is not blocking the connection`
        );
      } else if (error.message.includes('Access denied')) {
        throw new ConfigurationError(
          `Access denied for user '${config.user}'@'${config.host}'.\n` +
          `Please check:\n` +
          `1. DB_USER (${config.user}) is correct\n` +
          `2. DB_PASSWORD is correct\n` +
          `3. User has permission to connect from this host\n` +
          `4. MySQL user account exists and is not locked`
        );
      } else if (error.message.includes('Unknown database')) {
        throw new ConfigurationError(
          `Database '${config.database}' does not exist.\n` +
          `Please:\n` +
          `1. Run database migrations first\n` +
          `2. Create the database manually: CREATE DATABASE ${config.database};\n` +
          `3. Check DB_NAME is spelled correctly`
        );
      } else {
        throw new ConfigurationError(`Database connection failed: ${error.message}`);
      }
    }
    
    throw new ConfigurationError(`Database connection failed: ${String(error)}`);
  } finally {
    if (connection) {
      await connection.end();
    }
  }
};

// Export singleton configuration getter
let _cachedConfig: DatabaseConfig | null = null;

/**
 * Gets database configuration with caching
 * Validates and caches configuration on first call
 */
export const getDatabaseConfig = (): DatabaseConfig => {
  if (!_cachedConfig) {
    _cachedConfig = validateDatabaseConfig();
  }
  return _cachedConfig;
};

/**
 * Clears cached configuration (useful for testing)
 */
export const clearConfigCache = (): void => {
  _cachedConfig = null;
};