import {
  db,
  orders,
  userSubscriptions,
  eq,
  and,
  gte,
} from "@yuyu/db";
import {
  calculateTotalCommission,
  isSubscriptionActive,
  SUBSCRIPTION_TIERS,
} from "@yuyu/shared";
import { generateRandomString } from "@yuyu/shared";
import {
  NotFoundError,
  ValidationError,
  ForbiddenError,
} from "../middleware/error";

export interface CreateOrderData {
  customerName: string;
  customerPhone: string;
  customerEmail?: string;
  deliveryAddress: string;
  deliveryMethod: string;
  paymentMethod: string;
  goods: Array<{
    name: string;
    link?: string;
    quantity: number;
    priceYuan: number;
  }>;
}

export interface OrderProcessingInfo {
  userId?: string;
  canProcess: boolean;
  processingTimeHours: number;
  storageTimeHours: number;
  priorityProcessing: boolean;
  restrictions: string[];
  subscriptionTier: "free" | "group" | "elite" | "vip_temp";
}

export interface DetailedOrderCalculation {
  goods: Array<{
    name: string;
    quantity: number;
    priceYuan: number;
    commissionYuan: number;
    commissionRuble: number;
    commissionType: "percentage_low" | "percentage_standard" | "flat_fee_high";
    totalYuan: number;
    totalRuble: number;
  }>;
  totals: {
    originalPriceYuan: number;
    originalPriceRuble: number;
    totalCommissionYuan: number;
    totalCommissionRuble: number;
    totalFinalPriceYuan: number;
    totalFinalPriceRuble: number;
  };
  exchangeRate: number;
}

class OrderService {
  /**
   * Get processing information for user based on subscription tier
   */
  async getOrderProcessingInfo(userId?: string): Promise<OrderProcessingInfo> {
    let subscriptionTier: "free" | "group" | "elite" | "vip_temp" = "free";
    let activeSubscription = null;

    if (userId) {
      // Get user's active subscription
      activeSubscription = await db.query.userSubscriptions.findFirst({
        where: and(
          eq(userSubscriptions.userId, userId),
          eq(userSubscriptions.status, "active"),
          gte(userSubscriptions.endDate, new Date()),
        ),
        orderBy: userSubscriptions.endDate, // Get latest expiring one
      });

      if (
        activeSubscription &&
        isSubscriptionActive(activeSubscription.endDate)
      ) {
        subscriptionTier = activeSubscription.tier;
      }
    }

    const tierInfo = SUBSCRIPTION_TIERS[subscriptionTier];
    const features = tierInfo.features;

    const restrictions: string[] = [];

    // Add restrictions based on tier
    if (subscriptionTier === "free") {
      restrictions.push("Обработка заказов до 5 рабочих дней");
      restrictions.push("Хранение на складе до 14 дней");
      restrictions.push("Нет участия в акциях");
      restrictions.push("Нет объединения посылок");
    } else if (subscriptionTier === "vip_temp") {
      restrictions.push("Разовый VIP доступ (до 7 дней)");
      restrictions.push("Ограничено 1 заказом с максимальным вниманием");
    }

    return {
      userId,
      canProcess: true, // For now, all users can create orders
      processingTimeHours: features.processingTimeHours,
      storageTimeHours:
        features.maxStorageDays === -1 ? -1 : features.maxStorageDays * 24,
      priorityProcessing: features.hasPriorityProcessing,
      restrictions,
      subscriptionTier,
    };
  }

  /**
   * Calculate detailed order pricing with commission breakdown
   */
  async calculateDetailedOrder(
    goods: Array<{ name: string; quantity: number; priceYuan: number }>,
    exchangeRate: number,
  ): Promise<DetailedOrderCalculation> {
    const items = goods.map((good) => ({
      priceYuan: good.priceYuan,
      quantity: good.quantity,
    }));

    const calculation = calculateTotalCommission(items, exchangeRate);

    const detailedGoods = goods.map((good, index) => {
      const itemCalc = calculation.items[index];

      return {
        name: good.name,
        quantity: good.quantity,
        priceYuan: good.priceYuan,
        commissionYuan: itemCalc.commissionYuan,
        commissionRuble: itemCalc.commissionRuble,
        commissionType: itemCalc.calculationType,
        totalYuan:
          good.priceYuan * good.quantity +
          itemCalc.commissionYuan * good.quantity,
        totalRuble: itemCalc.totalFinalPrice,
      };
    });

    return {
      goods: detailedGoods,
      totals: {
        originalPriceYuan: calculation.totals.originalPriceYuan,
        originalPriceRuble: calculation.totals.originalPriceRuble,
        totalCommissionYuan: calculation.totals.totalCommissionYuan,
        totalCommissionRuble: calculation.totals.totalCommissionRuble,
        totalFinalPriceYuan:
          calculation.totals.originalPriceYuan +
          calculation.totals.totalCommissionYuan,
        totalFinalPriceRuble: calculation.totals.totalFinalPriceRuble,
      },
      exchangeRate,
    };
  }

