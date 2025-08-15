import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  boolean,
  integer,
  pgEnum,
  json,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";

// Webhook event enum
export const webhookEventEnum = pgEnum("webhook_event", [
  "user.created",
  "user.updated",
  "user.deleted",
  "order.created", 
  "order.updated",
  "order.status_changed",
  "subscription.created",
  "subscription.renewed",
  "subscription.expired",
  "subscription.cancelled",
  "payment.completed",
  "payment.failed",
]);

// Webhook status enum
export const webhookStatusEnum = pgEnum("webhook_status", [
  "pending",
  "success",
  "failed",
  "retry",
]);

// Webhook subscriptions table
export const webhookSubscriptions = pgTable("webhook_subscriptions", {
  id: uuid("id").defaultRandom().primaryKey(),
  
  // Webhook details
  url: text("url").notNull(),
  events: json("events").notNull(), // Array of webhook events to subscribe to
  secret: varchar("secret", { length: 255 }).notNull(), // For signature verification
  
  // Configuration
  isActive: boolean("is_active").default(true).notNull(),
  retryCount: integer("retry_count").default(0).notNull(),
  maxRetries: integer("max_retries").default(3).notNull(),
  
  // Metadata
  description: text("description"),
  headers: json("headers"), // Additional headers to send
  
  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
  lastTriggeredAt: timestamp("last_triggered_at"),
});

// Webhook logs table
export const webhookLogs = pgTable("webhook_logs", {
  id: uuid("id").defaultRandom().primaryKey(),
  
  // Reference to subscription
  subscriptionId: uuid("subscription_id").references(() => webhookSubscriptions.id, {
    onDelete: "cascade",
  }),
  
  // Event details
  event: webhookEventEnum("event").notNull(),
  payload: json("payload").notNull(),
  
  // Request details
  url: text("url").notNull(),
  method: varchar("method", { length: 10 }).default("POST").notNull(),
  headers: json("headers"),
  
  // Response details
  status: webhookStatusEnum("status").default("pending").notNull(),
  httpStatus: integer("http_status"),
  responseBody: text("response_body"),
  responseHeaders: json("response_headers"),
  
  // Timing
  attemptNumber: integer("attempt_number").default(1).notNull(),
  processingTimeMs: integer("processing_time_ms"),
  
  // Error tracking
  errorMessage: text("error_message"),
  
  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  sentAt: timestamp("sent_at"),
  completedAt: timestamp("completed_at"),
});

// Zod schemas for validation
export const insertWebhookSubscriptionSchema = createInsertSchema(webhookSubscriptions);
export const selectWebhookSubscriptionSchema = createSelectSchema(webhookSubscriptions);
export const insertWebhookLogSchema = createInsertSchema(webhookLogs);
export const selectWebhookLogSchema = createSelectSchema(webhookLogs);

// Types
export type WebhookSubscription = typeof webhookSubscriptions.$inferSelect;
export type NewWebhookSubscription = typeof webhookSubscriptions.$inferInsert;
export type WebhookLog = typeof webhookLogs.$inferSelect;
export type NewWebhookLog = typeof webhookLogs.$inferInsert;