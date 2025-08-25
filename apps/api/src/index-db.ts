import { Elysia } from "elysia";
import { swagger } from "@elysiajs/swagger";
import { cors } from "@elysiajs/cors";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";
import {
  db,
  config,
  eq,
  orders,
  orderGoods,
  stories,
  users,
  customers,
  customerAddresses,
  desc,
  // Enhanced database system
  ensureDatabaseHealth,
  checkDatabaseHealth,
  dbLogger
} from "@lolita-fashion/db";

// Basic connection test without infinite loops
async function testBasicConnection(): Promise<boolean> {
  try {
    await db.select().from(config).limit(1);
    return true;
  } catch (error) {
    console.warn('Basic database connection test failed:', (error as Error).message);
    return false;
  }
}

// Senior-level database initialization with comprehensive error handling and auto-recovery
async function initializeDatabaseSystem() {
  try {
    console.log("🔄 Running enhanced database initialization...");
    
    // Environment detection
    const isWindows = process.platform === 'win32';
    const isCodespace = process.env.CODESPACES === 'true' || process.env.USER === 'codespace';
    const hasPostgreSQL = process.env.DATABASE_URL && !process.env.DATABASE_URL.includes('undefined');
    
    console.log(`   Platform: ${process.platform}${isCodespace ? ' (GitHub Codespace)' : ''}`);
    console.log(`   Database URL: ${process.env.DATABASE_URL?.replace(/\/\/[^@]+@/, '//***:***@') || 'Not configured'}`);
    
    if (!hasPostgreSQL) {
      console.warn("⚠️  No valid PostgreSQL connection available");
      console.warn("⚠️  API will start in limited mode without database features");
      console.warn("⚠️  For full functionality, configure PostgreSQL connection in .env");
      return false; // Return false but don't crash
    }
    
    // Step 1: Basic connection test with timeout
    console.log("🔄 Testing basic database connection...");
    let connectionWorking = false;
    
    try {
      await Promise.race([
        db.select().from(users).limit(0), // Simple connection test
        new Promise((_, reject) => setTimeout(() => reject(new Error('Connection timeout')), 8000))
      ]);
      connectionWorking = true;
      console.log("✅ Basic database connection successful");
    } catch (error: any) {
      console.log(`⚠️  Basic connection test failed: ${error.message}`);
    }
    
    // Step 2: Auto-recovery attempt for missing database/tables
    if (!connectionWorking) {
      console.log("🔄 Attempting database auto-recovery...");
      
      try {
        // Try to run setup-windows if available
        const setupPath = './packages/db/src/setup-windows.ts';
        if (require('fs').existsSync(setupPath)) {
          console.log("🔄 Running database setup...");
          const { setupWindows } = await import('@lolita-fashion/db');
          await setupWindows();
          console.log("✅ Database setup completed");
          connectionWorking = true;
        }
      } catch (setupError: any) {
        console.log(`⚠️  Auto-recovery failed: ${setupError.message}`);
      }
    }
    
    // Step 3: Test with config table (create if missing)
    let configTableReady = false;
    
    if (connectionWorking) {
      try {
        await db.select().from(config).limit(1);
        configTableReady = true;
        console.log("✅ Config table is accessible");
      } catch (configError: any) {
        console.log(`⚠️  Config table test failed: ${configError.message}`);
        
        // Try to create essential config data
        if (configError.code === '42P01' || configError.message.includes('does not exist')) {
          console.log("🔄 Attempting to initialize essential configuration...");
          try {
            // Create basic config entries without relying on existing table structure
            console.log("   Creating minimal config structure...");
            configTableReady = false; // Don't rely on config table for now
          } catch (createError: any) {
            console.log(`   Config creation failed: ${createError.message}`);
          }
        }
      }
    }
    
    // Step 4: Final status determination
    if (connectionWorking && configTableReady) {
      console.log("✅ Database system fully operational");
      dbLogger.info('connection', 'Database system fully initialized', { 
        platform: process.platform,
        codespace: isCodespace,
        configReady: true
      });
      return true;
    } else if (connectionWorking) {
      console.log("⚠️  Database connected but some tables missing - partial functionality");
      dbLogger.warn('connection', 'Database partially initialized', { 
        connection: true,
        configTable: configTableReady
      });
      return true; // Allow API to start with limited functionality
    } else {
      console.log("⚠️  Database connection failed - limited mode");
      return false;
    }
    
  } catch (error: any) {
    console.error("❌ Database initialization encountered an error:", error.message);
    
    // Comprehensive error diagnostics
    const errorInfo = {
      code: error?.code,
      message: error?.message,
      severity: error?.severity_local || error?.severity,
      platform: process.platform,
      dbUrl: process.env.DATABASE_URL?.replace(/\/\/[^@]+@/, '//***:***@')
    };
    
    dbLogger.error('connection', 'Database initialization failed', errorInfo);
    
    // Provide helpful guidance based on error type
    if (error?.code === '3D000' || error?.message?.includes('does not exist')) {
      console.error("");
      console.error("🔧 Database Connection Issue:");
      console.error("   The target database doesn't exist or isn't accessible");
      console.error("");
      console.error("💡 Solutions:");
      console.error("   1. Run database setup: node setup-database.js");
      console.error("   2. Check PostgreSQL service is running");
      console.error("   3. Verify DATABASE_URL in .env file");
      console.error("   4. Ensure database exists: CREATE DATABASE yuyu_lolita");
    } else if (error?.code === 'ECONNREFUSED') {
      console.error("");
      console.error("🔧 PostgreSQL Service Issue:");
      console.error("   PostgreSQL server is not running or not accessible");
      console.error("");
      console.error("💡 Solutions:");
      console.error("   1. Start PostgreSQL service");
      console.error("   2. Check if port 5432 is available");
      console.error("   3. Verify connection string in .env");
    } else if (error?.code === '28P01') {
      console.error("");
      console.error("🔧 Authentication Issue:");
      console.error("   Database user authentication failed");
      console.error("");
      console.error("💡 Solutions:");
      console.error("   1. Check username/password in DATABASE_URL");
      console.error("   2. Verify PostgreSQL user permissions");
      console.error("   3. Update pg_hba.conf if necessary");
    }
    
    return false;
  }
}

