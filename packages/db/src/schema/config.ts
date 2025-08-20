import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  integer,
  boolean,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";

// Config value type enum
export const configTypeEnum = pgEnum("config_type", [
  "string",
  "number",
  "boolean",
  "json",
]);

// Configuration table
export const config = pgTable("config", {
  id: uuid("id").defaultRandom().primaryKey(),
  key: varchar("key", { length: 100 }).notNull().unique(),
  value: text("value").notNull(),
  description: text("description"),
  type: configTypeEnum("type").default("string").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// FAQ Categories table
export const faqCategories = pgTable("faq_categories", {
  id: uuid("id").defaultRandom().primaryKey(),
  name: varchar("name", { length: 100 }).notNull(),
  slug: varchar("slug", { length: 100 }).notNull().unique(),
  description: text("description"),
  order: integer("order").default(0).notNull(),
  isActive: boolean("is_active").default(true).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// FAQ table
export const faqs = pgTable("faqs", {
  id: uuid("id").defaultRandom().primaryKey(),
  question: varchar("question", { length: 500 }).notNull(),
  answer: text("answer").notNull(),
  // categoryId field removed as faq_categories table doesn't exist in current DB
  order: integer("order").default(0).notNull(),
  isActive: boolean("is_active").default(true).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// File uploads table
export const uploads = pgTable("uploads", {
  id: uuid("id").defaultRandom().primaryKey(),
  originalName: varchar("original_name", { length: 255 }).notNull(),
  filename: varchar("filename", { length: 255 }).notNull(),
  mimetype: varchar("mimetype", { length: 100 }).notNull(),
  size: integer("size").notNull(),
  path: text("path").notNull(),
  url: text("url").notNull(),
  uploadedBy: uuid("uploaded_by"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Email templates table moved to notifications.ts for better organization
// This avoids duplicate exports and keeps email templates with notification logic

// Zod schemas for validation
export const insertConfigSchema = createInsertSchema(config);
export const selectConfigSchema = createSelectSchema(config);
export const insertFaqCategorySchema = createInsertSchema(faqCategories);
export const selectFaqCategorySchema = createSelectSchema(faqCategories);
export const insertFaqSchema = createInsertSchema(faqs);
export const selectFaqSchema = createSelectSchema(faqs);
export const insertUploadSchema = createInsertSchema(uploads);
export const selectUploadSchema = createSelectSchema(uploads);
// Email template schemas moved to notifications.ts

// Types
export type Config = typeof config.$inferSelect;
export type NewConfig = typeof config.$inferInsert;
export type FaqCategory = typeof faqCategories.$inferSelect;
export type NewFaqCategory = typeof faqCategories.$inferInsert;
export type FAQ = typeof faqs.$inferSelect;
export type NewFAQ = typeof faqs.$inferInsert;
export type Upload = typeof uploads.$inferSelect;
export type NewUpload = typeof uploads.$inferInsert;
// Email template types moved to notifications.ts
