import { Elysia, t } from "elysia";
import { requireAuth, requireAdmin } from "../middleware/auth";
import { notificationService } from "../services/notification";
import {
  db,
  users,
  notificationHistory,
  notificationPreferences,
  eq,
} from "@yuyu/db";
import { sendEmail } from "../services/email";
import { smsService } from "../services/sms";
import { NotFoundError } from "../middleware/error";

export const notificationRoutes = new Elysia({ prefix: "/notifications" })

  // User notification endpoints (require auth)
  .use(requireAuth)

  // Get user notification history
  .get(
    "/history",
    async ({ store, query }) => {
      const userId = store.user.id;
      const limit = query.limit || 50;

      const history = await notificationService.getUserNotificationHistory(
        userId,
        limit,
      );

      return {
        success: true,
        data: { history },
      };
    },
    {
      query: t.Object({
        limit: t.Optional(t.Number({ minimum: 1, maximum: 100 })),
      }),
      detail: {
        summary: "Get user notification history",
        description: "Get notification history for the current user",
        tags: ["Notifications"],
      },
    },
  )

  // Get user notification preferences
  .get(
    "/preferences",
    async ({ store }) => {
      const userId = store.user.id;

      // Get preferences from database or return defaults
      const preferences = await db.query.notificationPreferences.findFirst({
        where: eq(notificationPreferences.userId, userId),
      });

      const defaultPreferences = {
        emailEnabled: true,
        smsEnabled: false,
        pushEnabled: true,
        inAppEnabled: true,
        subscriptionNotifications: true,
        orderNotifications: true,
        promotionNotifications: false,
        systemNotifications: true,
        quietHoursStart: null,
        quietHoursEnd: null,
        timezone: "Europe/Moscow",
      };

      return {
        success: true,
        data: {
          preferences: preferences || defaultPreferences,
        },
      };
    },
    {
      detail: {
        summary: "Get notification preferences",
        description: "Get current user notification preferences",
        tags: ["Notifications"],
      },
    },
  )

  // Update user notification preferences
  .put(
    "/preferences",
    async ({ store, body }) => {
      const userId = store.user.id;

      // Check if preferences exist
      const existing = await db.query.notificationPreferences.findFirst({
        where: eq(notificationPreferences.userId, userId),
      });

      if (existing) {
        // Update existing preferences
        await db
          .update(notificationPreferences)
          .set({
            ...body,
            updatedAt: new Date(),
          })
          .where(eq(notificationPreferences.userId, userId));
      } else {
        // Create new preferences
        await db.insert(notificationPreferences).values({
          userId,
          ...body,
        });
      }

      return {
        success: true,
        message: "Notification preferences updated successfully",
      };
    },
    {
      body: t.Object({
        emailEnabled: t.Optional(t.Boolean()),
        smsEnabled: t.Optional(t.Boolean()),
        pushEnabled: t.Optional(t.Boolean()),
        inAppEnabled: t.Optional(t.Boolean()),
        subscriptionNotifications: t.Optional(t.Boolean()),
        orderNotifications: t.Optional(t.Boolean()),
        promotionNotifications: t.Optional(t.Boolean()),
        systemNotifications: t.Optional(t.Boolean()),
        quietHoursStart: t.Optional(t.String()),
        quietHoursEnd: t.Optional(t.String()),
        timezone: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update notification preferences",
        description: "Update user notification preferences",
        tags: ["Notifications"],
      },
    },
  )

  // Test notification (send test notification to current user)
  .post(
    "/test",
    async ({ store, body }) => {
      const userId = store.user.id;

      // Get user details
      const user = await db.query.users.findFirst({
        where: eq(users.id, userId),
      });

      if (!user) {
        throw new NotFoundError("User not found");
      }

      // Create test notification
      const results = [];

      if (body.type === "email" && user.email) {
        try {
          await sendEmail("welcome", user.email, {
            name: user.name || "Пользователь",
            testMessage: "Это тестовое уведомление для проверки email системы",
          });

          results.push({
            type: "email",
            success: true,
            message: "Test email sent successfully",
          });
        } catch (error) {
          results.push({
            type: "email",
            success: false,
            message: `Email failed: ${error.message}`,
          });
        }
      }

      if (body.type === "sms" && user.phone) {
        try {
          await smsService.sendNotificationSms(user.phone, "YuYu: Тестовое SMS уведомление");

          results.push({
            type: "sms",
            success: true,
            message: "Test SMS sent successfully",
          });
        } catch (error) {
          results.push({
            type: "sms",
            success: false,
            message: `SMS failed: ${error.message}`,
          });
        }
      }

      return {
        success: true,
        message: "Test notifications processed",
        data: { results },
      };
    },
    {
      body: t.Object({
        type: t.Union([t.Literal("email"), t.Literal("sms"), t.Literal("all")]),
      }),
      detail: {
        summary: "Send test notification",
        description: "Send test notification to current user",
        tags: ["Notifications"],
      },
    },
  )

  // Admin notification endpoints
  .use(requireAdmin)

  // Process expiration notifications manually
  .post(
    "/admin/process-expiring",
    async () => {
      const stats = await notificationService.processExpirationNotifications();

      return {
        success: true,
        message: `Processed ${stats.processed} subscriptions, sent ${stats.emailsSent} emails and ${stats.smsSent} SMS`,
        data: { stats },
      };
    },
    {
      detail: {
        summary: "Process expiring subscription notifications (Admin)",
        description:
          "Manually trigger processing of expiring subscription notifications",
        tags: ["Notifications"],
      },
    },
  )

  // Get expiring subscriptions schedule
  .get(
    "/admin/expiring-schedule",
    async () => {
      const expiringSubscriptions =
        await notificationService.getExpiringSubscriptions();

      return {
        success: true,
        data: {
          expiringSubscriptions,
          count: expiringSubscriptions.length,
        },
      };
    },
    {
      detail: {
        summary: "Get expiring subscriptions schedule (Admin)",
        description:
          "Get list of subscriptions that need expiration notifications",
        tags: ["Notifications"],
      },
    },
  )

  // Get notification statistics
  .get(
    "/admin/stats",
    async ({ query }) => {
      const days = query.days || 30;
      const stats = await notificationService.getNotificationStats(days);

      return {
        success: true,
        data: { stats },
      };
    },
    {
      query: t.Object({
        days: t.Optional(t.Number({ minimum: 1, maximum: 365 })),
      }),
      detail: {
        summary: "Get notification statistics (Admin)",
        description: "Get notification statistics for specified period",
        tags: ["Notifications"],
      },
    },
  )

  // Send custom notification to user
  .post(
    "/admin/send-custom",
    async ({ body }) => {
      const results = [];

      // Get user details
      const user = await db.query.users.findFirst({
        where: eq(users.id, body.userId),
      });

      if (!user) {
        throw new NotFoundError("User not found");
      }

      // Send custom notification
      if (body.channels.includes("email") && user.email) {
        try {
          await sendEmail("system_announcement", user.email, {
            name: user.name || "Пользователь",
            message: body.message,
            subject: body.subject,
          });

          results.push({
            type: "email",
            success: true,
            message: "Custom email sent successfully",
          });

          // Record notification
          await db.insert(notificationHistory).values({
            userId: body.userId,
            type: "system_announcement",
            channel: "email",
            recipient: user.email,
            subject: body.subject,
            content: body.message,
            status: "sent",
          });
        } catch (error) {
          results.push({
            type: "email",
            success: false,
            message: `Email failed: ${error.message}`,
          });
        }
      }

      if (body.channels.includes("sms") && user.phone) {
        try {
          await smsService.sendNotificationSms(user.phone, `YuYu: ${body.message}`);

          results.push({
            type: "sms",
            success: true,
            message: "Custom SMS sent successfully",
          });

          // Record notification
          await db.insert(notificationHistory).values({
            userId: body.userId,
            type: "system_announcement",
            channel: "sms",
            recipient: user.phone,
            content: body.message,
            status: "sent",
          });
        } catch (error) {
          results.push({
            type: "sms",
            success: false,
            message: `SMS failed: ${error.message}`,
          });
        }
      }

      return {
        success: true,
        message: "Custom notifications processed",
        data: { results },
      };
    },
    {
      body: t.Object({
        userId: t.String(),
        subject: t.String({ minLength: 1 }),
        message: t.String({ minLength: 1 }),
        channels: t.Array(t.Union([t.Literal("email"), t.Literal("sms")])),
      }),
      detail: {
        summary: "Send custom notification (Admin)",
        description: "Send custom notification to specific user",
        tags: ["Notifications"],
      },
    },
  );
