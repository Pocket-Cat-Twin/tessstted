import {
  db,
  userSubscriptions,
  subscriptionHistory,
  users,
  eq,
  and,
  gte,
  sql,
} from "@yuyu/db";
import {
  SUBSCRIPTION_TIERS,
  calculateSubscriptionEndDate,
  isSubscriptionActive,
  getEffectiveTier,
} from "@yuyu/shared";
import {
  NotFoundError,
  ValidationError,
  ConflictError,
} from "../middleware/error";

export interface PurchaseSubscriptionData {
  tier: "group" | "elite" | "vip_temp";
  paymentMethod: string;
  paymentReference?: string;
  autoRenew?: boolean;
}

export interface SubscriptionPurchaseResult {
  subscription: {
    id: string;
    tier: string;
    price: number;
    startDate: Date;
    endDate: Date;
    status: string;
  };
  previousTier: string;
  upgraded: boolean;
  savings?: number; // If upgraded from existing subscription
}

export interface SubscriptionStats {
  totalSubscriptions: number;
  activeSubscriptions: number;
  subscriptionsByTier: Record<string, number>;
  monthlyRevenue: number;
  churnRate: number;
  upgradeRate: number;
}

class SubscriptionService {
  /**
   * Purchase or upgrade subscription
   */
  async purchaseSubscription(
    userId: string,
    data: PurchaseSubscriptionData,
  ): Promise<SubscriptionPurchaseResult> {
    const user = await db.query.users.findFirst({
      where: eq(users.id, userId),
    });

    if (!user) {
      throw new NotFoundError("User not found");
    }

    const targetTier = SUBSCRIPTION_TIERS[data.tier];
    if (!targetTier) {
      throw new ValidationError("Invalid subscription tier");
    }

    // Get current active subscription
    const currentSubscription = await db.query.userSubscriptions.findFirst({
      where: and(
        eq(userSubscriptions.userId, userId),
        eq(userSubscriptions.status, "active"),
        gte(userSubscriptions.endDate, new Date()),
      ),
      orderBy: userSubscriptions.endDate,
    });

    let previousTier = "free";
    let upgraded = true;
    let savings = 0;

    if (currentSubscription) {
      previousTier = currentSubscription.tier;

      // Check if this is actually an upgrade
      const tierLevels = { free: 0, group: 1, elite: 2, vip_temp: 1.5 };
      upgraded = tierLevels[data.tier] > tierLevels[currentSubscription.tier];

      // Handle VIP temp as special case - can be purchased alongside other subscriptions
      if (data.tier !== "vip_temp" && currentSubscription.tier !== "vip_temp") {
        // Calculate remaining time value for refund/upgrade
        const remainingDays = Math.max(
          0,
          Math.ceil(
            (currentSubscription.endDate.getTime() - Date.now()) /
              (24 * 60 * 60 * 1000),
          ),
        );

        if (remainingDays > 0) {
          const dailyValue = Number(currentSubscription.price) / 30; // Assuming monthly subscriptions
          savings = remainingDays * dailyValue;
        }

        // Deactivate current subscription
        await db
          .update(userSubscriptions)
          .set({ status: "cancelled", updatedAt: new Date() })
          .where(eq(userSubscriptions.id, currentSubscription.id));
      }
    }

    // Calculate subscription dates
    const startDate = new Date();
    const endDate = calculateSubscriptionEndDate(data.tier, startDate);

    if (!endDate) {
      throw new ValidationError("Invalid subscription duration");
    }

    // Create new subscription
    const [newSubscription] = await db
      .insert(userSubscriptions)
      .values({
        userId,
        tier: data.tier,
        status: "active",
        price: (targetTier.price - savings).toString(),
        startDate,
        endDate,
        autoRenew: data.autoRenew || false,
        paymentReference: data.paymentReference,
      })
      .returning();

    // Record subscription history
    await db.insert(subscriptionHistory).values({
      userId,
      subscriptionId: newSubscription.id,
      action: currentSubscription ? "upgraded" : "created",
      fromTier: previousTier as any,
      toTier: data.tier,
      amount: newSubscription.price,
      paymentMethod: data.paymentMethod,
      notes: savings > 0 ? `Savings applied: ${savings} RUB` : undefined,
    });

    return {
      subscription: {
        id: newSubscription.id,
        tier: newSubscription.tier,
        price: Number(newSubscription.price),
        startDate: newSubscription.startDate,
        endDate: newSubscription.endDate,
        status: newSubscription.status,
      },
      previousTier,
      upgraded,
      savings: savings > 0 ? savings : undefined,
    };
  }

