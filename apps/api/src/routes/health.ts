import { Elysia } from "elysia";
import { getPool, checkMySQLHealth } from "@lolita-fashion/db";
import { ApiHealthMonitor } from "../middleware/request-logger";

export const healthRoutes = new Elysia({ prefix: "/health" })

  // Basic Health Check
  .get(
    "/",
    async () => {
      try {
        const pool = await getPool();
        await pool.execute("SELECT 1");
        
        return {
          status: "healthy",
          database: "MySQL8 Connected",
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        return {
          status: "unhealthy", 
          database: "MySQL8 Connection Failed",
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        };
      }
    },
    {
      detail: {
        tags: ["Health"],
        summary: "Health check",
        description: "Check API and MySQL8 database health",
      },
    },
  )

  // Database Health Check
  .get(
    "/db",
    async () => {
      try {
        const pool = await getPool();
        
        // Test basic connection
        await pool.execute("SELECT 1");
        
        // Test table existence
        const [tables] = await pool.execute(`
          SELECT COUNT(*) as table_count 
          FROM information_schema.tables 
          WHERE table_schema = DATABASE()
        `);
        
        const tableCount = (tables as any)[0].table_count;

        return {
          status: "healthy",
          database: {
            type: "MySQL8",
            connected: true,
            tables: Number(tableCount),
          },
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        return {
          status: "unhealthy",
          database: {
            type: "MySQL8", 
            connected: false,
            error: error instanceof Error ? error.message : "Unknown error",
          },
          timestamp: new Date().toISOString(),
        };
      }
    },
    {
      detail: {
        tags: ["Health"],
        summary: "Database health check",
        description: "Detailed MySQL8 database health information",
      },
    },
  )

  // Detailed Health Check
  .get(
    "/detailed",
    async () => {
      const healthResult = await checkMySQLHealth();
      return {
        api: {
          status: "healthy",
          timestamp: new Date().toISOString(),
        },
        database: healthResult,
      };
    },
    {
      detail: {
        tags: ["Health"],
        summary: "Detailed health check", 
        description: "Comprehensive health check including MySQL8 database details",
      },
    },
  )

  // API Monitoring and Stats
  .get(
    "/monitoring",
    async () => {
      try {
        const healthStats = ApiHealthMonitor.getHealthStats();
        const pool = await getPool();
        
        // Get database connection info
        const [connections] = await pool.execute(`
          SELECT COUNT(*) as active_connections 
          FROM information_schema.PROCESSLIST 
          WHERE DB = DATABASE()
        `);
        
        const activeConnections = (connections as any)[0]?.active_connections || 0;
        
        return {
          success: true,
          data: {
            api: healthStats,
            database: {
              activeConnections,
              type: "MySQL8",
            },
            system: {
              nodeVersion: process.version,
              platform: process.platform,
              memory: process.memoryUsage(),
              uptime: process.uptime(),
            },
            timestamp: new Date().toISOString(),
          },
        };
      } catch (error) {
        return {
          success: false,
          error: "MONITORING_ERROR",
          message: "Failed to fetch monitoring data",
          timestamp: new Date().toISOString(),
        };
      }
    },
    {
      detail: {
        tags: ["Health"],
        summary: "API monitoring and statistics",
        description: "Get detailed API performance monitoring, request statistics, and system health metrics",
      },
    }
  )

  // Reset monitoring stats (for development/testing)
  .post(
    "/monitoring/reset",
    async () => {
      try {
        ApiHealthMonitor.reset();
        return {
          success: true,
          message: "Monitoring statistics reset successfully",
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        return {
          success: false,
          error: "RESET_ERROR", 
          message: "Failed to reset monitoring statistics",
        };
      }
    },
    {
      detail: {
        tags: ["Health"],
        summary: "Reset monitoring statistics",
        description: "Reset API monitoring statistics (useful for development and testing)",
      },
    }
  );
