import {
  db,
  orders,
  userSubscriptions,
  eq,
  and,
  gte,
  desc,
} from "@lolita-fashion/db";
import {
  isSubscriptionActive,
  SUBSCRIPTION_TIERS,
} from "@lolita-fashion/shared";
import {
  NotFoundError,
  ValidationError,
} from "../middleware/error";

export interface StorageItem {
  orderId: string;
  orderNumber: string;
  customerName: string;
  status: "in_storage" | "approaching_expiry" | "expired" | "ready_for_pickup";
  storageEntryDate: Date;
  storageExpiryDate: Date | null;
  daysInStorage: number;
  daysUntilExpiry: number | null;
  subscriptionTier: "free" | "group" | "elite" | "vip_temp";
}

export interface StorageStats {
  totalItems: number;
  byTier: {
    free: number;
    group: number;
    elite: number;
    vip_temp: number;
  };
  approaching_expiry: number;
  expired: number;
  avgDaysInStorage: number;
}

export interface UserStorageInfo {
  currentTier: "free" | "group" | "elite" | "vip_temp";
  maxStorageDays: number; // -1 for unlimited
  itemsInStorage: number;
  storageUsagePercent: number | null; // null for unlimited
  itemsApproachingExpiry: StorageItem[];
  itemsExpired: StorageItem[];
  nextExpiryDate: Date | null;
}

class StorageService {
  /**
   * Get user's current subscription tier for storage calculations
   */
  private async getUserSubscriptionTier(
    userId: string,
  ): Promise<"free" | "group" | "elite" | "vip_temp"> {
    const activeSubscription = await db.query.userSubscriptions.findFirst({
      where: and(
        eq(userSubscriptions.userId, userId),
        eq(userSubscriptions.status, "active"),
        gte(userSubscriptions.endDate, new Date()),
      ),
      orderBy: desc(userSubscriptions.endDate),
    });

    if (
      activeSubscription &&
      isSubscriptionActive(activeSubscription.endDate)
    ) {
      return activeSubscription.tier;
    }

    return "free";
  }

  /**
   * Calculate storage expiry date based on subscription tier
   */
  private calculateStorageExpiry(
    storageEntryDate: Date,
    tier: "free" | "group" | "elite" | "vip_temp",
  ): Date | null {
    const tierInfo = SUBSCRIPTION_TIERS[tier];
    const maxStorageDays = tierInfo.features.maxStorageDays;

    if (maxStorageDays === -1) {
      return null; // Unlimited storage
    }

    return new Date(
      storageEntryDate.getTime() + maxStorageDays * 24 * 60 * 60 * 1000,
    );
  }

  /**
   * Get all items currently in storage
   */
  async getStorageItems(filters?: {
    userId?: string;
    tier?: "free" | "group" | "elite" | "vip_temp";
    status?: "approaching_expiry" | "expired";
  }): Promise<StorageItem[]> {
    // Get orders that are shipped (in storage)
    const whereConditions = [eq(orders.status, "shipped")];

    if (filters?.userId) {
      whereConditions.push(eq(orders.userId, filters.userId));
    }

    const ordersInStorage = await db.query.orders.findMany({
      where: and(...whereConditions),
      orderBy: desc(orders.createdAt),
    });

    const storageItems: StorageItem[] = [];

    for (const order of ordersInStorage) {
      let tier: "free" | "group" | "elite" | "vip_temp" = "free";

      // If order has a user, get their tier at the time of storage entry
      if (order.userId) {
        tier = await this.getUserSubscriptionTier(order.userId);
      }

      // For orders, storage entry date is when they were shipped
      const storageEntryDate = order.updatedAt || order.createdAt;
      const storageExpiryDate = this.calculateStorageExpiry(
        storageEntryDate,
        tier,
      );

      const now = new Date();
      const daysInStorage = Math.floor(
        (now.getTime() - storageEntryDate.getTime()) / (24 * 60 * 60 * 1000),
      );

      let daysUntilExpiry: number | null = null;
      let status: StorageItem["status"] = "in_storage";

      if (storageExpiryDate) {
        daysUntilExpiry = Math.floor(
          (storageExpiryDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000),
        );

        if (daysUntilExpiry <= 0) {
          status = "expired";
        } else if (daysUntilExpiry <= 3) {
          status = "approaching_expiry";
        }
      }

      // Apply tier filter if specified
      if (filters?.tier && tier !== filters.tier) {
        continue;
      }

      // Apply status filter if specified
      if (filters?.status && status !== filters.status) {
        continue;
      }

      storageItems.push({
        orderId: order.id,
        orderNumber: order.nomerok,
        customerName: order.customerName,
        status,
        storageEntryDate,
        storageExpiryDate,
        daysInStorage,
        daysUntilExpiry,
        subscriptionTier: tier,
      });
    }

    return storageItems;
  }

