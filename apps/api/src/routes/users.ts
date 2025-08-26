import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { getPool, QueryBuilder } from "@lolita-fashion/db";
import type { User } from "@lolita-fashion/db";

export const userRoutes = new Elysia({ prefix: "/users" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Get User Profile
  .get(
    "/profile",
    async ({ jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        const user = await queryBuilder.getUserById(payload.userId as string);

        if (!user) {
          return {
            success: false,
            error: "User not found",
          };
        }

        return {
          success: true,
          user: {
            id: user.id,
            email: user.email,
            name: user.name,
            fullName: user.full_name,
            phone: user.phone,
            role: user.role,
            status: user.status,
            emailVerified: user.email_verified,
            phoneVerified: user.phone_verified,
            avatar: user.avatar,
            contactEmail: user.contact_email,
            contactPhone: user.contact_phone,
            createdAt: user.created_at,
            updatedAt: user.updated_at,
          },
        };
      } catch (error) {
        console.error("Get profile error:", error);
        return {
          success: false,
          error: "Failed to get user profile",
        };
      }
    },
    {
      detail: {
        tags: ["Users"],
        summary: "Get user profile",
        description: "Get the current user's profile information",
      },
    },
  )

  // Update User Profile
  .put(
    "/profile",
    async ({ body, jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        
        // Update user profile (simple UPDATE query)
        const sql = `
          UPDATE users 
          SET name = ?, full_name = ?, phone = ?, contact_email = ?, contact_phone = ?, updated_at = NOW()
          WHERE id = ?
        `;
        
        await pool.execute(sql, [
          body.name,
          body.fullName,
          body.phone,
          body.contactEmail,
          body.contactPhone,
          payload.userId as string,
        ]);

        return {
          success: true,
          message: "Profile updated successfully",
        };
      } catch (error) {
        console.error("Update profile error:", error);
        return {
          success: false,
          error: "Failed to update profile",
        };
      }
    },
    {
      body: t.Object({
        name: t.String({ minLength: 1 }),
        fullName: t.Optional(t.String()),
        phone: t.Optional(t.String()),
        contactEmail: t.Optional(t.String({ format: "email" })),
        contactPhone: t.Optional(t.String()),
      }),
      detail: {
        tags: ["Users"],
        summary: "Update user profile",
        description: "Update the current user's profile information",
      },
    },
  )

  // Get User Statistics
  .get(
    "/stats",
    async ({ jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Authentication required",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        
        // Get user statistics with direct SQL
        const orderStatsSQL = `
          SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
            SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing_orders,
            SUM(total_price_cny) as total_spent,
            SUM(commission_amount) as total_commission
          FROM orders 
          WHERE user_id = ?
        `;
        
        const [statsRows] = await pool.execute(orderStatsSQL, [payload.userId as string]);
        const stats = (statsRows as any[])[0];

        // Get active subscription
        const queryBuilder = new QueryBuilder(pool);
        const subscription = await queryBuilder.getActiveSubscription(payload.userId as string);

        return {
          success: true,
          stats: {
            totalOrders: Number(stats.total_orders) || 0,
            completedOrders: Number(stats.completed_orders) || 0,
            pendingOrders: Number(stats.pending_orders) || 0,
            processingOrders: Number(stats.processing_orders) || 0,
            totalSpent: Number(stats.total_spent) || 0,
            totalCommission: Number(stats.total_commission) || 0,
            subscription: subscription ? {
              tier: subscription.tier,
              status: subscription.status,
              expiresAt: subscription.expires_at,
            } : null,
          },
        };
      } catch (error) {
        console.error("Get user stats error:", error);
        return {
          success: false,
          error: "Failed to get user statistics",
        };
      }
    },
    {
      detail: {
        tags: ["Users"],
        summary: "Get user statistics",
        description: "Get order statistics and subscription info for the current user",
      },
    },
  );
