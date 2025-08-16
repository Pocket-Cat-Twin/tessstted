import {
  db,
  userSubscriptions,
  users,
  notificationHistory,
  eq,
  and,
  gte,
  lte,
  desc,
  asc,
} from "@yuyu/db";
import {
  sendSubscriptionExpiringEmail,
  sendSubscriptionExpiredEmail,
  sendSubscriptionRenewedEmail,
} from "./email";
import { smsService } from "./sms";

export interface NotificationSchedule {
  subscriptionId: string;
  userId: string;
  tier: string;
  expiresAt: Date;
  daysRemaining: number;
  notificationsSent: string[];
  shouldNotify: boolean;
}

export interface NotificationResult {
  success: boolean;
  message: string;
  subscriptionId: string;
  notificationType: string;
  sentAt: Date;
}

export interface NotificationStats {
  processed: number;
  emailsSent: number;
  smsSent: number;
  failed: number;
  errors: string[];
}

class NotificationService {
  /**
   * Get subscriptions that need expiration notifications
   */
  async getExpiringSubscriptions(): Promise<NotificationSchedule[]> {
    const now = new Date();
    const next30Days = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);

    // Get active subscriptions expiring in the next 30 days
    const expiringSubscriptions = await db.query.userSubscriptions.findMany({
      where: and(
        eq(userSubscriptions.status, "active"),
        gte(userSubscriptions.endDate, now), // Not expired yet
        lte(userSubscriptions.endDate, next30Days), // Expires within 30 days
      ),
      with: {
        user: {
          columns: {
            id: true,
            name: true,
            email: true,
            phone: true,
            preferences: true,
          },
        },
      },
      orderBy: asc(userSubscriptions.endDate),
    });

    const schedules: NotificationSchedule[] = [];

    for (const subscription of expiringSubscriptions) {
      const daysRemaining = Math.ceil(
        (subscription.endDate.getTime() - now.getTime()) /
          (24 * 60 * 60 * 1000),
      );

      // Get notification history for this subscription
      const sentNotifications = await db.query.notificationHistory.findMany({
        where: and(
          eq(notificationHistory.subscriptionId, subscription.id),
          eq(notificationHistory.type, "subscription_expiring"),
        ),
        orderBy: desc(notificationHistory.createdAt),
      });

      const notificationsSent = sentNotifications.map(
        (n) => n.subtype || "email",
      );

      // Determine if we should send notification based on days remaining
      const shouldNotify = this.shouldSendExpirationNotification(
        daysRemaining,
        notificationsSent,
      );

      schedules.push({
        subscriptionId: subscription.id,
        userId: subscription.userId,
        tier: subscription.tier,
        expiresAt: subscription.endDate,
        daysRemaining,
        notificationsSent,
        shouldNotify,
      });
    }

