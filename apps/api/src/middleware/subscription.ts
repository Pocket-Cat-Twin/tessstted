import { Elysia } from "elysia";
import { db, userSubscriptions, orders, eq, and, gte } from "@yuyu/db";
import {
  getEffectiveTier,
  isSubscriptionActive,
  SUBSCRIPTION_TIERS,
} from "@yuyu/shared";
import { ForbiddenError, UnauthorizedError } from "./error";

export interface SubscriptionContext {
  subscription: {
    tier: "free" | "group" | "elite" | "vip_temp";
    isActive: boolean;
    features: any;
    expiresAt: Date | null;
    daysRemaining: number | null;
  };
}

/**
 * Middleware to check user subscription and add subscription context
 */
export const subscriptionMiddleware = new Elysia({
  name: "subscription",
}).derive(async ({ store }) => {
  const userId = store?.user?.id;

  let tier: "free" | "group" | "elite" | "vip_temp" = "free";
  let isActive = true;
  let expiresAt: Date | null = null;
  let activeSubscription = null;

  if (userId) {
    // Get user's active subscription
    activeSubscription = await db.query.userSubscriptions.findFirst({
      where: and(
        eq(userSubscriptions.userId, userId),
        eq(userSubscriptions.status, "active"),
        gte(userSubscriptions.endDate, new Date()),
      ),
      orderBy: userSubscriptions.endDate,
    });

    if (activeSubscription) {
      tier = activeSubscription.tier;
      expiresAt = activeSubscription.endDate;
      isActive = isSubscriptionActive(activeSubscription.endDate);
    }
  }

  // Get effective tier (falls back to free if expired)
  const effectiveTier = getEffectiveTier(tier, expiresAt);
  const features = SUBSCRIPTION_TIERS[effectiveTier].features;

  // Calculate days remaining
  let daysRemaining: number | null = null;
  if (expiresAt) {
    const now = new Date();
    const diffTime = expiresAt.getTime() - now.getTime();
    daysRemaining = Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
  }

  return {
    subscription: {
      tier: effectiveTier,
      isActive,
      features,
      expiresAt,
      daysRemaining,
    },
  } as SubscriptionContext;
});

/**
 * Require specific subscription tier or higher
 */
export function requireSubscription(minTier: "group" | "elite" | "vip_temp") {
  const tierLevels = {
    group: 1,
    elite: 2,
    vip_temp: 2, // VIP temp has same level as elite for most purposes
  };

  return new Elysia({ name: `require-${minTier}` })
    .use(subscriptionMiddleware)
    .derive(({ subscription }) => {
      const currentLevel =
        subscription.tier === "free" ? 0 : tierLevels[subscription.tier] || 0;
      const requiredLevel = tierLevels[minTier];

      if (currentLevel < requiredLevel) {
        throw new ForbiddenError(`${minTier} subscription or higher required`);
      }

      return {};
    });
}

/**
 * Check if user can perform specific action based on subscription features
 */
export function requireFeature(
  featureName: keyof typeof SUBSCRIPTION_TIERS.free.features,
) {
  return new Elysia({ name: `require-${featureName}` })
    .use(subscriptionMiddleware)
    .derive(({ subscription }) => {
      const hasFeature = subscription.features[featureName];

      if (!hasFeature) {
        const featureMessages = {
          canParticipateInPromotions:
            "Участие в акциях доступно только для подписчиков",
          canCombineOrders:
            "Объединение заказов доступно для групповой подписки и выше",
          hasPriorityProcessing:
            "Приоритетная обработка доступна для элитных подписчиков",
          hasPersonalSupport:
            "Персональная поддержка доступна для элитных подписчиков",
          hasProductInspection:
            "Проверка товаров доступна для элитных подписчиков",
        };

        const message =
          featureMessages[featureName] ||
          `Feature ${featureName} not available`;
        throw new ForbiddenError(message);
      }

      return {};
    });
}

/**
 * Check storage limit for user
 */
export function checkStorageLimit() {
  return new Elysia({ name: "storage-limit" })
    .use(subscriptionMiddleware)
    .derive(async ({ subscription, store }) => {
      const userId = store?.user?.id;

      if (!userId) {
        throw new UnauthorizedError("Authentication required to check storage");
      }

      const maxStorageDays = subscription.features.maxStorageDays;

      if (maxStorageDays === -1) {
        // Unlimited storage
        return { storageInfo: { unlimited: true, used: 0, limit: -1 } };
      }

      // Count active orders in storage
      const activeOrders = await db.query.orders.findMany({
        where: and(
          eq(orders.userId, userId),
          eq(orders.status, "shipped"), // Orders currently in storage
        ),
      });

      // Check orders approaching storage limit
      const storageExpiration = new Date(
        Date.now() - maxStorageDays * 24 * 60 * 60 * 1000,
      );
      const expiredOrders = activeOrders.filter(
        (order) => order.createdAt <= storageExpiration,
      );

      if (expiredOrders.length > 0) {
        throw new ForbiddenError(
          `${expiredOrders.length} orders have exceeded storage limit. Please arrange delivery.`,
        );
      }

      return {
        storageInfo: {
          unlimited: false,
          used: activeOrders.length,
          limit: maxStorageDays,
          approaching: activeOrders.filter((order) => {
            const daysInStorage = Math.floor(
              (Date.now() - order.createdAt.getTime()) / (24 * 60 * 60 * 1000),
            );
            return daysInStorage >= maxStorageDays - 3; // Warning 3 days before expiry
          }).length,
        },
      };
    });
}

