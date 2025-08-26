import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { getPool, QueryBuilder } from "@lolita-fashion/db";
import type { Subscription } from "@lolita-fashion/db";

export const subscriptionRoutes = new Elysia({ prefix: "/subscriptions" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Get Available Subscription Tiers
  .get(
    "/tiers",
    async () => {
      return {
        success: true,
        tiers: [
          {
            id: "basic",
            name: "Basic",
            commissionRate: 0.08, // 8%
            features: [
              "8% commission rate",
              "Standard processing",
              "Email support",
            ],
            price: 0, // Free
          },
          {
            id: "premium",
            name: "Premium",
            commissionRate: 0.06, // 6%
            features: [
              "6% commission rate",
              "Priority processing",
              "Email & phone support",
              "Extended storage",
            ],
            price: 999, // ¥999/month
          },
          {
            id: "vip",
            name: "VIP",
            commissionRate: 0.04, // 4%
            features: [
              "4% commission rate",
              "VIP processing priority",
              "Dedicated support",
              "Premium storage",
              "Express shipping",
            ],
            price: 1999, // ¥1999/month
          },
          {
            id: "elite",
            name: "Elite",
            commissionRate: 0.02, // 2%
            features: [
              "2% commission rate",
              "Elite priority processing",
              "Personal account manager",
              "Unlimited storage",
              "Premium shipping",
              "Advanced analytics",
            ],
            price: 3999, // ¥3999/month
          },
        ],
      };
    },
    {
      detail: {
        tags: ["Subscriptions"],
        summary: "Get subscription tiers",
        description: "Get all available subscription tiers with their features and pricing",
      },
    },
  )

  // Get Current Subscription
  .get(
    "/current",
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
        
        const subscription = await queryBuilder.getActiveSubscription(payload.userId as string);

        if (!subscription) {
          return {
            success: true,
            subscription: null,
          };
        }

        return {
          success: true,
          subscription: {
            id: subscription.id,
            tier: subscription.tier,
            status: subscription.status,
            expiresAt: subscription.expires_at,
            createdAt: subscription.created_at,
          },
        };
      } catch (error) {
        console.error("Get current subscription error:", error);
        return {
          success: false,
          error: "Failed to get subscription",
        };
      }
    },
    {
      detail: {
        tags: ["Subscriptions"],
        summary: "Get current subscription",
        description: "Get the current user's active subscription",
      },
    },
  )

  // Subscribe to a Tier
  .post(
    "/subscribe",
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

        // Validate tier
        const validTiers = ["basic", "premium", "vip", "elite"];
        if (!validTiers.includes(body.tier)) {
          return {
            success: false,
            error: "Invalid subscription tier",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);

        // Calculate expiration date (1 month from now)
        const expiresAt = new Date();
        expiresAt.setMonth(expiresAt.getMonth() + 1);

        // Create subscription
        const subscriptionId = await queryBuilder.createSubscription({
          user_id: payload.userId as string,
          tier: body.tier as "basic" | "premium" | "vip" | "elite",
          status: "active",
          expires_at: expiresAt,
        });

        return {
          success: true,
          message: "Subscription created successfully",
          subscription: {
            id: subscriptionId,
            tier: body.tier,
            status: "active",
            expiresAt: expiresAt,
          },
        };
      } catch (error) {
        console.error("Subscribe error:", error);
        return {
          success: false,
          error: "Failed to create subscription",
        };
      }
    },
    {
      body: t.Object({
        tier: t.String(),
      }),
      detail: {
        tags: ["Subscriptions"],
        summary: "Subscribe to a tier",
        description: "Create a new subscription for the current user",
      },
    },
  )

  // Cancel Subscription
  .delete(
    "/cancel",
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

        // Cancel active subscription
        const cancelSQL = `
          UPDATE subscriptions 
          SET status = 'cancelled', updated_at = NOW()
          WHERE user_id = ? AND status = 'active'
        `;
        
        await pool.execute(cancelSQL, [payload.userId as string]);

        return {
          success: true,
          message: "Subscription cancelled successfully",
        };
      } catch (error) {
        console.error("Cancel subscription error:", error);
        return {
          success: false,
          error: "Failed to cancel subscription",
        };
      }
    },
    {
      detail: {
        tags: ["Subscriptions"],
        summary: "Cancel subscription",
        description: "Cancel the current user's active subscription",
      },
    },
  );