    return schedules.filter((s) => s.shouldNotify);
  }

  /**
   * Determine if we should send expiration notification based on days remaining
   */
  private shouldSendExpirationNotification(
    daysRemaining: number,
    sentNotifications: string[],
  ): boolean {
    // Send notifications at 14 days, 7 days, 3 days, 1 day before expiration
    const notificationPoints = [14, 7, 3, 1];

    for (const point of notificationPoints) {
      if (daysRemaining <= point) {
        const notificationKey = `${point}_days`;
        if (!sentNotifications.includes(notificationKey)) {
          return true;
        }
      }
    }

    return false;
  }

  /**
   * Send expiration notification for a specific subscription
   */
  async sendExpirationNotification(
    schedule: NotificationSchedule,
  ): Promise<NotificationResult[]> {
    const results: NotificationResult[] = [];

    try {
      // Get user details
      const user = await db.query.users.findFirst({
        where: eq(users.id, schedule.userId),
      });

      if (!user) {
        throw new Error("User not found");
      }

      const preferences = (user.preferences as any) || {};
      const emailEnabled = preferences.emailNotifications !== false;
      const smsEnabled = preferences.smsNotifications === true;

      // Determine notification subtype based on days remaining
      let notificationSubtype: string;
      if (schedule.daysRemaining <= 1) {
        notificationSubtype = "1_days";
      } else if (schedule.daysRemaining <= 3) {
        notificationSubtype = "3_days";
      } else if (schedule.daysRemaining <= 7) {
        notificationSubtype = "7_days";
      } else {
        notificationSubtype = "14_days";
      }

      const expirationDateStr = schedule.expiresAt.toLocaleDateString("ru-RU");

      // Send email notification
      if (emailEnabled && user.email) {
        try {
          await sendSubscriptionExpiringEmail(
            user.email,
            user.name || "Пользователь",
            schedule.tier,
            schedule.daysRemaining,
            expirationDateStr,
          );

          results.push({
            success: true,
            message: "Email notification sent successfully",
            subscriptionId: schedule.subscriptionId,
            notificationType: "email",
            sentAt: new Date(),
          });

          // Record notification in history
          await db.insert(notificationHistory).values({
            userId: schedule.userId,
            subscriptionId: schedule.subscriptionId,
            type: "subscription_expiring",
            subtype: notificationSubtype,
            channel: "email",
            recipient: user.email,
            status: "sent",
            content: `Subscription ${schedule.tier} expires in ${schedule.daysRemaining} days`,
          });
        } catch (error) {
          results.push({
            success: false,
            message: `Email failed: ${error.message}`,
            subscriptionId: schedule.subscriptionId,
            notificationType: "email",
            sentAt: new Date(),
          });
        }
      }

      // Send SMS notification (if enabled and phone available)
      if (smsEnabled && user.phone) {
        try {
          const smsMessage = `YuYu: Ваша подписка ${this.getTierDisplayName(schedule.tier)} истекает через ${schedule.daysRemaining} дн. Продлите на сайте.`;

          await smsService.sendNotificationSms(user.phone, smsMessage);

          results.push({
            success: true,
            message: "SMS notification sent successfully",
            subscriptionId: schedule.subscriptionId,
            notificationType: "sms",
            sentAt: new Date(),
          });

          // Record SMS notification in history
          await db.insert(notificationHistory).values({
            userId: schedule.userId,
            subscriptionId: schedule.subscriptionId,
            type: "subscription_expiring",
            subtype: notificationSubtype,
            channel: "sms",
            recipient: user.phone,
            status: "sent",
            content: smsMessage,
          });
        } catch (error) {
          results.push({
            success: false,
            message: `SMS failed: ${error.message}`,
            subscriptionId: schedule.subscriptionId,
            notificationType: "sms",
            sentAt: new Date(),
          });
        }
      }
    } catch (error) {
      results.push({
        success: false,
        message: `Notification failed: ${error.message}`,
        subscriptionId: schedule.subscriptionId,
        notificationType: "general",
        sentAt: new Date(),
      });
    }

    return results;
  }

  /**
   * Process all expiring subscription notifications
   */
  async processExpirationNotifications(): Promise<NotificationStats> {
    const stats: NotificationStats = {
      processed: 0,
      emailsSent: 0,
      smsSent: 0,
      failed: 0,
      errors: [],
    };

    try {
      const expiringSubscriptions = await this.getExpiringSubscriptions();

      for (const schedule of expiringSubscriptions) {
        const results = await this.sendExpirationNotification(schedule);

        stats.processed++;

        for (const result of results) {
          if (result.success) {
            if (result.notificationType === "email") {
              stats.emailsSent++;
            } else if (result.notificationType === "sms") {
              stats.smsSent++;
            }
          } else {
            stats.failed++;
            stats.errors.push(`${schedule.subscriptionId}: ${result.message}`);
          }
        }
      }
    } catch (error) {
      stats.errors.push(`Process failed: ${error.message}`);
      console.error("Failed to process expiration notifications:", error);
    }

    return stats;
  }

  /**
   * Send notification when subscription expires
   */
  async sendSubscriptionExpiredNotification(
    subscriptionId: string,
  ): Promise<NotificationResult[]> {
    const results: NotificationResult[] = [];

    try {
      const subscription = await db.query.userSubscriptions.findFirst({
        where: eq(userSubscriptions.id, subscriptionId),
        with: {
          user: true,
        },
      });

      if (!subscription || !subscription.user) {
        throw new Error("Subscription or user not found");
      }

      const user = subscription.user;
      const preferences = (user.preferences as any) || {};
      const emailEnabled = preferences.emailNotifications !== false;

      const expiredDateStr = subscription.endDate.toLocaleDateString("ru-RU");

      // Send email notification
      if (emailEnabled && user.email) {
        try {
          await sendSubscriptionExpiredEmail(
            user.email,
            user.name || "Пользователь",
            subscription.tier,
            expiredDateStr,
          );

          results.push({
            success: true,
            message: "Expiration email sent successfully",
            subscriptionId,
            notificationType: "email",
            sentAt: new Date(),
          });

          // Record notification
          await db.insert(notificationHistory).values({
            userId: user.id,
            subscriptionId,
            type: "subscription_expired",
            channel: "email",
            recipient: user.email,
            status: "sent",
            content: `Subscription ${subscription.tier} has expired`,
          });
        } catch (error) {
          results.push({
            success: false,
            message: `Expiration email failed: ${error.message}`,
            subscriptionId,
            notificationType: "email",
            sentAt: new Date(),
          });
        }
      }
    } catch (error) {
      results.push({
        success: false,
        message: `Expiration notification failed: ${error.message}`,
        subscriptionId,
        notificationType: "general",
        sentAt: new Date(),
      });
    }

    return results;
  }

  /**
   * Send notification when subscription is renewed
   */
  async sendSubscriptionRenewedNotification(
    subscriptionId: string,
  ): Promise<NotificationResult[]> {
    const results: NotificationResult[] = [];

    try {
      const subscription = await db.query.userSubscriptions.findFirst({
        where: eq(userSubscriptions.id, subscriptionId),
        with: {
          user: true,
        },
      });

      if (!subscription || !subscription.user) {
        throw new Error("Subscription or user not found");
      }

      const user = subscription.user;
      const preferences = (user.preferences as any) || {};
      const emailEnabled = preferences.emailNotifications !== false;

      const renewedDateStr = subscription.startDate.toLocaleDateString("ru-RU");
      const nextExpirationDateStr =
        subscription.endDate.toLocaleDateString("ru-RU");

      // Send email notification
      if (emailEnabled && user.email) {
        try {
          await sendSubscriptionRenewedEmail(
            user.email,
            user.name || "Пользователь",
            subscription.tier,
            renewedDateStr,
            nextExpirationDateStr,
          );

          results.push({
            success: true,
            message: "Renewal email sent successfully",
            subscriptionId,
            notificationType: "email",
            sentAt: new Date(),
          });

          // Record notification
          await db.insert(notificationHistory).values({
            userId: user.id,
            subscriptionId,
            type: "subscription_renewed",
            channel: "email",
            recipient: user.email,
            status: "sent",
            content: `Subscription ${subscription.tier} renewed until ${nextExpirationDateStr}`,
          });
        } catch (error) {
          results.push({
            success: false,
            message: `Renewal email failed: ${error.message}`,
            subscriptionId,
            notificationType: "email",
            sentAt: new Date(),
          });
        }
      }
    } catch (error) {
      results.push({
        success: false,
        message: `Renewal notification failed: ${error.message}`,
        subscriptionId,
        notificationType: "general",
        sentAt: new Date(),
      });
    }

    return results;
  }

  /**
   * Get user-friendly tier display name
   */
  private getTierDisplayName(tier: string): string {
    const tierNames = {
      free: "Обычная",
      group: "Групповая",
      elite: "Элитная",
      vip_temp: "VIP временная",
    };

    return tierNames[tier] || tier;
  }

  /**
   * Get notification history for user
   */
  async getUserNotificationHistory(
    userId: string,
    limit: number = 50,
  ): Promise<any[]> {
    return await db.query.notificationHistory.findMany({
      where: eq(notificationHistory.userId, userId),
      orderBy: desc(notificationHistory.createdAt),
      limit,
    });
  }

  /**
   * Get notification statistics
   */
  async getNotificationStats(days: number = 30): Promise<{
    totalSent: number;
    byType: Record<string, number>;
    byChannel: Record<string, number>;
    successRate: number;
  }> {
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

    const notifications = await db.query.notificationHistory.findMany({
      where: gte(notificationHistory.createdAt, since),
    });

    const totalSent = notifications.length;
    const successful = notifications.filter((n) => n.status === "sent").length;

    const byType = notifications.reduce(
      (acc, n) => {
        acc[n.type] = (acc[n.type] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    const byChannel = notifications.reduce(
      (acc, n) => {
        acc[n.channel] = (acc[n.channel] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return {
      totalSent,
      byType,
      byChannel,
      successRate: totalSent > 0 ? (successful / totalSent) * 100 : 0,
    };
  }
}

// Export singleton instance
export const notificationService = new NotificationService();
