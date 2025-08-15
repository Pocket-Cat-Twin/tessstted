import { pgTable, uuid, varchar, text, timestamp, boolean, integer } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';
import { stories } from './stories';

// Blog categories table
export const blogCategories = pgTable('blog_categories', {
  id: uuid('id').defaultRandom().primaryKey(),
  name: varchar('name', { length: 100 }).notNull(),
  slug: varchar('slug', { length: 100 }).notNull().unique(),
  description: text('description'),
  color: varchar('color', { length: 7 }).default('#3B82F6').notNull(), // hex color
  
  // SEO fields
  metaTitle: varchar('meta_title', { length: 255 }),
  metaDescription: varchar('meta_description', { length: 500 }),
  
  // Display settings
  order: integer('order').default(0).notNull(),
  isActive: boolean('is_active').default(true).notNull(),
  showOnHomepage: boolean('show_on_homepage').default(true).notNull(),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Junction table for many-to-many relationship between stories and categories
export const storyCategoryRelations = pgTable('story_category_relations', {
  id: uuid('id').defaultRandom().primaryKey(),
  storyId: uuid('story_id').notNull().references(() => stories.id, { onDelete: 'cascade' }),
  categoryId: uuid('category_id').notNull().references(() => blogCategories.id, { onDelete: 'cascade' }),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Story tags table for more granular classification
export const storyTags = pgTable('story_tags', {
  id: uuid('id').defaultRandom().primaryKey(),
  name: varchar('name', { length: 50 }).notNull().unique(),
  slug: varchar('slug', { length: 50 }).notNull().unique(),
  color: varchar('color', { length: 7 }).default('#6B7280').notNull(),
  
  // Usage count for sorting/filtering
  usageCount: integer('usage_count').default(0).notNull(),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Junction table for many-to-many relationship between stories and tags
export const storyTagRelations = pgTable('story_tag_relations', {
  id: uuid('id').defaultRandom().primaryKey(),
  storyId: uuid('story_id').notNull().references(() => stories.id, { onDelete: 'cascade' }),
  tagId: uuid('tag_id').notNull().references(() => storyTags.id, { onDelete: 'cascade' }),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Zod schemas for validation
export const insertBlogCategorySchema = createInsertSchema(blogCategories);
export const selectBlogCategorySchema = createSelectSchema(blogCategories);
export const insertStoryCategoryRelationSchema = createInsertSchema(storyCategoryRelations);
export const selectStoryCategoryRelationSchema = createSelectSchema(storyCategoryRelations);
export const insertStoryTagSchema = createInsertSchema(storyTags);
export const selectStoryTagSchema = createSelectSchema(storyTags);
export const insertStoryTagRelationSchema = createInsertSchema(storyTagRelations);
export const selectStoryTagRelationSchema = createSelectSchema(storyTagRelations);

// Types
export type BlogCategory = typeof blogCategories.$inferSelect;
export type NewBlogCategory = typeof blogCategories.$inferInsert;
export type StoryCategoryRelation = typeof storyCategoryRelations.$inferSelect;
export type NewStoryCategoryRelation = typeof storyCategoryRelations.$inferInsert;
export type StoryTag = typeof storyTags.$inferSelect;
export type NewStoryTag = typeof storyTags.$inferInsert;
export type StoryTagRelation = typeof storyTagRelations.$inferSelect;
export type NewStoryTagRelation = typeof storyTagRelations.$inferInsert;