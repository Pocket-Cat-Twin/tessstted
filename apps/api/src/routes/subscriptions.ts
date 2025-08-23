import { Elysia, t } from "elysia";
import { db, subscriptionHistory, userSubscriptions, eq, desc, and, sql } from "@yuyu/db";
import { requireAuth, requireAdmin } from "../middleware/auth";
import {
  subscriptionMiddleware,
  requireSubscription,
  requireFeature,
} from "../middleware/subscription";
import { subscriptionService } from "../services/subscription";
import { NotFoundError } from "../middleware/error";

export const subscriptionRoutes = new Elysia({ prefix: "/subscriptions" })

  // Get all available subscription tiers (public)
  .get(
    "/tiers",
    async () => {
      return {
        success: true,
        data: {
          tiers: [
            {
              id: "free",
              name: "Обычный подписчик",
              price: 0,
              currency: "RUB",
              duration: null,
              description: "Редкие заказы, знакомство с сервисом",
              features: [
                "Обработка заказов: до 5 рабочих дней",
                "Хранение на складе: до 14 дней",
              ],
              limitations: [
                "Нет участия в акциях и скидках",
                "Нет приоритета в очереди",
                "Нет объединения посылок",
              ],
            },
            {
              id: "group",
              name: "Групповая подписка",
              price: 990,
              currency: "RUB",
              duration: 30,
              description: "Накопительные заказы, совместные покупки",
              features: [
                "Хранение на складе: до 3 месяцев",
                "Объединение заказов от разных продавцов",
                "Обработка: 2–4 рабочих дня",
                "Доступ к групповым акциям",
              ],
              limitations: ["Нет приоритетной поддержки"],
            },
            {
              id: "elite",
              name: "Элитный подписчик",
              price: 1990,
              currency: "RUB",
              duration: 30,
              description: "Активные клиенты, ценящие скорость и сервис",
              features: [
                "Быстрые ответы: до 12 часов",
                "Хранение без ограничений",
                "Приоритетная отправка заказов",
                "Участие в закрытых акциях",
                "Индивидуальная помощь и проверка товара",
                "Персональная поддержка",
              ],
              limitations: [],
            },
            {
              id: "vip_temp",
              name: "Разовый VIP-доступ",
              price: 890,
              currency: "RUB",
              duration: 7,
              description: "Срочные разовые заказы",
              features: [
                "Экстренная обработка и приоритет",
                "Хранение до 30 дней",
                "1 заказ с максимальным вниманием",
                "Временное VIP-обслуживание",
              ],
              limitations: ["Ограничено 7 днями", "Только для разовых заказов"],
            },
          ],
        },
      };
    },
    {
      detail: {
        summary: "Get subscription tiers",
        description:
          "Get all available subscription tiers with features and pricing",
        tags: ["Subscriptions"],
      },
    },
  )

  // User subscription management (requires auth)
  .use(requireAuth)

  // Get current user subscription status
  .get(
    "/status",
    async ({ store }) => {
      const userId = store.user.id;
      const subscriptionInfo =
        await subscriptionService.getUserSubscriptionInfo(userId);

      return {
        success: true,
        data: { subscription: subscriptionInfo },
      };
    },
    {
      detail: {
        summary: "Get user subscription status",
        description:
          "Get current subscription tier, expiration, and available upgrades",
        tags: ["Subscriptions"],
      },
    },
  )

  // Purchase or upgrade subscription
  .post(
    "/purchase",
    async ({ body, store }) => {
      const userId = store.user.id;

      const result = await subscriptionService.purchaseSubscription(userId, {
        tier: body.tier,
        paymentMethod: body.paymentMethod,
        paymentReference: body.paymentReference,
        autoRenew: body.autoRenew,
      });

      return {
        success: true,
        message: `Successfully ${result.upgraded ? "upgraded to" : "purchased"} ${body.tier} subscription`,
        data: { purchase: result },
      };
    },
    {
      body: t.Object({
        tier: t.Union([
          t.Literal("group"),
          t.Literal("elite"),
          t.Literal("vip_temp"),
        ]),
        paymentMethod: t.String({ minLength: 1 }),
        paymentReference: t.Optional(t.String()),
        autoRenew: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Purchase subscription",
        description: "Purchase or upgrade to a new subscription tier",
        tags: ["Subscriptions"],
      },
    },
  )

  // Cancel subscription (disable auto-renewal)
  .post(
    "/cancel",
    async ({ body, store }) => {
      const userId = store.user.id;

      await subscriptionService.cancelSubscription(userId, body.subscriptionId);

      return {
        success: true,
        message:
          "Subscription auto-renewal cancelled. Your current subscription will remain active until expiration.",
      };
    },
    {
      body: t.Object({
        subscriptionId: t.Optional(t.String()),
      }),
      detail: {
        summary: "Cancel subscription",
        description: "Cancel auto-renewal for current subscription",
        tags: ["Subscriptions"],
      },
    },
  )

  // Renew subscription
  .post(
    "/renew",
    async ({ body, store }) => {
      const userId = store.user.id;

      const result = await subscriptionService.renewSubscription(
        userId,
        body.paymentMethod,
        body.paymentReference,
      );

      return {
        success: true,
        message: "Subscription renewed successfully",
        data: { renewal: result },
      };
    },
    {
      body: t.Object({
        paymentMethod: t.String({ minLength: 1 }),
        paymentReference: t.Optional(t.String()),
      }),
      detail: {
        summary: "Renew subscription",
        description: "Renew expired or current subscription",
        tags: ["Subscriptions"],
      },
    },
  )

  // Get subscription with middleware context
  .use(subscriptionMiddleware)
  .get(
    "/context",
    async ({ subscription }) => {
      return {
        success: true,
        data: { subscription },
      };
    },
    {
      detail: {
        summary: "Get subscription context",
        description: "Get current subscription context with features",
        tags: ["Subscriptions"],
      },
    },
  )

  // Test subscription features
  .get(
    "/features/promotions",
    async ({ subscription }) => {
      return {
        success: true,
        data: {
          canAccess: subscription.features.canParticipateInPromotions,
          tier: subscription.tier,
          message: subscription.features.canParticipateInPromotions
            ? "You can participate in promotions"
            : "Upgrade to access promotions",
        },
      };
    },
    {
      detail: {
        summary: "Check promotions access",
        description: "Check if user can access promotional features",
        tags: ["Subscriptions"],
      },
    },
  )

  // Test feature requirement middleware
  .use(requireFeature("canCombineOrders"))
  .get(
    "/features/combine-orders",
    async () => {
      return {
        success: true,
        message: "You have access to order combining feature",
      };
    },
    {
      detail: {
        summary: "Access order combining (Group+)",
        description: "Endpoint requiring order combining feature",
        tags: ["Subscriptions"],
      },
    },
  )

  // Test subscription requirement middleware
  .use(requireSubscription("elite"))
  .get(
    "/features/priority-support",
    async () => {
      return {
        success: true,
        message:
          "Welcome to priority support! Your Elite subscription gives you access to dedicated assistance.",
      };
    },
    {
      detail: {
        summary: "Access priority support (Elite+)",
        description: "Endpoint requiring Elite subscription or higher",
        tags: ["Subscriptions"],
      },
    },
  )

  // Admin subscription management
  .use(requireAdmin)

  // Get subscription statistics
  .get(
    "/admin/stats",
    async () => {
      const stats = await subscriptionService.getSubscriptionStats();

      return {
        success: true,
        data: { stats },
      };
    },
    {
      detail: {
        summary: "Get subscription statistics (Admin)",
        description: "Get detailed subscription analytics and metrics",
        tags: ["Subscriptions"],
      },
    },
  )

  // Process auto-renewals (for scheduled jobs)
  .post(
    "/admin/process-renewals",
    async () => {
      const result = await subscriptionService.processAutoRenewals();

      return {
        success: true,
        message: `Processed ${result.processed} renewals, ${result.failed} failed`,
        data: { result },
      };
    },
    {
      detail: {
        summary: "Process auto-renewals (Admin)",
        description: "Process pending auto-renewals for subscriptions",
        tags: ["Subscriptions"],
      },
    },
  )

  // Get all user subscriptions
  .get(
    "/admin/users/:userId",
    async ({ params: { userId } }) => {
      const subscriptionInfo =
        await subscriptionService.getUserSubscriptionInfo(userId);

      // Get subscription history
      const history = await db.query.subscriptionHistory.findMany({
        where: eq(subscriptionHistory.userId, userId),
        orderBy: desc(subscriptionHistory.createdAt),
        limit: 20,
      });

      return {
        success: true,
        data: {
          current: subscriptionInfo,
          history,
        },
      };
    },
    {
      params: t.Object({
        userId: t.String(),
      }),
      detail: {
        summary: "Get user subscriptions (Admin)",
        description: "Get subscription status and history for specific user",
        tags: ["Subscriptions"],
      },
    },
  )

  // Manually grant subscription to user
  .post(
    "/admin/grant",
    async ({ body }) => {
      const result = await subscriptionService.purchaseSubscription(
        body.userId,
        {
          tier: body.tier,
          paymentMethod: "admin_grant",
          paymentReference: body.reason || "Manually granted by admin",
          autoRenew: body.autoRenew || false,
        },
      );

      return {
        success: true,
        message: `Granted ${body.tier} subscription to user`,
        data: { grant: result },
      };
    },
    {
      body: t.Object({
        userId: t.String(),
        tier: t.Union([
          t.Literal("group"),
          t.Literal("elite"),
          t.Literal("vip_temp"),
        ]),
        autoRenew: t.Optional(t.Boolean()),
        reason: t.Optional(t.String()),
      }),
      detail: {
        summary: "Grant subscription to user (Admin)",
        description: "Manually grant subscription to specific user",
        tags: ["Subscriptions"],
      },
    },
  )

  // Cancel user subscription (admin)
  .post(
    "/admin/cancel",
    async ({ body }) => {
      const { userId, subscriptionId, reason } = body;

      // Find the subscription
      const subscription = await db.query.userSubscriptions.findFirst({
        where: and(
          eq(userSubscriptions.userId, userId),
          eq(userSubscriptions.id, subscriptionId),
        ),
      });

      if (!subscription) {
        throw new NotFoundError("Subscription not found");
      }

      // Cancel the subscription
      await subscriptionService.cancelSubscription(userId, subscriptionId);

      // Log the admin action in history
      await db.insert(subscriptionHistory).values({
        userId,
        subscriptionId,
        action: "admin_cancelled",
        details: JSON.stringify({ reason: reason || "Cancelled by admin" }),
        performedBy: "admin",
      });

      return {
        success: true,
        message: "Subscription cancelled successfully",
      };
    },
    {
      body: t.Object({
        userId: t.String(),
        subscriptionId: t.String(),
        reason: t.Optional(t.String()),
      }),
      detail: {
        summary: "Cancel user subscription (Admin)",
        description: "Cancel specific user subscription",
        tags: ["Subscriptions"],
      },
    },
  )

  // Extend user subscription (admin)
  .post(
    "/admin/extend",
    async ({ body }) => {
      const { userId, subscriptionId, extensionDays, reason } = body;

      // Find the subscription
      const subscription = await db.query.userSubscriptions.findFirst({
        where: and(
          eq(userSubscriptions.userId, userId),
          eq(userSubscriptions.id, subscriptionId),
        ),
      });

      if (!subscription) {
        throw new NotFoundError("Subscription not found");
      }

      // Extend the subscription
      const currentEndDate = new Date(subscription.endDate);
      const newEndDate = new Date(
        currentEndDate.getTime() + extensionDays * 24 * 60 * 60 * 1000,
      );

      await db
        .update(userSubscriptions)
        .set({
          endDate: newEndDate,
          updatedAt: new Date(),
        })
        .where(eq(userSubscriptions.id, subscriptionId));

      // Log the admin action in history
      await db.insert(subscriptionHistory).values({
        userId,
        subscriptionId,
        action: "admin_extended",
        details: JSON.stringify({
          extensionDays,
          newEndDate: newEndDate.toISOString(),
          reason: reason || "Extended by admin",
        }),
        performedBy: "admin",
      });

      return {
        success: true,
        message: `Subscription extended by ${extensionDays} days`,
        data: { newEndDate },
      };
    },
    {
      body: t.Object({
        userId: t.String(),
        subscriptionId: t.String(),
        extensionDays: t.Number({ minimum: 1, maximum: 365 }),
        reason: t.Optional(t.String()),
      }),
      detail: {
        summary: "Extend user subscription (Admin)",
        description: "Extend specific user subscription by days",
        tags: ["Subscriptions"],
      },
    },
  )

  // Get all subscriptions with filtering (admin)
  .get(
    "/admin/all",
    async ({ query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 20;
      const offset = (page - 1) * limit;
      const tier = query.tier;
      const status = query.status;
      const search = query.search;

      // Build where conditions
      const conditions = [];

      if (tier) {
        conditions.push(eq(userSubscriptions.tier, tier as any));
      }

      if (status === "active") {
        conditions.push(sql`${userSubscriptions.endDate} > NOW()`);
      } else if (status === "expired") {
        conditions.push(sql`${userSubscriptions.endDate} <= NOW()`);
      }

      const whereClause =
        conditions.length > 0 ? and(...conditions) : undefined;

      const subscriptions = await db.query.userSubscriptions.findMany({
        where: whereClause,
        with: {
          user: {
            columns: {
              id: true,
              name: true,
              email: true,
              password: false,
            },
          },
        },
        orderBy: desc(userSubscriptions.createdAt),
        limit,
        offset,
      });

      // Filter by user search if provided
      let filteredSubscriptions = subscriptions;
      if (search) {
        filteredSubscriptions = subscriptions.filter(
          (sub) =>
            sub.user.name?.toLowerCase().includes(search.toLowerCase()) ||
            sub.user.email.toLowerCase().includes(search.toLowerCase()),
        );
      }

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(userSubscriptions)
        .where(whereClause);

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: filteredSubscriptions,
        pagination: {
          page,
          limit,
          total: count,
          totalPages,
          hasNext: page < totalPages,
          hasPrev: page > 1,
        },
      };
    },
    {
      query: t.Object({
        page: t.Optional(t.String()),
        limit: t.Optional(t.String()),
        tier: t.Optional(t.String()),
        status: t.Optional(t.String()),
        search: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get all subscriptions (Admin)",
        description: "Get all subscriptions with filtering and pagination",
        tags: ["Subscriptions"],
      },
    },
  );
