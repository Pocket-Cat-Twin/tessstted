import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  integer,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "./users.js";

// Verification type enum
export const verificationTypeEnum = pgEnum("verification_type", [
  "email_registration", // Email verification during registration
  "phone_registration", // SMS verification during registration
  "password_reset", // Password reset verification
  "phone_change", // Phone number change verification
  "email_change", // Email change verification
  "login_2fa", // Two-factor authentication
]);

// Verification status enum
export const verificationStatusEnum = pgEnum("verification_status", [
  "pending",
  "verified",
  "expired",
  "failed",
]);

// Verification tokens table
export const verificationTokens = pgTable("verification_tokens", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: uuid("user_id").references(() => users.id, { onDelete: "cascade" }),

  // Verification details
  type: verificationTypeEnum("type").notNull(),
  status: verificationStatusEnum("status").default("pending").notNull(),

  // Contact information
  email: varchar("email", { length: 255 }),
  phone: varchar("phone", { length: 50 }),

  // Token and code
  token: varchar("token", { length: 255 }).notNull().unique(),
  code: varchar("code", { length: 10 }).notNull(),

  // Attempt tracking
  attemptCount: integer("attempt_count").default(0).notNull(),
  maxAttempts: integer("max_attempts").default(3).notNull(),

  // Expiration
  expiresAt: timestamp("expires_at").notNull(),
  verifiedAt: timestamp("verified_at"),

  // Metadata
  ipAddress: varchar("ip_address", { length: 45 }),
  userAgent: text("user_agent"),

  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// SMS logs table for tracking SMS sending
export const smsLogs = pgTable("sms_logs", {
  id: uuid("id").defaultRandom().primaryKey(),
  phone: varchar("phone", { length: 50 }).notNull(),
  message: text("message").notNull(),

  // Provider details
  provider: varchar("provider", { length: 50 }).notNull(),
  providerId: varchar("provider_id", { length: 255 }),

  // Status tracking
  status: varchar("status", { length: 50 }).notNull(), // sent, delivered, failed
  statusMessage: text("status_message"),

  // Cost tracking
  cost: varchar("cost", { length: 50 }),

  // Timestamps
  sentAt: timestamp("sent_at").defaultNow().notNull(),
  deliveredAt: timestamp("delivered_at"),
  failedAt: timestamp("failed_at"),
});

// Email logs table for tracking email sending
export const emailLogs = pgTable("email_logs", {
  id: uuid("id").defaultRandom().primaryKey(),
  email: varchar("email", { length: 255 }).notNull(),
  subject: varchar("subject", { length: 255 }).notNull(),

  // Template information
  templateName: varchar("template_name", { length: 100 }),

  // Status tracking
  status: varchar("status", { length: 50 }).notNull(), // sent, delivered, bounced, failed
  statusMessage: text("status_message"),

  // Provider details
  messageId: varchar("message_id", { length: 255 }),

  // Timestamps
  sentAt: timestamp("sent_at").defaultNow().notNull(),
  deliveredAt: timestamp("delivered_at"),
  bouncedAt: timestamp("bounced_at"),
  failedAt: timestamp("failed_at"),
});

// Rate limiting table for verification attempts
export const verificationRateLimit = pgTable("verification_rate_limit", {
  id: uuid("id").defaultRandom().primaryKey(),
  identifier: varchar("identifier", { length: 255 }).notNull(), // IP address, phone, or email
  type: verificationTypeEnum("type").notNull(),

  // Rate limiting
  attemptCount: integer("attempt_count").default(1).notNull(),
  windowStart: timestamp("window_start").defaultNow().notNull(),
  blockedUntil: timestamp("blocked_until"),

  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Zod schemas for validation
export const insertVerificationTokenSchema =
  createInsertSchema(verificationTokens);
export const selectVerificationTokenSchema =
  createSelectSchema(verificationTokens);
export const insertSmsLogSchema = createInsertSchema(smsLogs);
export const selectSmsLogSchema = createSelectSchema(smsLogs);
export const insertEmailLogSchema = createInsertSchema(emailLogs);
export const selectEmailLogSchema = createSelectSchema(emailLogs);
export const insertVerificationRateLimitSchema = createInsertSchema(
  verificationRateLimit,
);
export const selectVerificationRateLimitSchema = createSelectSchema(
  verificationRateLimit,
);

// Types
export type VerificationToken = typeof verificationTokens.$inferSelect;
export type NewVerificationToken = typeof verificationTokens.$inferInsert;
export type SmsLog = typeof smsLogs.$inferSelect;
export type NewSmsLog = typeof smsLogs.$inferInsert;
export type EmailLog = typeof emailLogs.$inferSelect;
export type NewEmailLog = typeof emailLogs.$inferInsert;
export type VerificationRateLimit = typeof verificationRateLimit.$inferSelect;
export type NewVerificationRateLimit =
  typeof verificationRateLimit.$inferInsert;
