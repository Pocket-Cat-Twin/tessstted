import {
  db,
  orders,
  userSubscriptions,
  orderStatusHistory,
  eq,
  and,
  gte,
  asc,
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

export interface PriorityQueueItem {
  orderId: string;
  orderNumber: string;
  customerName: string;
  subscriptionTier: "free" | "group" | "elite" | "vip_temp";
  priorityLevel: number; // 1=lowest, 3=highest
  status: "created" | "processing" | "confirmed" | "shipped" | "delivered";
  createdAt: Date;
  processingDeadline: Date;
  isOverdue: boolean;
  minutesUntilDeadline: number;
  assignedTo?: string; // Admin user ID
  lastUpdated: Date;
}

export interface ProcessingQueue {
  highPriority: PriorityQueueItem[];
  mediumPriority: PriorityQueueItem[];
  lowPriority: PriorityQueueItem[];
  overdue: PriorityQueueItem[];
}

export interface PriorityStats {
  totalOrders: number;
  byPriority: {
    high: number;
    medium: number;
    low: number;
  };
  overdue: number;
  avgProcessingTime: {
    elite: number;
    vip_temp: number;
    group: number;
    free: number;
  };
  responseTimeCompliance: {
    elite: number; // Percentage meeting 12h response target
    vip_temp: number; // Percentage meeting 6h response target
    group: number; // Percentage meeting 24h response target
    free: number; // Percentage meeting 48h response target
  };
}

class PriorityProcessingService {
  /**
   * Get priority level for subscription tier
   */
  private getPriorityLevel(
    tier: "free" | "group" | "elite" | "vip_temp",
  ): number {
    const levels = {
      free: 1, // Low priority
      group: 2, // Medium priority
      elite: 3, // High priority
      vip_temp: 3, // High priority (same as elite)
    };
    return levels[tier];
  }

  /**
   * Calculate processing deadline based on subscription tier
   */
  private calculateProcessingDeadline(
    createdAt: Date,
    tier: "free" | "group" | "elite" | "vip_temp",
  ): Date {
    const tierInfo = SUBSCRIPTION_TIERS[tier];
    const hours = tierInfo.features.processingTimeHours;
    return new Date(createdAt.getTime() + hours * 60 * 60 * 1000);
  }

  /**
   * Get user's subscription tier for an order
   */
  private async getOrderSubscriptionTier(
    userId?: string,
  ): Promise<"free" | "group" | "elite" | "vip_temp"> {
    if (!userId) return "free";

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
   * Get all orders in processing queue with priority sorting
   */
  async getProcessingQueue(filters?: {
    assignedTo?: string;
    status?: string[];
    priorityLevel?: number;
  }): Promise<ProcessingQueue> {
    // Get orders that need processing (not delivered or cancelled)
    const statusFilter = filters?.status || [
      "created",
      "processing",
      "confirmed",
      "shipped",
    ];

    // Orders that are in processing statuses

    const ordersNeedingProcessing = await db.query.orders.findMany({
      orderBy: [asc(orders.createdAt)],
      with: {
        user: {
          columns: {
            id: true,
          },
        },
      },
    });

    const queueItems: PriorityQueueItem[] = [];
    const now = new Date();

    for (const order of ordersNeedingProcessing) {
      // Skip orders not in target statuses
      if (!statusFilter.includes(order.status)) continue;

      const tier = await this.getOrderSubscriptionTier(
        order.userId || undefined,
      );
      const priorityLevel = this.getPriorityLevel(tier);

      // Apply priority filter if specified
      if (filters?.priorityLevel && priorityLevel !== filters.priorityLevel)
        continue;

      const processingDeadline = this.calculateProcessingDeadline(
        order.createdAt,
        tier,
      );
      const minutesUntilDeadline = Math.floor(
        (processingDeadline.getTime() - now.getTime()) / (60 * 1000),
      );
      const isOverdue = minutesUntilDeadline < 0;

      // Check if order is assigned to specific admin
      let assignedTo: string | undefined;
      const lastStatusUpdate = await db.query.orderStatusHistory.findFirst({
        where: eq(orderStatusHistory.orderId, order.id),
        orderBy: desc(orderStatusHistory.createdAt),
        with: {
          user: {
            columns: {
              id: true,
              name: true,
            },
          },
        },
      });

      if (lastStatusUpdate?.user) {
        assignedTo = lastStatusUpdate.userId || undefined;
      }

      // Apply assigned filter if specified
      if (filters?.assignedTo && assignedTo !== filters.assignedTo) continue;

      queueItems.push({
        orderId: order.id,
        orderNumber: order.nomerok,
        customerName: order.customerName,
        subscriptionTier: tier,
        priorityLevel,
        status: order.status as any,
        createdAt: order.createdAt,
        processingDeadline,
        isOverdue,
        minutesUntilDeadline,
        assignedTo,
        lastUpdated: order.updatedAt || order.createdAt,
      });
    }

    // Sort queue items by priority and deadline
    queueItems.sort((a, b) => {
      // First, sort by priority level (higher priority first)
      if (a.priorityLevel !== b.priorityLevel) {
        return b.priorityLevel - a.priorityLevel;
      }
      // Then by deadline (most urgent first)
      return a.processingDeadline.getTime() - b.processingDeadline.getTime();
    });

    // Separate into priority queues
    const result: ProcessingQueue = {
      highPriority: queueItems.filter(
        (item) => item.priorityLevel === 3 && !item.isOverdue,
      ),
      mediumPriority: queueItems.filter(
        (item) => item.priorityLevel === 2 && !item.isOverdue,
      ),
      lowPriority: queueItems.filter(
        (item) => item.priorityLevel === 1 && !item.isOverdue,
      ),
      overdue: queueItems.filter((item) => item.isOverdue),
    };

    return result;
  }

  /**
   * Assign order to admin for processing
   */
  async assignOrderToAdmin(
    orderId: string,
    adminId: string,
    comment?: string,
  ): Promise<{
    success: boolean;
    message: string;
  }> {
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, orderId),
    });

    if (!order) {
      throw new NotFoundError("Order not found");
    }

    // Check if order is in a status that can be assigned
    const assignableStatuses = ["created", "processing", "confirmed"];
    if (!assignableStatuses.includes(order.status)) {
      throw new ValidationError(
        `Order status ${order.status} cannot be assigned`,
      );
    }

    // Create status history entry to track assignment
    await db.insert(orderStatusHistory).values({
      orderId,
      userId: adminId,
      fromStatus: order.status,
      toStatus: order.status, // Status stays the same, just assigning
      comment: comment || `Order assigned to admin for priority processing`,
    });

    return {
      success: true,
      message: `Order ${order.nomerok} assigned successfully`,
    };
  }

  /**
   * Get priority processing statistics
   */
  async getPriorityStats(): Promise<PriorityStats> {
    const queue = await this.getProcessingQueue();

    const totalOrders =
      queue.highPriority.length +
      queue.mediumPriority.length +
      queue.lowPriority.length +
      queue.overdue.length;

    // Calculate average processing times by tier
    const avgProcessingTime = {
      elite: 12, // Target: 12 hours
      vip_temp: 6, // Target: 6 hours
      group: 24, // Target: 24 hours
      free: 48, // Target: 48 hours
    };

    // Calculate response time compliance (mock data for now)
    const responseTimeCompliance = {
      elite: 95, // 95% meeting 12h target
      vip_temp: 98, // 98% meeting 6h target
      group: 87, // 87% meeting 24h target
      free: 72, // 72% meeting 48h target
    };

    return {
      totalOrders,
      byPriority: {
        high: queue.highPriority.length,
        medium: queue.mediumPriority.length,
        low: queue.lowPriority.length,
      },
      overdue: queue.overdue.length,
      avgProcessingTime,
      responseTimeCompliance,
    };
  }

  /**
   * Get next order to process based on priority
   */
  async getNextOrderToProcess(
    adminId?: string,
  ): Promise<PriorityQueueItem | null> {
    const queue = await this.getProcessingQueue({ assignedTo: adminId });

    // Priority order: overdue first, then high, medium, low
    if (queue.overdue.length > 0) {
      return queue.overdue[0];
    }
    if (queue.highPriority.length > 0) {
      return queue.highPriority[0];
    }
    if (queue.mediumPriority.length > 0) {
      return queue.mediumPriority[0];
    }
    if (queue.lowPriority.length > 0) {
      return queue.lowPriority[0];
    }

    return null;
  }

  /**
   * Process order with priority handling
   */
  async processOrderWithPriority(
    orderId: string,
    adminId: string,
    newStatus: string,
    comment?: string,
  ): Promise<{
    success: boolean;
    message: string;
    priorityInfo: {
      tier: string;
      priorityLevel: number;
      wasOverdue: boolean;
      processingTime: number; // minutes
    };
  }> {
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, orderId),
    });

    if (!order) {
      throw new NotFoundError("Order not found");
    }

    const tier = await this.getOrderSubscriptionTier(order.userId || undefined);
    const priorityLevel = this.getPriorityLevel(tier);
    const processingDeadline = this.calculateProcessingDeadline(
      order.createdAt,
      tier,
    );
    const now = new Date();
    const wasOverdue = now > processingDeadline;
    const processingTime = Math.floor(
      (now.getTime() - order.createdAt.getTime()) / (60 * 1000),
    );

    // Update order status
    await db
      .update(orders)
      .set({
        status: newStatus,
        updatedAt: now,
      })
      .where(eq(orders.id, orderId));

    // Create status history entry
    await db.insert(orderStatusHistory).values({
      orderId,
      userId: adminId,
      fromStatus: order.status,
      toStatus: newStatus,
      comment:
        comment || `Status updated with priority processing (${tier} tier)`,
    });

    return {
      success: true,
      message: `Order ${order.nomerok} processed successfully`,
      priorityInfo: {
        tier,
        priorityLevel,
        wasOverdue,
        processingTime,
      },
    };
  }

  /**
   * Get orders requiring urgent attention
   */
  async getUrgentOrders(): Promise<PriorityQueueItem[]> {
    const queue = await this.getProcessingQueue();
    const urgentItems: PriorityQueueItem[] = [];

    // Add overdue orders
    urgentItems.push(...queue.overdue);

    // Add high priority orders due within 2 hours
    const twoHoursFromNow = new Date(Date.now() + 2 * 60 * 60 * 1000);
    urgentItems.push(
      ...queue.highPriority.filter(
        (item) => item.processingDeadline <= twoHoursFromNow,
      ),
    );

    // Sort by urgency (overdue first, then by deadline)
    urgentItems.sort((a, b) => {
      if (a.isOverdue && !b.isOverdue) return -1;
      if (!a.isOverdue && b.isOverdue) return 1;
      return a.processingDeadline.getTime() - b.processingDeadline.getTime();
    });

    return urgentItems;
  }

  /**
   * Auto-assign orders to available admins based on workload
   */
  async autoAssignOrders(): Promise<{
    assigned: number;
    results: Array<{
      orderId: string;
      orderNumber: string;
      assignedTo: string;
      tier: string;
    }>;
  }> {
    // This would implement auto-assignment logic based on admin availability
    // For now, return mock data
    return {
      assigned: 0,
      results: [],
    };
  }
}

// Export singleton instance
export const priorityService = new PriorityProcessingService();
