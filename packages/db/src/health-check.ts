// MySQL8 Health Check
import { getPool } from "./connection";

interface HealthCheckResult {
  status: "healthy" | "unhealthy";
  message: string;
  details?: {
    database?: string;
    uptime?: number;
    version?: string;
    connections?: {
      active: number;
      idle: number;
      total: number;
    };
  };
  timestamp: string;
}

export async function checkMySQLHealth(): Promise<HealthCheckResult> {
  const timestamp = new Date().toISOString();
  
  try {
    const pool = await getPool();
    
    // Test basic connection
    const connection = await pool.getConnection();
    
    try {
      // Check if we can run a basic query
      const [rows] = await connection.execute("SELECT 1 as test");
      
      if (!rows || (rows as any[])[0]?.test !== 1) {
        return {
          status: "unhealthy",
          message: "MySQL connection test failed",
          timestamp
        };
      }
      
      // Get MySQL version
      const [versionRows] = await connection.execute("SELECT VERSION() as version");
      const version = (versionRows as any[])[0]?.version || "unknown";
      
      // Get uptime
      const [uptimeRows] = await connection.execute("SHOW GLOBAL STATUS LIKE 'Uptime'");
      const uptime = parseInt((uptimeRows as any[])[0]?.Value || "0");
      
      // Get connection statistics
      const [threadsRows] = await connection.execute(`
        SELECT 
          (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') as active,
          (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections') as max_connections
      `);
      
      const activeConnections = parseInt((threadsRows as any[])[0]?.active || "0");
      const maxConnections = parseInt((threadsRows as any[])[0]?.max_connections || "0");
      
      return {
        status: "healthy",
        message: "MySQL8 database is healthy and responsive",
        details: {
          database: "yuyu_lolita",
          uptime: uptime,
          version: version,
          connections: {
            active: activeConnections,
            idle: maxConnections - activeConnections,
            total: maxConnections
          }
        },
        timestamp
      };
      
    } finally {
      connection.release();
    }
    
  } catch (error) {
    return {
      status: "unhealthy",
      message: `MySQL8 health check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      timestamp
    };
  }
}

// CLI execution
if (require.main === module) {
  checkMySQLHealth()
    .then(result => {
      console.log(`[${result.status.toUpperCase()}] ${result.message}`);
      if (result.details) {
        console.log(`Database: ${result.details.database}`);
        console.log(`Version: ${result.details.version}`);
        console.log(`Uptime: ${result.details.uptime} seconds`);
        if (result.details.connections) {
          console.log(`Connections: ${result.details.connections.active}/${result.details.connections.total} (${result.details.connections.idle} idle)`);
        }
      }
      console.log(`Checked at: ${result.timestamp}`);
      process.exit(result.status === "healthy" ? 0 : 1);
    })
    .catch(error => {
      console.error(`[ERROR] Health check failed: ${error.message}`);
      process.exit(1);
    });
}

export default checkMySQLHealth;