import { Elysia } from 'elysia';
import { swagger } from '@elysiajs/swagger';
import { cors } from '@elysiajs/cors';
import { db, config, eq, orders, orderGoods, stories, users, desc } from '@yuyu/db';

// Database connection test
async function testDBConnection() {
  try {
    const result = await db.select().from(config).limit(1);
    console.log('✅ Database connection successful');
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    return false;
  }
}

const app = new Elysia()
  .use(
    swagger({
      documentation: {
        info: {
          title: 'YuYu Lolita Shopping API (DB)',
          version: '1.0.0',
          description: 'API for YuYu Lolita Shopping with database connection'
        }
      }
    })
  )
  .use(
    cors({
      origin: ['http://localhost:5173', 'http://127.0.0.1:5173'],
      credentials: true
    })
  )
  
  // Health check
  .get('/', () => ({
    success: true,
    message: 'YuYu Lolita Shopping API with DB is running',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
  }))
  
  .get('/health', async () => {
    const dbStatus = await testDBConnection();
    return {
      success: true,
      database: dbStatus ? 'connected' : 'disconnected',
      timestamp: new Date().toISOString(),
    };
  })

  // Config endpoints
  .get('/api/v1/config/kurs', async () => {
    try {
      const result = await db.select().from(config).where(eq(config.key, 'kurs')).limit(1);
      const kurs = result[0]?.value ? parseFloat(result[0].value) : 13.5;
      return { kurs };
    } catch (error) {
      return { kurs: 13.5 };
    }
  })

  .get('/api/v1/config/faq', async () => {
    try {
      const result = await db.select().from(config).where(eq(config.key, 'faq')).limit(1);
      const faq = result[0]?.value ? JSON.parse(result[0].value) : [];
      return { faq };
    } catch (error) {
      return { faq: [] };
    }
  })

  // Orders endpoints
  .get('/api/v1/orders', async () => {
    try {
      const result = await db.select({
        id: orders.id,
        nomerok: orders.nomerok,
        customerName: orders.customerName,
        customerPhone: orders.customerPhone,
        customerEmail: orders.customerEmail,
        deliveryAddress: orders.deliveryAddress,
        deliveryMethod: orders.deliveryMethod,
        paymentMethod: orders.paymentMethod,
        status: orders.status,
        totalRuble: orders.totalRuble,
        createdAt: orders.createdAt,
        updatedAt: orders.updatedAt
      }).from(orders).orderBy(desc(orders.createdAt));
      
      return result;
    } catch (error) {
      console.error('Error fetching orders:', error);
      return [];
    }
  })

  .get('/api/v1/orders/:nomerok', async ({ params }) => {
    try {
      const order = await db.select().from(orders).where(eq(orders.nomerok, params.nomerok)).limit(1);
      if (!order.length) {
        return { error: 'Order not found' };
      }
      
      const goods = await db.select().from(orderGoods).where(eq(orderGoods.orderId, order[0].id));
      
      return {
        ...order[0],
        goods
      };
    } catch (error) {
      console.error('Error fetching order:', error);
      return { error: 'Order not found' };
    }
  })

  // Stories endpoints
  .get('/api/v1/stories', async () => {
    try {
      const result = await db.select({
        id: stories.id,
        title: stories.title,
        link: stories.link,
        excerpt: stories.excerpt,
        thumbnail: stories.thumbnail,
        status: stories.status,
        publishedAt: stories.publishedAt,
        createdAt: stories.createdAt
      }).from(stories).orderBy(desc(stories.publishedAt));
      
      return result;
    } catch (error) {
      console.error('Error fetching stories:', error);
      return [];
    }
  })

  .get('/api/v1/stories/:link', async ({ params }) => {
    try {
      const story = await db.select().from(stories).where(eq(stories.link, params.link)).limit(1);
      if (!story.length) {
        return { error: 'Story not found' };
      }
      
      return story[0];
    } catch (error) {
      console.error('Error fetching story:', error);
      return { error: 'Story not found' };
    }
  })

  // Admin endpoints
  .get('/api/v1/admin/orders', async () => {
    try {
      const result = await db.select({
        id: orders.id,
        nomerok: orders.nomerok,
        customerName: orders.customerName,
        customerPhone: orders.customerPhone,
        customerEmail: orders.customerEmail,
        deliveryAddress: orders.deliveryAddress,
        deliveryMethod: orders.deliveryMethod,
        paymentMethod: orders.paymentMethod,
        status: orders.status,
        totalRuble: orders.totalRuble,
        createdAt: orders.createdAt,
        updatedAt: orders.updatedAt
      }).from(orders).orderBy(desc(orders.createdAt));
      
      return {
        success: true,
        data: {
          orders: result,
          total: result.length
        }
      };
    } catch (error) {
      console.error('Error fetching admin orders:', error);
      return {
        success: false,
        message: 'Ошибка загрузки заказов'
      };
    }
  })

  .patch('/api/v1/admin/orders/:id/status', async ({ params, body }) => {
    try {
      const { status: newStatus } = body as { status: string };
      
      // Get order details for email
      const order = await db.select().from(orders).where(eq(orders.id, params.id)).limit(1);
      
      await db.update(orders)
        .set({ 
          status: newStatus as any,
          updatedAt: new Date()
        })
        .where(eq(orders.id, params.id));
      
      // Send email notification (mock implementation)
      if (order.length > 0) {
        console.log(`📧 Email notification sent to ${order[0].customerEmail}`);
        console.log(`   Order ${order[0].nomerok} status changed to: ${newStatus}`);
      }
      
      return {
        success: true,
        message: 'Статус заказа обновлён и уведомление отправлено'
      };
    } catch (error) {
      console.error('Error updating order status:', error);
      return {
        success: false,
        message: 'Ошибка обновления статуса'
      };
    }
  })

  // Order creation endpoint
  .post('/api/v1/orders', async ({ body }) => {
    try {
      const orderData = body as any;
      
      // Generate order number
      const nomerok = 'YL' + Date.now().toString();
      
      // Create order
      const newOrder = await db.insert(orders).values({
        nomerok,
        ...orderData,
        status: 'created' as const,
        createdAt: new Date(),
        updatedAt: new Date()
      }).returning();
      
      // Send email notification (mock implementation)
      console.log(`📧 Order creation email sent to ${orderData.customerEmail}`);
      console.log(`   New order created: ${nomerok}`);
      
      return {
        success: true,
        data: newOrder[0],
        message: 'Заказ создан и уведомление отправлено'
      };
    } catch (error) {
      console.error('Error creating order:', error);
      return {
        success: false,
        message: 'Ошибка создания заказа'
      };
    }
  })

  // Auth endpoints (mock for now)
  .post('/api/v1/auth/login', async ({ body }) => {
    return {
      success: true,
      token: 'mock-jwt-token',
      user: {
        id: 'user-id',
        email: 'user@example.com',
        role: 'ADMIN'
      }
    };
  })

  .post('/api/v1/auth/register', async ({ body }) => {
    return {
      success: true,
      message: 'User registered successfully',
      user: {
        id: 'user-id',
        email: 'user@example.com',
        role: 'user'
      }
    };
  })

  // Initialize database connection
  .onStart(async () => {
    console.log('🔄 Initializing database connection...');
    await testDBConnection();
  })

  .listen(3001);

console.log('🚀 YuYu Lolita Shopping API (DB) is running on http://localhost:3001');
console.log('📚 Swagger documentation: http://localhost:3001/swagger');