  /**
   * Validate order creation for user (subscription limits, restrictions)
   */
  async validateOrderCreation(
    userId?: string,
    orderData?: CreateOrderData,
  ): Promise<{
    canCreate: boolean;
    errors: string[];
    warnings: string[];
    processingInfo: OrderProcessingInfo;
  }> {
    const processingInfo = await this.getOrderProcessingInfo(userId);
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check for VIP temp restrictions
    if (processingInfo.subscriptionTier === "vip_temp" && userId) {
      // Check if user already has an order in this VIP period
      const subscription = await db.query.userSubscriptions.findFirst({
        where: and(
          eq(userSubscriptions.userId, userId),
          eq(userSubscriptions.tier, "vip_temp"),
          eq(userSubscriptions.status, "active"),
          gte(userSubscriptions.endDate, new Date()),
        ),
      });

      if (subscription) {
        const ordersInPeriod = await db.query.orders.findMany({
          where: and(
            eq(orders.userId, userId),
            gte(orders.createdAt, subscription.startDate),
          ),
        });

        if (ordersInPeriod.length >= 1) {
          errors.push("VIP временный доступ ограничен 1 заказом за период");
        }
      }
    }

    // Add warnings for free users
    if (processingInfo.subscriptionTier === "free") {
      warnings.push("Обработка займет до 5 рабочих дней");
      warnings.push("Хранение на складе ограничено 14 днями");
      warnings.push("Нет доступа к акциям и специальным предложениям");
    }

    // Check order value for recommendations
    if (orderData) {
      const totalValue = orderData.goods.reduce(
        (sum, good) => sum + good.priceYuan * good.quantity,
        0,
      );

      if (totalValue > 500 && processingInfo.subscriptionTier === "free") {
        warnings.push(
          "Для крупных заказов рекомендуем групповую или элитную подписку",
        );
      }
    }

    return {
      canCreate: errors.length === 0,
      errors,
      warnings,
      processingInfo,
    };
  }

  /**
   * Get order processing deadline based on subscription tier
   */
  getProcessingDeadline(
    subscriptionTier: "free" | "group" | "elite" | "vip_temp",
  ): Date {
    const tierInfo = SUBSCRIPTION_TIERS[subscriptionTier];
    const hoursToAdd = tierInfo.features.processingTimeHours;

    return new Date(Date.now() + hoursToAdd * 60 * 60 * 1000);
  }

  /**
   * Get storage expiration date based on subscription tier
   */
  getStorageExpiration(
    subscriptionTier: "free" | "group" | "elite" | "vip_temp",
  ): Date | null {
    const tierInfo = SUBSCRIPTION_TIERS[subscriptionTier];
    const maxStorageDays = tierInfo.features.maxStorageDays;

    if (maxStorageDays === -1) return null; // Unlimited

    return new Date(Date.now() + maxStorageDays * 24 * 60 * 60 * 1000);
  }

  /**
   * Generate order number with prefix based on subscription tier
   */
  generateOrderNomerok(
    subscriptionTier: "free" | "group" | "elite" | "vip_temp" = "free",
  ): string {
    const prefix = {
      free: "YL",
      group: "YG",
      elite: "YE",
      vip_temp: "YV",
    }[subscriptionTier];

    const timestamp = Date.now().toString().slice(-6);
    const random = Math.floor(Math.random() * 1000)
      .toString()
      .padStart(3, "0");

    return `${prefix}${timestamp}${random}`;
  }

  /**
   * Check if user can combine orders (group/elite/vip_temp feature)
   */
  async canCombineOrders(userId: string): Promise<boolean> {
    const processingInfo = await this.getOrderProcessingInfo(userId);
    return processingInfo.subscriptionTier !== "free";
  }

  /**
   * Get user's current storage limit usage
   */
  async getStorageUsage(userId: string): Promise<{
    activeOrders: number;
    storageLimit: number; // -1 for unlimited
    storageUsagePercent: number | null; // null for unlimited
    willExpireSoon: boolean;
  }> {
    const processingInfo = await this.getOrderProcessingInfo(userId);
    const tierInfo = SUBSCRIPTION_TIERS[processingInfo.subscriptionTier];

    // Count orders in storage (shipped but not delivered)
    const activeOrders = await db.query.orders.findMany({
      where: and(
        eq(orders.userId, userId),
        eq(orders.status, "shipped"), // Orders on storage
      ),
    });

    const storageLimit = tierInfo.features.maxStorageDays;
    let storageUsagePercent = null;
    let willExpireSoon = false;

    if (storageLimit !== -1) {
      // Check how many orders are close to storage limit
      const expirationThreshold = new Date(
        Date.now() - (storageLimit - 3) * 24 * 60 * 60 * 1000,
      );
      const ordersNearExpiry = activeOrders.filter(
        (order) => order.createdAt <= expirationThreshold,
      );

      storageUsagePercent =
        activeOrders.length > 0
          ? (ordersNearExpiry.length / activeOrders.length) * 100
          : 0;
      willExpireSoon = ordersNearExpiry.length > 0;
    }

    return {
      activeOrders: activeOrders.length,
      storageLimit,
      storageUsagePercent,
      willExpireSoon,
    };
  }
}

// Export singleton instance
export const orderService = new OrderService();
