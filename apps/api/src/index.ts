import { Elysia } from "elysia";
import { swagger } from "@elysiajs/swagger";
import { cors } from "@elysiajs/cors";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";

// MySQL8 Native Database
import { createConnection, getPool } from "@lolita-fashion/db";
import type { DatabaseConfig } from "@lolita-fashion/db";

// Import routes
import { authRoutes } from "./routes/auth";
import { userRoutes } from "./routes/users";
import { orderRoutes } from "./routes/orders";
import { subscriptionRoutes } from "./routes/subscriptions";
import { healthRoutes } from "./routes/health";
import { configRoutes } from "./routes/config";
import { adminRoutes } from "./routes/admin";
import { profileRoutes } from "./routes/profile";
import { errorHandler } from "./middleware/error";
import { enhancedRequestLogger } from "./middleware/request-logger";

// Configuration with MySQL8
console.log("🚀 YuYu Lolita Shopping API - MySQL8 Native");
console.log("====================================================");
console.log("🐬 Running with Native MySQL8 Database");
console.log("✅ No ORM - Pure MySQL2 implementation");
console.log("====================================================");

// Database configuration
const dbConfig: DatabaseConfig = {
  host: process.env.DB_HOST || "localhost",
  port: parseInt(process.env.DB_PORT || "3306"),
  database: process.env.DB_NAME || "yuyu_lolita",
  user: process.env.DB_USER || "root",
  password: process.env.DB_PASSWORD || ""
};

// Initialize MySQL connection
const connection = createConnection(dbConfig);

const app = new Elysia()
  .use(enhancedRequestLogger)
  .use(errorHandler)
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-key-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())
  .use(
    swagger({
      documentation: {
        info: {
          title: "YuYu Lolita Shopping API (MySQL8)",
          version: "2.0.0-mysql",
          description: "Native MySQL8 API without ORM - Pure SQL implementation"
        },
        tags: [
          { name: "Auth", description: "Authentication endpoints" },
          { name: "Config", description: "Configuration and settings endpoints" },
          { name: "Profile", description: "User profile management" },
          { name: "Orders", description: "Order management" },
          { name: "Users", description: "User management" },
          { name: "Subscriptions", description: "Subscription management" },
          { name: "Admin", description: "Admin management endpoints (Admin only)" },
          { name: "Health", description: "Health check endpoints" }
        ],
      },
    }),
  )
  .use(
    cors({
      origin: process.env.CORS_ORIGIN || "http://localhost:5173",
      methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
      allowedHeaders: ["Content-Type", "Authorization"],
      credentials: true,
    }),
  )
  
  // API routes
  .use(authRoutes)
  .use(userRoutes)
  .use(profileRoutes)
  .use(orderRoutes)
  .use(subscriptionRoutes)
  .use(healthRoutes)
  .use(configRoutes)
  .use(adminRoutes)

  // Initialize database connection on startup
  .onStart(async () => {
    try {
      const pool = await connection.connect();
      console.log("✅ MySQL8 connection established successfully");
      
      // Test connection
      await pool.execute("SELECT 1");
      console.log("✅ MySQL8 database connectivity verified");
    } catch (error) {
      console.error("❌ Failed to connect to MySQL8:", error);
      process.exit(1);
    }
  })

  .onStop(async () => {
    try {
      await connection.disconnect();
      console.log("✅ MySQL8 connection closed gracefully");
    } catch (error) {
      console.error("❌ Error closing MySQL8 connection:", error);
    }
  });

// Start server only if not in test mode
if (process.env.NODE_ENV !== "test") {
  const port = parseInt(process.env.API_PORT || "3001");
  const host = process.env.API_HOST || "localhost";

  try {
    // Try Bun first (if available)
    app.listen(port, () => {
      console.log(`🚀 YuYu API Server running on http://${host}:${port}`);
      console.log(`📚 API Documentation: http://${host}:${port}/swagger`);
      console.log(`🐬 Database: MySQL8 Native (No ORM)`);
    });
  } catch (error) {
    // Fallback to Node.js adapter
    console.log("💡 Falling back to Node.js adapter...");
    try {
      const elysiaNode = require("@elysiajs/node");
      const serve = elysiaNode.default || elysiaNode.serve;
      
      if (typeof serve === 'function') {
        serve({
          fetch: app.fetch,
          port,
          hostname: host,
        });
        
        console.log(`🚀 YuYu API Server running on http://${host}:${port}`);
        console.log(`📚 API Documentation: http://${host}:${port}/swagger`);
        console.log(`🐬 Database: MySQL8 Native (No ORM)`);
      } else {
        console.error("❌ Node.js adapter not available. Please use the standalone index-node.ts file");
        process.exit(1);
      }
    } catch (nodeError) {
      console.error("❌ Failed to load Node.js adapter:", nodeError);
      console.log("💡 Please run: npx tsx src/index-node.ts");
      process.exit(1);
    }
  }
}

export default app;
export type App = typeof app;
