import { Elysia } from 'elysia';
import { swagger } from '@elysiajs/swagger';
import { cors } from '@elysiajs/cors';
import { staticPlugin } from '@elysiajs/static';
import { jwt } from '@elysiajs/jwt';
import { cookie } from '@elysiajs/cookie';

// Import routes
import { authRoutes } from './routes/auth';
import { userRoutes } from './routes/users';
import { orderRoutes } from './routes/orders';
import { storyRoutes } from './routes/stories';
import { configRoutes } from './routes/config';
import { uploadRoutes } from './routes/uploads';

// Import middleware
import { authMiddleware } from './middleware/auth';
import { errorHandler } from './middleware/error';
import { rateLimiter } from './middleware/rateLimit';

// Import utils
import { testConnection } from '@yuyu/db';

const app = new Elysia()
  // Basic setup
  .use(
    swagger({
      documentation: {
        info: {
          title: 'YuYu Lolita Shopping API',
          version: '1.0.0',
          description: 'API для системы заказов YuYu Lolita Shopping',
        },
        tags: [
          { name: 'Auth', description: 'Аутентификация и авторизация' },
          { name: 'Users', description: 'Управление пользователями' },
          { name: 'Orders', description: 'Управление заказами' },
          { name: 'Stories', description: 'Управление историями' },
          { name: 'Config', description: 'Конфигурация системы' },
          { name: 'Uploads', description: 'Загрузка файлов' },
        ],
      },
    })
  )
  .use(
    cors({
      origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
      credentials: true,
    })
  )
  .use(
    jwt({
      name: 'jwt',
      secret: process.env.JWT_SECRET || 'your-jwt-secret-key',
      exp: '7d',
    })
  )
  .use(cookie())
  .use(
    staticPlugin({
      assets: 'public',
      prefix: '/static',
    })
  )
  
  // Global middleware
  .use(errorHandler)
  .use(rateLimiter)
  
  // Health check
  .get('/', () => ({
    success: true,
    message: 'YuYu Lolita Shopping API is running',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
  }))
  
  .get('/health', async () => {
    const dbStatus = await testConnection();
    return {
      success: true,
      status: 'healthy',
      database: dbStatus ? 'connected' : 'disconnected',
      timestamp: new Date().toISOString(),
    };
  })
  
  // API routes
  .group('/api/v1', (app) =>
    app
      .use(authRoutes)
      .use(userRoutes)
      .use(orderRoutes)
      .use(storyRoutes)
      .use(configRoutes)
      .use(uploadRoutes)
  )
  
  // 404 handler
  .onError(({ code, error, set }) => {
    if (code === 'NOT_FOUND') {
      set.status = 404;
      return {
        success: false,
        error: 'Endpoint not found',
        message: 'The requested resource does not exist',
      };
    }
    
    // Let error handler middleware handle other errors
    throw error;
  });

// Start server
const port = process.env.API_PORT || 3001;
const host = process.env.API_HOST || 'localhost';

app.listen(port, () => {
  console.log(`🚀 YuYu Lolita Shopping API is running on http://${host}:${port}`);
  console.log(`📚 Swagger documentation: http://${host}:${port}/swagger`);
});

export default app;