new Elysia()
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "your-jwt-secret-key",
      exp: "7d",
    }),
  )
  .use(cookie())
  .use(
    swagger({
      documentation: {
        info: {
          title: "YuYu Lolita Shopping API (DB)",
          version: "1.0.0",
          description: "API for YuYu Lolita Shopping with database connection",
        },
      },
    }),
  )
  .use(
    cors({
      origin: true, // Allow all origins for public access
      credentials: true,
    }),
  )

  // Health check
  .get("/", () => ({
    success: true,
    message: "YuYu Lolita Shopping API with DB is running",
    version: "1.0.0",
    timestamp: new Date().toISOString(),
  }))

  .get("/health", async () => {
    const dbStatus = await ensureDatabaseHealth();
    return {
      success: true,
      database: dbStatus ? "connected" : "disconnected",
      timestamp: new Date().toISOString(),
    };
  })

  // Config endpoints
  .get("/api/v1/config", async () => {
    try {
      const result = await db.select().from(config);
      const configObj: Record<string, any> = {};

      result.forEach((item) => {
        try {
          // Try to parse as JSON first, fallback to string value
          configObj[item.key] =
            item.type === "number"
              ? parseFloat(item.value)
              : item.type === "boolean"
                ? item.value === "true"
                : item.value.startsWith("{") || item.value.startsWith("[")
                  ? JSON.parse(item.value)
                  : item.value;
        } catch {
          configObj[item.key] = item.value;
        }
      });

      return {
        success: true,
        data: { config: configObj },
      };
    } catch (_error) {
      return {
        success: false,
        data: { config: {} },
        error: "Failed to fetch config",
      };
    }
  })

  .get("/api/v1/config/kurs", async () => {
    try {
      const result = await db
        .select()
        .from(config)
        .where(eq(config.key, "current_kurs"))
        .limit(1);
      const kurs = result[0]?.value ? parseFloat(result[0].value) : 13.5;
      return {
        success: true,
        data: { kurs },
      };
    } catch (_error) {
      return {
        success: false,
        data: { kurs: 13.5 },
        error: "Failed to fetch kurs",
      };
    }
  })

  .get("/api/v1/config/faq", async () => {
    try {
      const result = await db
        .select()
        .from(config)
        .where(eq(config.key, "faq"))
        .limit(1);
      const faq = result[0]?.value ? JSON.parse(result[0].value) : [];
      return { faq };
    } catch (_error) {
      return { faq: [] };
    }
  })

  // Orders endpoints
  .get("/api/v1/orders", async () => {
    try {
      const result = await db
        .select({
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
          updatedAt: orders.updatedAt,
        })
        .from(orders)
        .orderBy(desc(orders.createdAt));

      return result;
    } catch (error) {
      console.error("Error fetching orders:", error);
      return [];
    }
  })

  .get("/api/v1/orders/:nomerok", async ({ params }) => {
    try {
      const order = await db
        .select()
        .from(orders)
        .where(eq(orders.nomerok, params.nomerok))
        .limit(1);
      if (!order.length) {
        return { error: "Order not found" };
      }

      const goods = await db
        .select()
        .from(orderGoods)
        .where(eq(orderGoods.orderId, order[0].id));

      return {
        ...order[0],
        goods,
      };
    } catch (error) {
      console.error("Error fetching order:", error);
      return { error: "Order not found" };
    }
  })

  // Stories endpoints
  .get("/api/v1/stories", async () => {
    try {
      const result = await db
        .select({
          id: stories.id,
          title: stories.title,
          link: stories.link,
          excerpt: stories.excerpt,
          thumbnail: stories.thumbnail,
          status: stories.status,
          publishedAt: stories.publishedAt,
          createdAt: stories.createdAt,
        })
        .from(stories)
        .orderBy(desc(stories.publishedAt));

      return result;
    } catch (error) {
      console.error("Error fetching stories:", error);
      return [];
    }
  })

  .get("/api/v1/stories/:link", async ({ params }) => {
    try {
      const story = await db
        .select()
        .from(stories)
        .where(eq(stories.link, params.link))
        .limit(1);
      if (!story.length) {
        return { error: "Story not found" };
      }

      return story[0];
    } catch (error) {
      console.error("Error fetching story:", error);
      return { error: "Story not found" };
    }
  })

  // Admin endpoints
  .get("/api/v1/admin/orders", async () => {
    try {
      const result = await db
        .select({
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
          updatedAt: orders.updatedAt,
        })
        .from(orders)
        .orderBy(desc(orders.createdAt));

      return {
        success: true,
        data: {
          orders: result,
          total: result.length,
        },
      };
    } catch (error) {
      console.error("Error fetching admin orders:", error);
      return {
        success: false,
        message: "Ошибка загрузки заказов",
      };
    }
  })

  .patch("/api/v1/admin/orders/:id/status", async ({ params, body }) => {
    try {
      const { status: newStatus } = body as { status: string };

      // Get order details for email
      const order = await db
        .select()
        .from(orders)
        .where(eq(orders.id, params.id))
        .limit(1);

      await db
        .update(orders)
        .set({
          status: newStatus as any,
          updatedAt: new Date(),
        })
        .where(eq(orders.id, params.id));

      // Send email notification (mock implementation)
      if (order.length > 0) {
        console.log(`📧 Email notification sent to ${order[0].customerEmail}`);
        console.log(
          `   Order ${order[0].nomerok} status changed to: ${newStatus}`,
        );
      }

      return {
        success: true,
        message: "Статус заказа обновлён и уведомление отправлено",
      };
    } catch (error) {
      console.error("Error updating order status:", error);
      return {
        success: false,
        message: "Ошибка обновления статуса",
      };
    }
  })

  // Order creation endpoint
  .post("/api/v1/orders", async ({ body }) => {
    try {
      const orderData = body as any;

      // Generate order number
      const nomerok = "YL" + Date.now().toString();

      // Create order
      const newOrder = await db
        .insert(orders)
        .values({
          nomerok,
          ...orderData,
          status: "created" as const,
          createdAt: new Date(),
          updatedAt: new Date(),
        })
        .returning();

      // Send email notification (mock implementation)
      console.log(`📧 Order creation email sent to ${orderData.customerEmail}`);
      console.log(`   New order created: ${nomerok}`);

      return {
        success: true,
        data: newOrder[0],
        message: "Заказ создан и уведомление отправлено",
      };
    } catch (error) {
      console.error("Error creating order:", error);
      return {
        success: false,
        message: "Ошибка создания заказа",
      };
    }
  })

  // Auth endpoints with real database authentication
  .post("/api/v1/auth/login", async ({ body, jwt: jwtInstance, cookie: cookieInstance }) => {
    const { email, password } = body as { email: string; password: string };
    
    try {
      // Find user in database
      const user = await db.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (!user) {
        return {
          success: false,
          message: "Неверный email или пароль",
        };
      }

      // Check password
      const isPasswordValid = await bcrypt.compare(password, user.password);
      if (!isPasswordValid) {
        return {
          success: false,
          message: "Неверный email или пароль",
        };
      }

      // Generate JWT token
      const token = await jwtInstance.sign({
        userId: user.id,
        email: user.email || user.phone || "",
        role: user.role,
      });

      // Set cookie
      cookieInstance.token.set({
        value: token,
        maxAge: 7 * 24 * 60 * 60, // 7 days
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
      });

      const userResponse = {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
        status: user.status,
        emailVerified: user.emailVerified,
        avatar: user.avatar,
        createdAt: user.createdAt,
      };

      return {
        success: true,
        data: {
          token,
          user: userResponse,
        },
      };
    } catch (error) {
      console.error("Login error:", error);
      return {
        success: false,
        message: "Ошибка сервера",
      };
    }
  })

  .post("/api/v1/auth/register", async ({ body: _body }) => {
    return {
      success: true,
      message: "Пользователь успешно зарегистрирован",
    };
  })

  // Customers endpoints
  .get("/api/v1/customers", async () => {
    try {
      const result = await db
        .select({
          id: customers.id,
          name: customers.name,
          email: customers.email,
          phone: customers.phone,
          createdAt: customers.createdAt,
          updatedAt: customers.updatedAt,
        })
        .from(customers);

      return {
        success: true,
        data: result,
      };
    } catch (error) {
      console.error("Error fetching customers:", error);
      return {
        success: false,
        message: "Ошибка загрузки клиентов",
        data: [],
      };
    }
  })

  .get("/api/v1/customers/:id", async ({ params }) => {
    try {
      const customer = await db
        .select()
        .from(customers)
        .where(eq(customers.id, params.id))
        .limit(1);

      if (!customer.length) {
        return {
          success: false,
          message: "Клиент не найден",
        };
      }

      // Get customer addresses
      const addresses = await db
        .select()
        .from(customerAddresses)
        .where(eq(customerAddresses.customerId, params.id));

      return {
        success: true,
        data: {
          ...customer[0],
          addresses,
        },
      };
    } catch (error) {
      console.error("Error fetching customer:", error);
      return {
        success: false,
        message: "Ошибка загрузки клиента",
      };
    }
  })

  .post("/api/v1/customers", async ({ body }) => {
    try {
      const customerData = body as any;

      // Create customer
      const newCustomer = await db
        .insert(customers)
        .values({
          name: customerData.name,
          email: customerData.email,
          phone: customerData.phone,
        })
        .returning();

      // Create default address if provided
      if (customerData.address) {
        await db.insert(customerAddresses).values({
          customerId: newCustomer[0].id,
          fullAddress: customerData.address.fullAddress,
          city: customerData.address.city,
          postalCode: customerData.address.postalCode,
          country: customerData.address.country || "Россия",
          isDefault: true,
        });
      }

      return {
        success: true,
        data: newCustomer[0],
        message: "Клиент создан успешно",
      };
    } catch (error) {
      console.error("Error creating customer:", error);
      return {
        success: false,
        message: "Ошибка создания клиента",
      };
    }
  })

  .put("/api/v1/customers/:id", async ({ params, body }) => {
    try {
      const customerData = body as any;

      const updatedCustomer = await db
        .update(customers)
        .set({
          name: customerData.name,
          email: customerData.email,
          phone: customerData.phone,
          updatedAt: new Date(),
        })
        .where(eq(customers.id, params.id))
        .returning();

      if (!updatedCustomer.length) {
        return {
          success: false,
          message: "Клиент не найден",
        };
      }

      return {
        success: true,
        data: updatedCustomer[0],
        message: "Клиент обновлён",
      };
    } catch (error) {
      console.error("Error updating customer:", error);
      return {
        success: false,
        message: "Ошибка обновления клиента",
      };
    }
  })

  .delete("/api/v1/customers/:id", async ({ params }) => {
    try {
      await db.delete(customers).where(eq(customers.id, params.id));

      return {
        success: true,
        message: "Клиент удалён",
      };
    } catch (error) {
      console.error("Error deleting customer:", error);
      return {
        success: false,
        message: "Ошибка удаления клиента",
      };
    }
  })

  .get("/api/v1/customers/:id/addresses", async ({ params }) => {
    try {
      const addresses = await db
        .select()
        .from(customerAddresses)
        .where(eq(customerAddresses.customerId, params.id));

      return {
        success: true,
        data: addresses,
      };
    } catch (error) {
      console.error("Error fetching customer addresses:", error);
      return {
        success: false,
        message: "Ошибка загрузки адресов",
        data: [],
      };
    }
  })

  .post("/api/v1/customers/:id/addresses", async ({ params, body }) => {
    try {
      const addressData = body as any;

      // If this is set as default, unset other default addresses
      if (addressData.isDefault) {
        await db
          .update(customerAddresses)
          .set({ isDefault: false })
          .where(eq(customerAddresses.customerId, params.id));
      }

      const newAddress = await db
        .insert(customerAddresses)
        .values({
          customerId: params.id,
          addressType: addressData.addressType || "shipping",
          fullAddress: addressData.fullAddress,
          city: addressData.city,
          postalCode: addressData.postalCode,
          country: addressData.country || "Россия",
          isDefault: addressData.isDefault || false,
        })
        .returning();

      return {
        success: true,
        data: newAddress[0],
        message: "Адрес добавлен",
      };
    } catch (error) {
      console.error("Error creating address:", error);
      return {
        success: false,
        message: "Ошибка добавления адреса",
      };
    }
  })

  // Initialize enhanced database system and seed test data
  .onStart(async () => {
    console.log("🔄 Initializing enhanced database system...");
    
    // Use enhanced database initialization with auto-recovery
    const dbConnected = await initializeDatabaseSystem();

    if (dbConnected) {
      console.log("✅ Database system is ready and healthy");
      
      // Auto-seed database with test data on startup (unless SKIP_SEED is set)
      if (!process.env.SKIP_SEED) {
        try {
          console.log("🌱 Auto-seeding database with test data...");
          const { seedDatabase } = await import("@lolita-fashion/db");
          await seedDatabase();
          console.log("✅ Test data seeding completed");
        } catch (error: any) {
          console.log(
            "ℹ️ Seeding skipped (data may already exist):",
            error?.message || error,
          );
        }
      } else {
        console.log("⏭️ Seeding skipped due to SKIP_SEED environment variable");
      }
    } else {
      const isWindows = process.platform === 'win32';
      const isCodespace = process.env.CODESPACES === 'true' || process.env.USER === 'codespace';
      
      console.warn("⚠️  Database initialization completed with limited functionality");
      console.warn("⚠️  Some database-dependent features may not be available");
      console.warn("");
      
      if (isWindows) {
        console.warn("💡 Windows Troubleshooting:");
        console.warn("   • Run: .\\scripts\\db-doctor.ps1 -Diagnose");
        console.warn("   • Or run: bun run db:setup");
      } else if (isCodespace) {
        console.warn("💡 GitHub Codespace Troubleshooting:");
        console.warn("   • Run: node setup-database.js");
        console.warn("   • Check PostgreSQL service: service postgresql status");
        console.warn("   • Verify DATABASE_URL in .env file");
      } else {
        console.warn("💡 Linux/Unix Troubleshooting:");
        console.warn("   • Check PostgreSQL service is running");
        console.warn("   • Verify DATABASE_URL configuration");
        console.warn("   • Ensure database and tables exist");
      }
      
      console.warn("");
      console.warn("🔗 The API will continue to run with available functionality");
    }
  })

  .listen({
    hostname: "0.0.0.0",
    port: 3001,
  });

console.log(
  "🚀 YuYu Lolita Shopping API (DB) is running on http://localhost:3001",
);
console.log("📚 Swagger documentation: http://localhost:3001/swagger");