/**
 * Rate limiting based on subscription tier
 */
export function subscriptionRateLimit(
  action: "order_creation" | "support_request",
) {
  return new Elysia({ name: `rate-limit-${action}` })
    .use(subscriptionMiddleware)
    .derive(async ({ subscription, store }) => {
      const userId = store?.user?.id;

      if (!userId) {
        return {}; // Skip rate limiting for anonymous users
      }

      const limits = {
        order_creation: {
          free: { requests: 2, windowHours: 24 },
          group: { requests: 10, windowHours: 24 },
          elite: { requests: 50, windowHours: 24 },
          vip_temp: { requests: 5, windowHours: 24 },
        },
        support_request: {
          free: { requests: 1, windowHours: 24 },
          group: { requests: 5, windowHours: 24 },
          elite: { requests: -1, windowHours: 24 }, // Unlimited
          vip_temp: { requests: 10, windowHours: 24 },
        },
      };

      const tierLimits = limits[action][subscription.tier];

      if (tierLimits.requests === -1) {
        return {}; // Unlimited
      }

      // Check rate limits in database (simplified implementation)
      const _windowStart = new Date(
        Date.now() - tierLimits.windowHours * 60 * 60 * 1000,
      );

      // This would require a rate_limits table - for now just return the info
      return {
        rateLimit: {
          action,
          tier: subscription.tier,
          limit: tierLimits.requests,
          windowHours: tierLimits.windowHours,
          resetTime: new Date(
            Date.now() + tierLimits.windowHours * 60 * 60 * 1000,
          ),
        },
      };
    });
}

/**
 * Add subscription warnings to response
 */
export function addSubscriptionWarnings() {
  return new Elysia({ name: "subscription-warnings" })
    .use(subscriptionMiddleware)
    .derive(({ subscription }) => {
      const warnings: string[] = [];

      // Free tier warnings
      if (subscription.tier === "free") {
        warnings.push(
          "Upgrade to Group subscription for faster processing and promotions access",
        );
      }

      // Expiring subscription warnings
      if (
        subscription.daysRemaining !== null &&
        subscription.daysRemaining <= 7
      ) {
        if (subscription.daysRemaining <= 0) {
          warnings.push(
            "Your subscription has expired. Upgrade to maintain premium features.",
          );
        } else {
          warnings.push(
            `Your subscription expires in ${subscription.daysRemaining} days.`,
          );
        }
      }

      // VIP temp specific warnings
      if (
        subscription.tier === "vip_temp" &&
        subscription.daysRemaining !== null
      ) {
        warnings.push(
          `VIP access expires in ${subscription.daysRemaining} days. Consider upgrading to Elite for permanent benefits.`,
        );
      }

      return { subscriptionWarnings: warnings };
    });
}

/**
 * Order-specific subscription middleware for validating order creation
 */
export function validateOrderCreation() {
  return new Elysia({ name: "validate-order-creation" })
    .use(subscriptionMiddleware)
    .derive(async ({ subscription, store }) => {
      const userId = store?.user?.id;
      const tier = subscription.tier;

      // VIP temp users can only have 1 order during their subscription period
      if (tier === "vip_temp" && userId) {
        const activeSubscription = await db.query.userSubscriptions.findFirst({
          where: and(
            eq(userSubscriptions.userId, userId),
            eq(userSubscriptions.tier, "vip_temp"),
            eq(userSubscriptions.status, "active"),
            gte(userSubscriptions.endDate, new Date()),
          ),
        });

        if (activeSubscription) {
          const ordersInPeriod = await db.query.orders.findMany({
            where: and(
              eq(orders.userId, userId),
              gte(orders.createdAt, activeSubscription.startDate),
            ),
          });

          if (ordersInPeriod.length >= 1) {
            throw new ForbiddenError(
              "VIP временный доступ ограничен 1 заказом за период",
            );
          }
        }
      }

      return {
        orderValidation: {
          canCreateOrder: true,
          processingTimeHours: subscription.features.processingTimeHours,
          storageTimeHours:
            subscription.features.maxStorageDays === -1
              ? -1
              : subscription.features.maxStorageDays * 24,
          priorityProcessing: subscription.features.hasPriorityProcessing,
        },
      };
    });
}

/**
 * Apply processing priority based on subscription tier
 */
