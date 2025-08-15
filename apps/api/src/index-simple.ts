import { Elysia } from 'elysia';
import { swagger } from '@elysiajs/swagger';
import { cors } from '@elysiajs/cors';

// Simple mock data for development
const mockConfig = {
  kurs: 13.5,
  commission: 0.1
};

const mockOrders: any[] = [
  {
    id: 'order_1704067200000',
    nomerok: 'YL123456',
    customerName: 'Анна Петрова',
    customerPhone: '+7 (999) 123-45-67',
    customerEmail: 'anna@example.com',
    deliveryAddress: 'г. Москва, ул. Ленина, д. 10, кв. 5',
    deliveryMethod: 'СДЭК',
    paymentMethod: 'Банковская карта',
    status: 'CONFIRMED',
    goods: [
      {
        name: 'Платье Sweet Lolita розовое',
        priceYuan: 200,
        quantity: 1,
        color: 'Розовый',
        size: 'M'
      }
    ],
    totalRuble: 2750,
    createdAt: '2024-01-01T10:00:00Z',
    updatedAt: '2024-01-02T14:30:00Z'
  },
  {
    id: 'order_1704153600000',
    nomerok: 'YL789012',
    customerName: 'Мария Сидорова',
    customerPhone: '+7 (888) 987-65-43',
    customerEmail: 'maria@example.com',
    deliveryAddress: 'г. Санкт-Петербург, Невский пр., д. 25',
    deliveryMethod: 'Почта России',
    paymentMethod: 'СБП',
    status: 'SHIPPED',
    goods: [
      {
        name: 'Блузка Gothic Lolita чёрная',
        priceYuan: 150,
        quantity: 1,
        color: 'Чёрный',
        size: 'S'
      },
      {
        name: 'Юбка плиссированная',
        priceYuan: 120,
        quantity: 1,
        color: 'Чёрный',
        size: 'S'
      }
    ],
    totalRuble: 4050,
    createdAt: '2024-01-02T16:20:00Z',
    updatedAt: '2024-01-05T09:15:00Z'
  },
  {
    id: 'order_1704240000000',
    nomerok: 'YL345678',
    customerName: 'Екатерина Иванова',
    customerPhone: '+7 (777) 555-33-11',
    customerEmail: 'kate@example.com',
    deliveryAddress: 'г. Новосибирск, ул. Красный пр., д. 5, оф. 12',
    deliveryMethod: 'Boxberry',
    paymentMethod: 'Наличные при получении',
    status: 'CREATED',
    goods: [
      {
        name: 'Платье Classic Lolita голубое',
        priceYuan: 280,
        quantity: 1,
        color: 'Голубой',
        size: 'L'
      }
    ],
    totalRuble: 3850,
    createdAt: '2024-01-03T11:45:00Z',
    updatedAt: '2024-01-03T11:45:00Z'
  }
];

const mockStories = [
  {
    id: 'story_1',
    title: 'История о том, как я начала носить лолиту',
    link: 'my-lolita-journey',
    excerpt: 'Мой путь в мир японской субкультуры лолита начался с простого любопытства к необычной моде...',
    content: 'Полная история о том, как я познакомилась с лолитой...',
    thumbnail: null,
    publishedAt: '2024-07-01T10:00:00Z',
    createdAt: '2024-07-01T10:00:00Z',
    author: {
      id: 'user_1',
      name: 'Юлия',
      email: 'yulia@example.com'
    }
  },
  {
    id: 'story_2',
    title: 'Мой первый лолита-комплект',
    link: 'first-lolita-coord',
    excerpt: 'Рассказываю о своем первом координате в стиле лолита и о том, какие ошибки я совершила...',
    content: 'Подробная история о первом координате...',
    thumbnail: null,
    publishedAt: '2024-06-28T14:30:00Z',
    createdAt: '2024-06-28T14:30:00Z',
    author: {
      id: 'user_2',
      name: 'Анна',
      email: 'anna@example.com'
    }
  },
  {
    id: 'story_3',
    title: 'Что такое Sweet Lolita?',
    link: 'what-is-sweet-lolita',
    excerpt: 'Подробный разбор одного из самых популярных направлений лолиты - Sweet Lolita стиля...',
    content: 'Полное описание Sweet Lolita стиля...',
    thumbnail: null,
    publishedAt: '2024-06-25T16:00:00Z',
    createdAt: '2024-06-25T16:00:00Z',
    author: {
      id: 'user_1',
      name: 'Юлия',
      email: 'yulia@example.com'
    }
  }
];

