import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { getPool, QueryBuilder } from "@lolita-fashion/db";
import type { Order } from "@lolita-fashion/db";

export const orderRoutes = new Elysia({ prefix: "/orders" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Create Order
  .post(
    "/",
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
        const queryBuilder = new QueryBuilder(pool);

        // Calculate commission based on subscription tier
        const subscription = await queryBuilder.getActiveSubscription(payload.userId as string);
        let commissionRate = 0.10; // Default 10%

        if (subscription) {
          switch (subscription.tier) {
            case "basic":
              commissionRate = 0.08; // 8%
              break;
            case "premium":
              commissionRate = 0.06; // 6%
              break;
            case "vip":
              commissionRate = 0.04; // 4%
              break;
            case "elite":
              commissionRate = 0.02; // 2%
              break;
          }
        }

        const commissionAmount = body.totalPriceCny * commissionRate;
        const finalPrice = body.totalPriceCny + commissionAmount;

        // Create order
        const orderId = await queryBuilder.createOrder({
          user_id: payload.userId as string,
          customer_id: body.customerId,
          goods: body.goods,
          weight_kg: body.weightKg,
          volume_cbm: body.volumeCbm,
          total_price_cny: body.totalPriceCny,
          commission_rate: commissionRate,
          commission_amount: commissionAmount,
          final_price: finalPrice,
          status: "pending",
          priority_processing: subscription?.tier === "vip" || subscription?.tier === "elite",
        });

        return {
          success: true,
          message: "Order created successfully",
          order: {
            id: orderId,
            totalPriceCny: body.totalPriceCny,
            commissionRate,
            commissionAmount,
            finalPrice,
            status: "pending",
          },
        };
      } catch (error) {
        console.error("Create order error:", error);
        return {
          success: false,
          error: "Failed to create order",
        };
      }
    },
    {
      body: t.Object({
        customerId: t.Optional(t.String()),
        goods: t.String({ minLength: 1 }),
        weightKg: t.Number({ minimum: 0 }),
        volumeCbm: t.Number({ minimum: 0 }),
        totalPriceCny: t.Number({ minimum: 0 }),
      }),
      detail: {
        tags: ["Orders"],
        summary: "Create new order",
        description: "Create a new order with automatic commission calculation",
      },
    },
  )

  // Get User Orders
  .get(
    "/",
    async ({ jwt, cookie: { auth }, query }) => {
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
        
        const orders = await queryBuilder.getOrdersByUserId(payload.userId as string);

        return {
          success: true,
          orders: orders.map(order => ({
            id: order.id,
            goods: order.goods,
            weightKg: order.weight_kg,
            volumeCbm: order.volume_cbm,
            totalPriceCny: order.total_price_cny,
            commissionRate: order.commission_rate,
            commissionAmount: order.commission_amount,
            finalPrice: order.final_price,
            status: order.status,
            priorityProcessing: order.priority_processing,
            createdAt: order.created_at,
            updatedAt: order.updated_at,
          })),
        };
      } catch (error) {
        console.error("Get orders error:", error);
        return {
          success: false,
          error: "Failed to get orders",
        };
      }
    },
    {
      detail: {
        tags: ["Orders"],
        summary: "Get user orders",
        description: "Get all orders for the current user",
      },
    },
  )

  // Get Order by ID
  .get(
    "/:id",
    async ({ params: { id }, jwt, cookie: { auth } }) => {
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

        // Get order and check ownership
        const orders = await queryBuilder.getOrdersByUserId(payload.userId as string);
        const order = orders.find(o => o.id === id);

        if (!order) {
          return {
            success: false,
            error: "Order not found",
          };
        }

        return {
          success: true,
          order: {
            id: order.id,
            goods: order.goods,
            weightKg: order.weight_kg,
            volumeCbm: order.volume_cbm,
            totalPriceCny: order.total_price_cny,
            commissionRate: order.commission_rate,
            commissionAmount: order.commission_amount,
            finalPrice: order.final_price,
            status: order.status,
            priorityProcessing: order.priority_processing,
            createdAt: order.created_at,
            updatedAt: order.updated_at,
          },
        };
      } catch (error) {
        console.error("Get order error:", error);
        return {
          success: false,
          error: "Failed to get order",
        };
      }
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        tags: ["Orders"],
        summary: "Get order by ID",
        description: "Get a specific order by its ID",
      },
    },
  );