  /**
   * Cancel subscription (disable auto-renewal)
   */
  async cancelSubscription(
    userId: string,
    subscriptionId?: string,
  ): Promise<void> {
    let subscription;

    if (subscriptionId) {
      // Cancel specific subscription
      subscription = await db.query.userSubscriptions.findFirst({
        where: and(
          eq(userSubscriptions.id, subscriptionId),
          eq(userSubscriptions.userId, userId),
        ),
      });
    } else {
      // Cancel current active subscription
      subscription = await db.query.userSubscriptions.findFirst({
        where: and(
          eq(userSubscriptions.userId, userId),
          eq(userSubscriptions.status, "active"),
          gte(userSubscriptions.endDate, new Date()),
        ),
        orderBy: userSubscriptions.endDate,
      });
    }

    if (!subscription) {
      throw new NotFoundError("Active subscription not found");
    }

    if (subscription.status === "cancelled") {
      throw new ConflictError("Subscription is already cancelled");
    }

    // Just disable auto-renewal, let subscription expire naturally
    await db
      .update(userSubscriptions)
      .set({
        autoRenew: false,
        updatedAt: new Date(),
      })
      .where(eq(userSubscriptions.id, subscription.id));

    // Record cancellation in history
    await db.insert(subscriptionHistory).values({
      userId,
      subscriptionId: subscription.id,
      action: "cancelled",
      fromTier: subscription.tier,
      toTier: subscription.tier, // Same tier, just cancelled
      notes: "Auto-renewal disabled by user",
    });
  }

  /**
   * Renew expired or expiring subscription
   */
  async renewSubscription(
    userId: string,
    paymentMethod: string,
    paymentReference?: string,
  ): Promise<SubscriptionPurchaseResult> {
    const currentSubscription = await db.query.userSubscriptions.findFirst({
      where: and(eq(userSubscriptions.userId, userId)),
      orderBy: userSubscriptions.endDate, // Get most recent
    });

    if (!currentSubscription) {
      throw new NotFoundError("No subscription history found");
    }

    // Renew with the same tier
    return this.purchaseSubscription(userId, {
      tier: currentSubscription.tier as "group" | "elite" | "vip_temp",
      paymentMethod,
      paymentReference,
      autoRenew: currentSubscription.autoRenew,
    });
  }

  /**
   * Process auto-renewals (to be called by scheduled job)
   */
  async processAutoRenewals(): Promise<{
    processed: number;
    failed: number;
    errors: string[];
  }> {
    const errors: string[] = [];
    let processed = 0;
    let failed = 0;

    // Find subscriptions that need auto-renewal (expiring in next 24 hours)
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);

    const expiringSubscriptions = await db.query.userSubscriptions.findMany({
      where: and(
        eq(userSubscriptions.status, "active"),
        eq(userSubscriptions.autoRenew, true),
        gte(tomorrow, userSubscriptions.endDate), // Expiring before tomorrow
      ),
      with: {
        user: true,
      },
    });

    for (const subscription of expiringSubscriptions) {
      try {
        // Create new subscription (simplified - in real app would charge payment method)
        const endDate = calculateSubscriptionEndDate(subscription.tier as any);
        if (!endDate) continue;

        await db.insert(userSubscriptions).values({
          userId: subscription.userId,
          tier: subscription.tier,
          status: "active",
          price: subscription.price,
          startDate: subscription.endDate, // Start where previous ended
          endDate,
          autoRenew: subscription.autoRenew,
          paymentReference: `auto-renewal-${Date.now()}`,
        });

        // Mark old subscription as expired
        await db
          .update(userSubscriptions)
          .set({ status: "expired" })
          .where(eq(userSubscriptions.id, subscription.id));

        // Record in history
        await db.insert(subscriptionHistory).values({
          userId: subscription.userId,
          subscriptionId: subscription.id,
          action: "renewed",
          fromTier: subscription.tier,
          toTier: subscription.tier,
          amount: subscription.price,
          paymentMethod: "auto-renewal",
          notes: "Automatically renewed",
        });

        processed++;
      } catch (error) {
        console.error(
          `Failed to renew subscription ${subscription.id}:`,
          error,
        );
        errors.push(`Subscription ${subscription.id}: ${error.message}`);
        failed++;
      }
    }

