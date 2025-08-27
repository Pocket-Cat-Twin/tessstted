import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { getPool, QueryBuilder } from "@lolita-fashion/db";

export const adminRoutes = new Elysia({ prefix: "/admin" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Admin middleware - check if user is admin
  .derive(async ({ jwt, cookie: { auth } }) => {
    if (!auth.value) {
      throw new Error("Authentication required");
    }

    const payload = await jwt.verify(auth.value);
    if (!payload) {
      throw new Error("Invalid token");
    }

    const pool = await getPool();
    const queryBuilder = new QueryBuilder(pool);
    const user = await queryBuilder.getUserById(payload.userId as string);

    if (!user || user.role !== 'admin') {
      throw new Error("Admin access required");
    }

    return { user, userId: payload.userId as string };
  })

  // Get all orders for admin
  .get(
    "/orders",
    async ({ user }) => {
      try {
        console.log(`👑 Admin ${user.name} requesting all orders`);
        
        const pool = await getPool();
        
        // Get all orders with user information
        const ordersSQL = `
          SELECT 
            o.*,
            u.name as customer_name,
            u.email as customer_email,
            u.phone as customer_phone
          FROM orders o
          LEFT JOIN users u ON o.user_id = u.id
          ORDER BY o.created_at DESC
        `;
        
        const [ordersRows] = await pool.execute(ordersSQL);
        const orders = ordersRows as any[];

        return {
          success: true,
          orders: orders.map(order => ({
            id: order.id,
            nomerok: order.id, // Using ID as nomerok for now
            goods: order.goods,
            weightKg: order.weight_kg,
            volumeCbm: order.volume_cbm,
            totalPriceCny: order.total_price_cny,
            commissionRate: order.commission_rate,
            commissionAmount: order.commission_amount,
            finalPrice: order.final_price,
            totalRuble: order.final_price * 15, // Approximate conversion
            status: order.status,
            priorityProcessing: order.priority_processing,
            customerName: order.customer_name || 'Unknown',
            customerEmail: order.customer_email || '',
            customerPhone: order.customer_phone || '',
            createdAt: order.created_at,
            updatedAt: order.updated_at,
          })),
        };
      } catch (error) {
        console.error("Admin get orders error:", error);
        
        if (error instanceof Error && error.message === "Authentication required") {
          return {
            success: false,
            error: "AUTHENTICATION_REQUIRED",
            message: "Authentication required",
          };
        }
        
        if (error instanceof Error && error.message === "Invalid token") {
          return {
            success: false,
            error: "INVALID_TOKEN", 
            message: "Invalid token",
          };
        }
        
        if (error instanceof Error && error.message === "Admin access required") {
          return {
            success: false,
            error: "ADMIN_ACCESS_REQUIRED",
            message: "Admin access required",
          };
        }

        return {
          success: false,
          error: "ADMIN_ORDERS_FAILED",
          message: "Failed to get orders",
        };
      }
    },
    {
      detail: {
        tags: ["Admin"],
        summary: "Get all orders (Admin only)",
        description: "Retrieve all orders in the system. Admin access required.",
      },
    },
  )

  // Update order status
  .patch(
    "/orders/:orderId/status", 
    async ({ params: { orderId }, body, user }) => {
      try {
        console.log(`👑 Admin ${user.name} updating order ${orderId} status to: ${body.status}`);
        
        const pool = await getPool();
        
        // Validate order exists
        const checkOrderSQL = "SELECT id FROM orders WHERE id = ?";
        const [checkRows] = await pool.execute(checkOrderSQL, [orderId]);
        
        if ((checkRows as any[]).length === 0) {
          return {
            success: false,
            error: "ORDER_NOT_FOUND",
            message: "Order not found",
          };
        }
        
        // Update order status
        const updateSQL = `
          UPDATE orders 
          SET status = ?, updated_at = NOW() 
          WHERE id = ?
        `;
        
        await pool.execute(updateSQL, [body.status, orderId]);

        return {
          success: true,
          message: "Order status updated successfully",
          data: {
            orderId,
            newStatus: body.status,
            updatedBy: user.name,
          },
        };
      } catch (error) {
        console.error("Admin update order status error:", error);
        
        if (error instanceof Error && error.message === "Authentication required") {
          return {
            success: false,
            error: "AUTHENTICATION_REQUIRED",
            message: "Authentication required",
          };
        }
        
        if (error instanceof Error && error.message === "Invalid token") {
          return {
            success: false,
            error: "INVALID_TOKEN",
            message: "Invalid token", 
          };
        }
        
        if (error instanceof Error && error.message === "Admin access required") {
          return {
            success: false,
            error: "ADMIN_ACCESS_REQUIRED",
            message: "Admin access required",
          };
        }

        return {
          success: false,
          error: "STATUS_UPDATE_FAILED",
          message: "Failed to update order status",
        };
      }
    },
    {
      params: t.Object({
        orderId: t.String(),
      }),
      body: t.Object({
        status: t.String({
          enum: ["created", "processing", "checking", "paid", "shipped", "delivered", "cancelled"]
        }),
      }),
      detail: {
        tags: ["Admin"],
        summary: "Update order status (Admin only)",
        description: "Update the status of a specific order. Admin access required.",
      },
    },
  )

  // Get admin statistics
  .get(
    "/stats",
    async ({ user }) => {
      try {
        console.log(`👑 Admin ${user.name} requesting statistics`);
        
        const pool = await getPool();
        
        // Get order statistics
        const statsSQL = `
          SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status IN ('created', 'processing', 'checking') THEN 1 ELSE 0 END) as pending_orders,
            SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
            SUM(final_price) as total_revenue,
            SUM(commission_amount) as total_commission
          FROM orders
        `;
        
        const [statsRows] = await pool.execute(statsSQL);
        const stats = (statsRows as any[])[0];

        // Get user statistics
        const userStatsSQL = `
          SELECT 
            COUNT(*) as total_users,
            SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_users,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_users
          FROM users
        `;
        
        const [userStatsRows] = await pool.execute(userStatsSQL);
        const userStats = (userStatsRows as any[])[0];

        return {
          success: true,
          stats: {
            orders: {
              total: Number(stats.total_orders) || 0,
              pending: Number(stats.pending_orders) || 0, 
              completed: Number(stats.completed_orders) || 0,
              cancelled: Number(stats.cancelled_orders) || 0,
            },
            financial: {
              totalRevenue: Number(stats.total_revenue) || 0,
              totalCommission: Number(stats.total_commission) || 0,
            },
            users: {
              total: Number(userStats.total_users) || 0,
              admins: Number(userStats.admin_users) || 0,
              active: Number(userStats.active_users) || 0,
            },
          },
        };
      } catch (error) {
        console.error("Admin get stats error:", error);
        
        if (error instanceof Error && error.message === "Authentication required") {
          return {
            success: false,
            error: "AUTHENTICATION_REQUIRED",
            message: "Authentication required",
          };
        }
        
        if (error instanceof Error && error.message === "Invalid token") {
          return {
            success: false,
            error: "INVALID_TOKEN",
            message: "Invalid token",
          };
        }
        
        if (error instanceof Error && error.message === "Admin access required") {
          return {
            success: false,
            error: "ADMIN_ACCESS_REQUIRED", 
            message: "Admin access required",
          };
        }

        return {
          success: false,
          error: "STATS_FETCH_FAILED",
          message: "Failed to get statistics",
        };
      }
    },
    {
      detail: {
        tags: ["Admin"],
        summary: "Get admin statistics (Admin only)",
        description: "Retrieve system statistics including orders, revenue, and users. Admin access required.",
      },
    },
  );