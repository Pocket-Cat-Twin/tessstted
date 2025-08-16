import { Elysia } from "elysia";
import { swagger } from "@elysiajs/swagger";
import { cors } from "@elysiajs/cors";
import { staticPlugin } from "@elysiajs/static";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";

// Import routes
import { authRoutes } from "./routes/auth";
import { authV2Routes } from "./routes/auth-v2";
import { userRoutes } from "./routes/users";
import { profileRoutes } from "./routes/profile";
import { orderRoutes } from "./routes/orders";
import { subscriptionRoutes } from "./routes/subscriptions";
import { notificationRoutes } from "./routes/notifications";
import { storageRoutes } from "./routes/storage";
import { schedulerRoutes } from "./routes/scheduler";
import { storyRoutes } from "./routes/stories";
import { blogRoutes } from "./routes/blog";
import { faqRoutes } from "./routes/faq";
import { adminStatsRoutes } from "./routes/admin-stats";
import { configRoutes } from "./routes/config";
import { uploadRoutes } from "./routes/uploads";
import { monitoringRoutes } from "./routes/monitoring";
import { cleanupRoutes } from "./routes/cleanup";
import { backupRoutes } from "./routes/backup";

// Import middleware
import { authMiddleware } from "./middleware/auth";
import { errorHandler } from "./middleware/error";
import { rateLimiter } from "./middleware/rateLimit";
import { loggingMiddleware } from "./middleware/logging";

// Import utils
import { testConnection } from "@yuyu/db";
import { startMetricsMonitoring } from "./services/monitoring";
import { scheduleCleanup } from "./services/cleanup";
import { scheduleBackups } from "./services/backup";

const app = new Elysia()
  // Basic setup
  .use(
    swagger({
      documentation: {
        info: {
          title: "YuYu Lolita Shopping API",
          version: "1.0.0",
          description: "API для системы заказов YuYu Lolita Shopping",
        },
        tags: [
          { name: "Auth", description: "Аутентификация и авторизация" },
          {
            name: "Auth V2",
            description: "Расширенная аутентификация (email/phone)",
          },
          { name: "Users", description: "Управление пользователями" },
          { name: "Profile", description: "Профиль пользователя и адреса" },
          { name: "Orders", description: "Управление заказами" },
          { name: "Subscriptions", description: "Управление подписками" },
          { name: "Notifications", description: "Управление уведомлениями" },
          { name: "Storage", description: "Управление хранением товаров" },
          { name: "Scheduler", description: "Планировщик задач" },
          { name: "Stories", description: "Управление историями" },
          { name: "Blog", description: "Блог - категории и теги" },
          { name: "FAQ", description: "Часто задаваемые вопросы" },
          { name: "Admin", description: "Административная панель" },
          { name: "Statistics", description: "Статистика и аналитика" },
          { name: "Config", description: "Конфигурация системы" },
          { name: "Uploads", description: "Загрузка файлов" },
        ],
      },
    }),
  )
  .use(
    cors({
      origin: process.env.CORS_ORIGIN 
        ? process.env.CORS_ORIGIN.split(',').map(url => url.trim()) 
        : ["http://localhost:5173", "https://yuyu.su", "http://yuyu.su"],
      credentials: true,
    }),
  )
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "your-jwt-secret-key",
      exp: "7d",
    }),
  )
  .use(cookie())
  .use(
    staticPlugin({
      assets: "public",
      prefix: "/static",
    }),
  )

  // Global middleware (order matters!)
  .use(loggingMiddleware) // Must be first to capture all requests
  .use(errorHandler)
  .use(rateLimiter)

  // Health check
  .get("/", () => ({
    success: true,
    message: "YuYu Lolita Shopping API is running",
    version: "1.0.0",
    timestamp: new Date().toISOString(),
  }))

  .get("/health", async () => {
    const dbStatus = await testConnection();
    return {
      success: true,
      status: "healthy",
      database: dbStatus ? "connected" : "disconnected",
      timestamp: new Date().toISOString(),
    };
  })

  // API routes
  .group("/api/v1", (app) =>
    app
      .use(authRoutes)
      .use(authV2Routes)
      .use(userRoutes)
      .use(profileRoutes)
      .use(orderRoutes)
      .use(subscriptionRoutes)
      .use(notificationRoutes)
      .use(storageRoutes)
      .use(schedulerRoutes)
      .use(storyRoutes)
      .use(blogRoutes)
      .use(faqRoutes)
      .use(adminStatsRoutes)
      .use(configRoutes)
      .use(uploadRoutes)
      .use(monitoringRoutes)
      .use(cleanupRoutes)
      .use(backupRoutes),
  )

  // 404 handler
  .onError(({ code, error, set }) => {
    if (code === "NOT_FOUND") {
      set.status = 404;
      return {
        success: false,
        error: "Endpoint not found",
        message: "The requested resource does not exist",
      };
    }

    // Let error handler middleware handle other errors
    throw error;
  });

// Start server only if not in test mode
if (process.env.NODE_ENV !== "test") {
  // Port configuration with explicit validation and fallbacks
  const rawApiPort = process.env.API_PORT;
  const rawPort = process.env.PORT;
  
  // Priority: API_PORT > 3001 (ignore generic PORT for API server)
  let port = 3001; // Default API port
  
  if (rawApiPort) {
    const parsedApiPort = parseInt(rawApiPort, 10);
    if (!isNaN(parsedApiPort) && parsedApiPort > 0 && parsedApiPort <= 65535) {
      port = parsedApiPort;
    } else {
      console.warn(`⚠️  Invalid API_PORT value: ${rawApiPort}, using default: 3001`);
    }
  }
  
  // Ensure we never use web ports (5173, 3000, 4173, etc.)
  const webPorts = [5173, 3000, 4173, 5000, 8080];
  if (webPorts.includes(port)) {
    console.error(`❌ ERROR: API server cannot use web port ${port}. This port is reserved for web applications.`);
    console.error(`   API_PORT environment variable: ${rawApiPort}`);
    console.error(`   PORT environment variable: ${rawPort}`);
    console.error(`   Using default API port: 3001 instead`);
    port = 3001;
  }

  const host = process.env.API_HOST || "0.0.0.0";

  // Additional validation
  if (typeof port !== 'number' || port < 1 || port > 65535) {
    console.error(`❌ ERROR: Invalid port number: ${port}`);
    console.error(`   Setting port to default: 3001`);
    port = 3001;
  }

  console.log(`🔧 API Server Configuration:`);
  console.log(`   NODE_ENV: ${process.env.NODE_ENV || 'undefined'}`);
  console.log(`   API_PORT env: ${rawApiPort || 'undefined'}`);
  console.log(`   PORT env: ${rawPort || 'undefined'}`);
  console.log(`   Selected port: ${port}`);
  console.log(`   Host: ${host}`);
  console.log('');

  app.listen(port, () => {
    console.log(
      `🚀 YuYu Lolita Shopping API is running on http://${host}:${port}`,
    );
    console.log(`📚 Swagger documentation: http://${host}:${port}/swagger`);
    console.log(
      `📊 Monitoring endpoints: http://${host}:${port}/api/v1/monitoring`,
    );
    console.log(`🧹 Cleanup endpoints: http://${host}:${port}/api/v1/cleanup`);
    console.log(`💾 Backup endpoints: http://${host}:${port}/api/v1/backup`);

    // Start metrics monitoring
    startMetricsMonitoring();

    // Start automatic cleanup scheduling
    scheduleCleanup();

    // Start automatic backup scheduling
    scheduleBackups();
  });
}

export default app;