export function applyOrderProcessingPriority() {
  return new Elysia({ name: "order-processing-priority" })
    .use(subscriptionMiddleware)
    .derive(({ subscription }) => {
      const tier = subscription.tier;

      // Priority levels: VIP temp & Elite = highest, Group = medium, Free = lowest
      const priorityLevels = {
        free: 1,
        group: 2,
        elite: 3,
        vip_temp: 3,
      };

      const processingDeadline = new Date(
        Date.now() + subscription.features.processingTimeHours * 60 * 60 * 1000,
      );

      return {
        orderPriority: {
          level: priorityLevels[tier],
          tier,
          processingDeadline,
          priorityProcessing: subscription.features.hasPriorityProcessing,
          processingTimeHours: subscription.features.processingTimeHours,
        },
      };
    });
}

/**
 * Check order value and recommend subscription upgrade
 */
export function checkOrderValueAndRecommendUpgrade() {
  return new Elysia({ name: "order-value-recommendations" })
    .use(subscriptionMiddleware)
    .derive(({ subscription }) => {
      const recommendations: string[] = [];

      if (subscription.tier === "free") {
        recommendations.push(
          "Для крупных заказов рекомендуем групповую или элитную подписку",
        );
        recommendations.push(
          "Групповая подписка: быстрая обработка, хранение до 3 месяцев",
        );
        recommendations.push(
          "Элитная подписка: приоритетная обработка, неограниченное хранение",
        );
      } else if (subscription.tier === "group") {
        recommendations.push(
          "Элитная подписка: приоритетная обработка и персональная поддержка",
        );
      }

      return {
        upgradeRecommendations: recommendations,
        currentTierBenefits: {
          processingTime: `${subscription.features.processingTimeHours} часов`,
          storage:
            subscription.features.maxStorageDays === -1
              ? "Неограниченное хранение"
              : `${subscription.features.maxStorageDays} дней хранения`,
          promotions: subscription.features.canParticipateInPromotions
            ? "Доступ к акциям"
            : "Нет доступа к акциям",
          combineOrders: subscription.features.canCombineOrders
            ? "Объединение заказов"
            : "Нет объединения",
        },
      };
    });
}

/**
 * Rate limiting specifically for order creation
 */
export function orderCreationRateLimit() {
  return new Elysia({ name: "order-creation-rate-limit" })
    .use(subscriptionMiddleware)
    .derive(async ({ subscription, store }) => {
      const userId = store?.user?.id;

      if (!userId) {
        // Anonymous users get basic rate limiting
        return {
          rateLimit: {
            maxOrdersPerDay: 1,
            tier: "anonymous",
            resetTime: new Date(Date.now() + 24 * 60 * 60 * 1000),
          },
        };
      }

      const dailyLimits = {
        free: 2,
        group: 10,
        elite: 50,
        vip_temp: 5,
      };

      // Check orders created in last 24 hours
      const last24Hours = new Date(Date.now() - 24 * 60 * 60 * 1000);
      const recentOrders = await db.query.orders.findMany({
        where: and(
          eq(orders.userId, userId),
          gte(orders.createdAt, last24Hours),
        ),
      });

      const ordersToday = recentOrders.length;
      const maxOrders = dailyLimits[subscription.tier];

      if (ordersToday >= maxOrders) {
        throw new ForbiddenError(
          `Превышен лимит заказов для тарифа ${subscription.tier}: ${maxOrders} заказов в день. Обновите подписку для увеличения лимита.`,
        );
      }

      return {
        rateLimit: {
          ordersToday,
          maxOrdersPerDay: maxOrders,
          remaining: maxOrders - ordersToday,
          tier: subscription.tier,
          resetTime: new Date(Date.now() + 24 * 60 * 60 * 1000),
        },
      };
    });
}

/**
 * Generate order number with tier-specific prefix
 */
export function generateTierOrderNumber() {
  return new Elysia({ name: "tier-order-number" })
    .use(subscriptionMiddleware)
    .derive(({ subscription }) => {
      const prefixes = {
        free: "YL",
        group: "YG",
        elite: "YE",
        vip_temp: "YV",
      };

      const prefix = prefixes[subscription.tier];
      const timestamp = Date.now().toString().slice(-6);
      const random = Math.floor(Math.random() * 1000)
        .toString()
        .padStart(3, "0");

      return {
        orderNumber: `${prefix}${timestamp}${random}`,
        tierPrefix: prefix,
      };
    });
}

/**
 * Complete order middleware that combines all order-specific checks
 */
export function orderSubscriptionMiddleware() {
  return new Elysia({ name: "order-subscription-complete" })
    .use(subscriptionMiddleware)
    .use(validateOrderCreation())
    .use(applyOrderProcessingPriority())
    .use(checkOrderValueAndRecommendUpgrade())
    .use(addSubscriptionWarnings())
    .derive(
      ({
        subscription,
        orderValidation,
        orderPriority,
        upgradeRecommendations,
        subscriptionWarnings,
      }) => {
        return {
          orderContext: {
            subscription: subscription,
            validation: orderValidation,
            priority: orderPriority,
            recommendations: upgradeRecommendations,
            warnings: subscriptionWarnings,
          },
        };
      },
    );
}