    return { processed, failed, errors };
  }

  /**
   * Get subscription analytics
   */
  async getSubscriptionStats(): Promise<SubscriptionStats> {
    // Total subscriptions ever created
    const [{ totalSubscriptions }] = await db
      .select({ totalSubscriptions: sql<number>`count(*)` })
      .from(userSubscriptions);

    // Active subscriptions
    const [{ activeSubscriptions }] = await db
      .select({ activeSubscriptions: sql<number>`count(*)` })
      .from(userSubscriptions)
      .where(
        and(
          eq(userSubscriptions.status, "active"),
          gte(userSubscriptions.endDate, new Date()),
        ),
      );

    // Subscriptions by tier
    const tierCounts = await db
      .select({
        tier: userSubscriptions.tier,
        count: sql<number>`count(*)`,
      })
      .from(userSubscriptions)
      .where(
        and(
          eq(userSubscriptions.status, "active"),
          gte(userSubscriptions.endDate, new Date()),
        ),
      )
      .groupBy(userSubscriptions.tier);

    const subscriptionsByTier = tierCounts.reduce(
      (acc, { tier, count }) => {
        acc[tier] = count;
        return acc;
      },
      {} as Record<string, number>,
    );

    // Monthly revenue (last 30 days)
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const [{ monthlyRevenue }] = await db
      .select({
        monthlyRevenue: sql<number>`sum(cast(${userSubscriptions.price} as decimal))`,
      })
      .from(userSubscriptions)
      .where(gte(userSubscriptions.createdAt, thirtyDaysAgo));

    // Churn rate (cancelled/expired vs total in last 30 days)
    const [{ churnedSubscriptions }] = await db
      .select({
        churnedSubscriptions: sql<number>`count(*)`,
      })
      .from(userSubscriptions)
      .where(
        and(
          sql`${userSubscriptions.status} IN ('cancelled', 'expired')`,
          gte(userSubscriptions.updatedAt, thirtyDaysAgo),
        ),
      );

    const churnRate =
      totalSubscriptions > 0
        ? (churnedSubscriptions / totalSubscriptions) * 100
        : 0;

    // Upgrade rate (from subscription history)
    const [{ upgrades }] = await db
      .select({
        upgrades: sql<number>`count(*)`,
      })
      .from(subscriptionHistory)
      .where(
        and(
          eq(subscriptionHistory.action, "upgraded"),
          gte(subscriptionHistory.createdAt, thirtyDaysAgo),
        ),
      );

    const upgradeRate =
      totalSubscriptions > 0 ? (upgrades / totalSubscriptions) * 100 : 0;

    return {
      totalSubscriptions: totalSubscriptions || 0,
      activeSubscriptions: activeSubscriptions || 0,
      subscriptionsByTier,
      monthlyRevenue: monthlyRevenue || 0,
      churnRate: Number(churnRate.toFixed(2)),
      upgradeRate: Number(upgradeRate.toFixed(2)),
    };
  }

  /**
   * Get user's subscription status and recommendations
   */
  async getUserSubscriptionInfo(userId: string): Promise<{
    currentTier: string;
    isActive: boolean;
    expiresAt: Date | null;
    daysRemaining: number | null;
    features: any;
    recommendations: string[];
    availableUpgrades: Array<{
      tier: string;
      price: number;
      benefits: string[];
      savings?: number;
    }>;
  }> {
    const currentSubscription = await db.query.userSubscriptions.findFirst({
      where: and(
        eq(userSubscriptions.userId, userId),
        eq(userSubscriptions.status, "active"),
        gte(userSubscriptions.endDate, new Date()),
      ),
      orderBy: userSubscriptions.endDate,
    });

    let currentTier: string = "free";
    let isActive = true;
    let expiresAt: Date | null = null;

    if (currentSubscription) {
      currentTier = currentSubscription.tier;
      expiresAt = currentSubscription.endDate;
      isActive = isSubscriptionActive(currentSubscription.endDate);
    }

    const effectiveTier = getEffectiveTier(currentTier as any, expiresAt);
    const features = SUBSCRIPTION_TIERS[effectiveTier].features;

    // Calculate days remaining
    let daysRemaining: number | null = null;
    if (expiresAt) {
      const diffTime = expiresAt.getTime() - Date.now();
      daysRemaining = Math.max(0, Math.ceil(diffTime / (24 * 60 * 60 * 1000)));
    }

    // Generate recommendations
    const recommendations: string[] = [];
    if (currentTier === "free") {
      recommendations.push(
        "Upgrade to Group subscription for faster processing and promotions",
      );
    } else if (currentTier === "group") {
      recommendations.push(
        "Upgrade to Elite for unlimited storage and personal support",
      );
    } else if (daysRemaining && daysRemaining <= 7) {
      recommendations.push(
        "Your subscription expires soon. Renew to keep your benefits",
      );
    }

    // Available upgrades
    const availableUpgrades = Object.entries(SUBSCRIPTION_TIERS)
      .filter(([tier]) => tier !== effectiveTier && tier !== "free")
      .map(([tier, info]) => ({
        tier,
        price: info.price,
        benefits: this.getTierBenefits(tier as any),
      }));

    return {
      currentTier: effectiveTier,
      isActive,
      expiresAt,
      daysRemaining,
      features,
      recommendations,
      availableUpgrades,
    };
  }

  /**
   * Get benefits for a specific tier
   */
  private getTierBenefits(tier: "group" | "elite" | "vip_temp"): string[] {
    const benefits = {
      group: [
        "Хранение до 3 месяцев",
        "Объединение заказов",
        "Обработка 2-4 дня",
        "Доступ к групповым акциям",
      ],
      elite: [
        "Безлимитное хранение",
        "Приоритетная обработка",
        "Персональная поддержка",
        "Проверка товаров",
        "Закрытые акции",
      ],
      vip_temp: [
        "Экстренная обработка",
        "VIP поддержка",
        "Максимальное внимание",
        "7 дней доступа",
      ],
    };

    return benefits[tier] || [];
  }
}

// Export singleton instance
export const subscriptionService = new SubscriptionService();