  /**
   * Get storage statistics for admin dashboard
   */
  async getStorageStats(): Promise<StorageStats> {
    const allItems = await this.getStorageItems();

    const stats: StorageStats = {
      totalItems: allItems.length,
      byTier: {
        free: 0,
        group: 0,
        elite: 0,
        vip_temp: 0,
      },
      approaching_expiry: 0,
      expired: 0,
      avgDaysInStorage: 0,
    };

    let totalDaysInStorage = 0;

    for (const item of allItems) {
      stats.byTier[item.subscriptionTier]++;
      totalDaysInStorage += item.daysInStorage;

      if (item.status === "approaching_expiry") {
        stats.approaching_expiry++;
      } else if (item.status === "expired") {
        stats.expired++;
      }
    }

    if (allItems.length > 0) {
      stats.avgDaysInStorage = Math.round(totalDaysInStorage / allItems.length);
    }

    return stats;
  }

  /**
   * Get storage info for specific user
   */
  async getUserStorageInfo(userId: string): Promise<UserStorageInfo> {
    const currentTier = await this.getUserSubscriptionTier(userId);
    const tierInfo = SUBSCRIPTION_TIERS[currentTier];
    const maxStorageDays = tierInfo.features.maxStorageDays;

    const userItems = await this.getStorageItems({ userId });

    const itemsApproachingExpiry = userItems.filter(
      (item) => item.status === "approaching_expiry",
    );
    const itemsExpired = userItems.filter((item) => item.status === "expired");

    // Calculate storage usage percentage
    let storageUsagePercent: number | null = null;
    if (maxStorageDays !== -1) {
      const itemsNearExpiry = userItems.filter(
        (item) => item.daysUntilExpiry !== null && item.daysUntilExpiry <= 3,
      );
      storageUsagePercent =
        userItems.length > 0
          ? (itemsNearExpiry.length / userItems.length) * 100
          : 0;
    }

    // Find next expiry date
    let nextExpiryDate: Date | null = null;
    const itemsWithExpiry = userItems
      .filter((item) => item.storageExpiryDate !== null)
      .sort(
        (a, b) =>
          a.storageExpiryDate!.getTime() - b.storageExpiryDate!.getTime(),
      );

    if (itemsWithExpiry.length > 0) {
      nextExpiryDate = itemsWithExpiry[0].storageExpiryDate;
    }

    return {
      currentTier,
      maxStorageDays,
      itemsInStorage: userItems.length,
      storageUsagePercent,
      itemsApproachingExpiry,
      itemsExpired,
      nextExpiryDate,
    };
  }

  /**
   * Process storage expiration notifications and cleanup
   */
  async processStorageExpirations(): Promise<{
    notificationsToSend: Array<{
      userId: string;
      email?: string;
      phone?: string;
      orderNumber: string;
      daysUntilExpiry: number;
      tier: string;
    }>;
    expiredItems: StorageItem[];
    processed: number;
  }> {
    const allItems = await this.getStorageItems();
    const notificationsToSend: any[] = [];
    const expiredItems: StorageItem[] = [];

    for (const item of allItems) {
      // Send notifications for items approaching expiry (3 days warning)
      if (
        item.status === "approaching_expiry" &&
        item.daysUntilExpiry !== null
      ) {
        // Get user details for notification
        const order = await db.query.orders.findFirst({
          where: eq(orders.id, item.orderId),
          with: {
            user: {
              columns: {
                email: true,
                phone: true,
              },
            },
          },
        });

        if (order?.user) {
          notificationsToSend.push({
            userId: order.userId!,
            email: order.user.email,
            phone: order.user.phone,
            orderNumber: item.orderNumber,
            daysUntilExpiry: item.daysUntilExpiry,
            tier: item.subscriptionTier,
          });
        }
      }

      // Track expired items
      if (item.status === "expired") {
        expiredItems.push(item);
      }
    }

    return {
      notificationsToSend,
      expiredItems,
      processed: notificationsToSend.length + expiredItems.length,
    };
  }

  /**
   * Move order from storage to delivery
   */
  async moveToDelivery(
    orderId: string,
    _adminUserId: string,
  ): Promise<{ success: boolean; message: string }> {
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, orderId),
    });

    if (!order) {
      throw new NotFoundError("Order not found");
    }

    if (order.status !== "shipped") {
      throw new ValidationError("Order is not in storage");
    }

    // Update order status to delivered or out_for_delivery
    await db
      .update(orders)
      .set({
        status: "out_for_delivery",
        updatedAt: new Date(),
      })
      .where(eq(orders.id, orderId));

    return {
      success: true,
      message: `Order ${order.nomerok} moved from storage to delivery`,
    };
  }

  /**
   * Extend storage for specific order (admin function)
   */
  async extendStorage(
    orderId: string,
    additionalDays: number,
    _adminUserId: string,
  ): Promise<{ success: boolean; message: string }> {
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, orderId),
    });

    if (!order) {
      throw new NotFoundError("Order not found");
    }

    // This would require adding an extension field to orders table
    // For now, we'll just update the notes field
    const currentNotes = order.notes || "";
    const extensionNote = `[${new Date().toISOString()}] Storage extended by ${additionalDays} days by admin`;
    const updatedNotes = currentNotes
      ? `${currentNotes}\n${extensionNote}`
      : extensionNote;

    await db
      .update(orders)
      .set({
        notes: updatedNotes,
        updatedAt: new Date(),
      })
      .where(eq(orders.id, orderId));

    return {
      success: true,
      message: `Storage extended by ${additionalDays} days for order ${order.nomerok}`,
    };
  }
}

// Export singleton instance
export const storageService = new StorageService();