const app = new Elysia()
  .use(
    swagger({
      documentation: {
        info: {
          title: 'YuYu Lolita Shopping API',
          version: '1.0.0',
          description: 'API для системы заказов YuYu Lolita Shopping (Simplified)',
        },
      },
    })
  )
  .use(
    cors({
      origin: process.env.CORS_ORIGIN || ['http://localhost:5173', 'http://127.0.0.1:5173'],
      credentials: true,
    })
  )
  
  // Health check
  .get('/', () => ({
    success: true,
    message: 'YuYu Lolita Shopping API is running (Simplified)',
    version: '1.0.0-simple',
    timestamp: new Date().toISOString(),
  }))
  
  .get('/health', () => ({
    success: true,
    status: 'healthy',
    database: 'mocked',
    timestamp: new Date().toISOString(),
  }))
  
  // Config endpoints
  .get('/api/v1/config', () => ({
    success: true,
    data: { config: mockConfig },
  }))
  
  .get('/api/v1/config/kurs', () => ({
    success: true,
    data: { kurs: mockConfig.kurs },
  }))
  
  .get('/api/v1/config/faq', () => ({
    success: true,
    data: {
      faqs: [
        {
          id: 1,
          question: "Как оформить заказ?",
          answer: "Для оформления заказа выберите понравившиеся товары, заполните форму с контактными данными и способом доставки."
        },
        {
          id: 2,
          question: "Сколько времени займет доставка?",
          answer: "Доставка обычно занимает 7-14 дней в зависимости от выбранного способа доставки."
        },
        {
          id: 3,
          question: "Можно ли вернуть товар?",
          answer: "Да, возврат товара возможен в течение 14 дней с момента получения при условии сохранения товарного вида."
        }
      ]
    },
  }))
  
  // Orders endpoints
  .post('/api/v1/orders', ({ body }) => {
    const orderData = body as any;
    
    // Generate mock order
    const order = {
      id: `order_${Date.now()}`,
      nomerok: `YL${Date.now().toString().slice(-6)}`,
      customerName: orderData.customerName,
      customerPhone: orderData.customerPhone,
      customerEmail: orderData.customerEmail,
      deliveryAddress: orderData.deliveryAddress,
      deliveryMethod: orderData.deliveryMethod,
      paymentMethod: orderData.paymentMethod,
      status: 'CREATED',
      goods: orderData.goods || [],
      totalRuble: orderData.goods?.reduce((sum: number, good: any) => 
        sum + (good.quantity * good.priceYuan * mockConfig.kurs * (1 + mockConfig.commission)), 0
      ) || 0,
      createdAt: new Date().toISOString(),
    };
    
    mockOrders.push(order);
    
    return {
      success: true,
      message: 'Order created successfully',
      data: { order },
    };
  })
  
  .get('/api/v1/orders/lookup/:nomerok', ({ params: { nomerok } }) => {
    const order = mockOrders.find(o => o.nomerok === nomerok);
    
    if (!order) {
      return {
        success: false,
        error: 'NOT_FOUND',
        message: 'Order not found',
      };
    }
    
    return {
      success: true,
      data: { order },
    };
  })
  
  // Admin: Get all orders
  .get('/api/v1/admin/orders', ({ headers }) => {
    const authHeader = headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return {
        success: false,
        error: 'AUTHENTICATION_ERROR',
        message: 'Authentication required',
      };
    }
    
    // Mock admin check - in real app would verify JWT and check role
    return {
      success: true,
      data: { 
        orders: mockOrders.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      },
    };
  })
  
  // Admin: Update order status
  .patch('/api/v1/admin/orders/:id/status', ({ params: { id }, body, headers }) => {
    const authHeader = headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return {
        success: false,
        error: 'AUTHENTICATION_ERROR',
        message: 'Authentication required',
      };
    }
    
    const { status } = body as { status: string };
    const orderIndex = mockOrders.findIndex(o => o.id === id);
    
    if (orderIndex === -1) {
      return {
        success: false,
        error: 'NOT_FOUND',
        message: 'Order not found',
      };
    }
    
    mockOrders[orderIndex].status = status;
    mockOrders[orderIndex].updatedAt = new Date().toISOString();
    
    return {
      success: true,
      message: 'Order status updated successfully',
      data: { order: mockOrders[orderIndex] },
    };
  })
  
  // Auth endpoints (simplified)
  .post('/api/v1/auth/login', ({ body }) => {
    const { email, password } = body as { email: string; password: string };
    
    // Mock authentication
    if (email && password) {
      const token = `mock_token_${Date.now()}`;
      const isAdmin = email === 'admin@test.com';
      const user = {
        id: isAdmin ? 'admin_1' : 'user_1',
        email,
        name: isAdmin ? 'Admin User' : 'Test User',
        role: isAdmin ? 'ADMIN' : 'USER',
        status: 'ACTIVE',
        emailVerified: true,
        createdAt: new Date().toISOString(),
      };
      
      return {
        success: true,
        message: 'Login successful',
        data: { token, user },
      };
    }
    
    return {
      success: false,
      error: 'AUTHENTICATION_ERROR',
      message: 'Invalid credentials',
    };
  })
  
  .post('/api/v1/auth/register', ({ body }) => {
    const userData = body as any;
    
    const user = {
      id: `user_${Date.now()}`,
      email: userData.email,
      name: userData.name,
      role: 'USER',
      status: 'PENDING',
      emailVerified: false,
      createdAt: new Date().toISOString(),
    };
    
    return {
      success: true,
      message: 'User registered successfully. Please check your email for verification.',
      data: { user },
    };
  })
  
  .get('/api/v1/auth/me', ({ headers }) => {
    const authHeader = headers.authorization;
    
    if (authHeader && authHeader.startsWith('Bearer ')) {
      // Mock admin user check - in real app would decode JWT
      const token = authHeader.replace('Bearer ', '');
      const isAdmin = token.includes('admin'); // Simple mock check
      
      const user = {
        id: isAdmin ? 'admin_1' : 'user_1',
        email: isAdmin ? 'admin@test.com' : 'test@example.com',
        name: isAdmin ? 'Admin User' : 'Test User',
        role: isAdmin ? 'ADMIN' : 'USER',
        status: 'ACTIVE',
        emailVerified: true,
        createdAt: new Date().toISOString(),
      };
      
      return {
        success: true,
        data: { user },
      };
    }
    
    return {
      success: false,
      error: 'AUTHENTICATION_ERROR',
      message: 'Authentication required',
    };
  })
  
  // Stories endpoints (mock)
  .get('/api/v1/stories', ({ query }) => {
    const page = parseInt(query.page as string) || 1;
    const limit = parseInt(query.limit as string) || 10;
    const offset = (page - 1) * limit;
    
    const total = mockStories.length;
    const totalPages = Math.ceil(total / limit);
    const stories = mockStories.slice(offset, offset + limit);
    
    return {
      success: true,
      data: {
        stories,
        pagination: {
          page,
          limit,
          total,
          totalPages,
          hasNext: page < totalPages,
          hasPrev: page > 1,
        },
      },
    };
  })
  
  .get('/api/v1/stories/:link', ({ params: { link } }) => {
    const story = mockStories.find(s => s.link === link);
    
    if (!story) {
      return {
        success: false,
        error: 'NOT_FOUND',
        message: 'Story not found',
      };
    }
    
    return {
      success: true,
      data: story,
    };
  })
  
  // 404 handler
  .onError(({ code, error, set }) => {
    if (code === 'NOT_FOUND') {
      set.status = 404;
      return {
        success: false,
        error: 'NOT_FOUND',
        message: 'The requested resource does not exist',
      };
    }
    
    console.error('API Error:', error);
    set.status = 500;
    return {
      success: false,
      error: 'INTERNAL_ERROR',
      message: 'Internal server error',
    };
  });

// Start server
const port = process.env.API_PORT || 3001;
const host = process.env.API_HOST || 'localhost';

app.listen(port, () => {
  console.log(`🚀 YuYu Lolita Shopping API (Simplified) is running on http://${host}:${port}`);
  console.log(`📚 Swagger documentation: http://${host}:${port}/swagger`);
});

export default app;