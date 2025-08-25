import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  pgEnum,
  json,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "./users";

// Story status enum
export const storyStatusEnum = pgEnum("story_status", [
  "draft",
  "published",
  "archived",
]);

// Stories table
export const stories = pgTable("stories", {
  id: uuid("id").defaultRandom().primaryKey(),
  title: varchar("title", { length: 200 }).notNull(),
  link: varchar("link", { length: 100 }).notNull().unique(),
  content: text("content").notNull(),
  excerpt: varchar("excerpt", { length: 500 }),

  // Images
  thumbnail: text("thumbnail"),
  images: json("images").$type<string[]>().default([]),

  // Status and publishing
  status: storyStatusEnum("status").default("draft").notNull(),
  publishedAt: timestamp("published_at"),

  // Author relationship
  authorId: uuid("author_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),

  // SEO fields
  metaTitle: varchar("meta_title", { length: 255 }),
  metaDescription: varchar("meta_description", { length: 500 }),

  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Zod schemas for validation
export const insertStorySchema = createInsertSchema(stories);
export const selectStorySchema = createSelectSchema(stories);

// Types
export type Story = typeof stories.$inferSelect;
export type NewStory = typeof stories.$inferInsert;
