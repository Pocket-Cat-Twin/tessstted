import { Elysia } from "elysia";
import { getPool } from "@lolita-fashion/db";

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
  );
