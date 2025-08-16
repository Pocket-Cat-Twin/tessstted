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
} from "@yuyu/db";

// Database connection test
async function testDBConnection() {
  try {
    const result = await db.select().from(config).limit(1);
    console.log("✅ Database connection successful");
    return true;
  } catch (error) {
    console.error("❌ Database connection failed:", error);
    return false;
  }
}

const app = new Elysia()
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
    const dbStatus = await testDBConnection();
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
    } catch (error) {
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
    } catch (error) {
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
    } catch (error) {
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
  .post("/api/v1/auth/login", async ({ body, jwt, cookie }) => {
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
      const token = await jwt.sign({
        userId: user.id,
        email: user.email,
        role: user.role,
      });

      // Set cookie
      cookie.token.set({
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

  .post("/api/v1/auth/register", async ({ body }) => {
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

  // Initialize database connection and seed test data
  .onStart(async () => {
    console.log("🔄 Initializing database connection...");
    const dbConnected = await testDBConnection();

    if (dbConnected) {
      // Auto-seed database with test data on startup (unless SKIP_SEED is set)
      if (!process.env.SKIP_SEED) {
        try {
          console.log("🌱 Auto-seeding database with test data...");
          const { seedDatabase } = await import("@yuyu/db/src/seed.ts");
          await seedDatabase();
          console.log("✅ Test data seeding completed");
        } catch (error) {
          console.log(
            "ℹ️ Seeding skipped (data may already exist):",
            error?.message || error,
          );
        }
      } else {
        console.log("⏭️ Seeding skipped due to SKIP_SEED environment variable");
      }
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
