import {
  pgTable,
  uuid,
  text,
  timestamp,
  pgEnum,
  index,
  boolean,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "./users";

// Notification type enum
export const notificationTypeEnum = pgEnum("notification_type", [
  "subscription_expiring",
  "subscription_expired",
  "subscription_renewed",
  "order_status",
  "system_announcement",
  "promotion",
]);

// Notification channel enum
export const notificationChannelEnum = pgEnum("notification_channel", [
  "email",
  "sms",
  "push",
  "in_app",
]);

// Notification status enum
export const notificationStatusEnum = pgEnum("notification_status", [
  "pending",
  "sent",
  "failed",
  "delivered",
  "read",
]);

// Notification history table
export const notificationHistory = pgTable(
  "notification_history",
  {
    id: uuid("id").primaryKey().defaultRandom(),

    // Reference to user
    userId: uuid("user_id").references(() => users.id),

    // Optional references
    subscriptionId: uuid("subscription_id"),
    orderId: uuid("order_id"),

    // Notification details
    type: notificationTypeEnum("type").notNull(),
    subtype: text("subtype"), // e.g., "7_days", "1_day" for expiring notifications
    channel: notificationChannelEnum("channel").notNull(),
    recipient: text("recipient").notNull(), // email address or phone number

    // Content
    subject: text("subject"),
    content: text("content").notNull(),

    // Status tracking
    status: notificationStatusEnum("status").default("pending").notNull(),
    statusMessage: text("status_message"), // Error message if failed

    // Timestamps
    scheduledFor: timestamp("scheduled_for"),
    sentAt: timestamp("sent_at"),
    deliveredAt: timestamp("delivered_at"),
    readAt: timestamp("read_at"),

    // Metadata
    metadata: text("metadata"), // JSON string for additional data

    // Audit
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
  },
  (table) => ({
    // Indexes for efficient querying
    userIdIdx: index("notification_history_user_id_idx").on(table.userId),
    typeIdx: index("notification_history_type_idx").on(table.type),
    statusIdx: index("notification_history_status_idx").on(table.status),
    scheduledForIdx: index("notification_history_scheduled_for_idx").on(
      table.scheduledFor,
    ),
    createdAtIdx: index("notification_history_created_at_idx").on(
      table.createdAt,
    ),

    // Composite indexes
    userTypeIdx: index("notification_history_user_type_idx").on(
      table.userId,
      table.type,
    ),
    subscriptionNotificationIdx: index(
      "notification_history_subscription_idx",
    ).on(table.subscriptionId, table.type),
  }),
);

// Notification preferences table (for user notification settings)
export const notificationPreferences = pgTable(
  "notification_preferences",
  {
    id: uuid("id").primaryKey().defaultRandom(),

    // Reference to user
    userId: uuid("user_id")
      .references(() => users.id)
      .notNull(),

    // Channel preferences
    emailEnabled: boolean("email_enabled").default(true).notNull(),
    smsEnabled: boolean("sms_enabled").default(false).notNull(),
    pushEnabled: boolean("push_enabled").default(true).notNull(),
    inAppEnabled: boolean("in_app_enabled").default(true).notNull(),

    // Type-specific preferences
    subscriptionNotifications: boolean("subscription_notifications")
      .default(true)
      .notNull(),
    orderNotifications: boolean("order_notifications").default(true).notNull(),
    promotionNotifications: boolean("promotion_notifications")
      .default(false)
      .notNull(),
    systemNotifications: boolean("system_notifications")
      .default(true)
      .notNull(),

    // Timing preferences
    quietHoursStart: text("quiet_hours_start"), // e.g., "22:00"
    quietHoursEnd: text("quiet_hours_end"), // e.g., "08:00"
    timezone: text("timezone").default("Europe/Moscow").notNull(),

    // Audit
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
  },
  (table) => ({
    userIdIdx: index("notification_preferences_user_id_idx").on(table.userId),
  }),
);

// Email templates table (if not already exists)
export const emailTemplates = pgTable(
  "email_templates",
  {
    id: uuid("id").primaryKey().defaultRandom(),

    // Template identification
    name: text("name").notNull().unique(), // e.g., 'subscription_expiring'
    displayName: text("display_name").notNull(),
    description: text("description"),

    // Template content
    subject: text("subject").notNull(),
    htmlContent: text("html_content").notNull(),
    textContent: text("text_content"),

    // Template settings
    isActive: boolean("is_active").default(true).notNull(),
    language: text("language").default("ru").notNull(),
    category: text("category").default("system").notNull(),

    // Variables documentation
    availableVariables: text("available_variables"), // JSON array of variable names

    // Audit
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
    createdBy: uuid("created_by"),
  },
  (table) => ({
    nameIdx: index("email_templates_name_idx").on(table.name),
    categoryIdx: index("email_templates_category_idx").on(table.category),
    isActiveIdx: index("email_templates_is_active_idx").on(table.isActive),
  }),
);

// Zod schemas for validation
export const insertEmailTemplateSchema = createInsertSchema(emailTemplates);
export const selectEmailTemplateSchema = createSelectSchema(emailTemplates);

// Types
export type EmailTemplate = typeof emailTemplates.$inferSelect;
export type NewEmailTemplate = typeof emailTemplates.$inferInsert;
