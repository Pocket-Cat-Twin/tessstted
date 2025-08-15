import { pgTable, uuid, varchar, timestamp, numeric, integer, pgEnum, boolean } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';
import { users } from './users';

// User subscription tier enum
export const subscriptionTierEnum = pgEnum('subscription_tier', [
  'free',         // Обычный подписчик (БЕСПЛАТНО)
  'group',        // Групповая подписка (990₽/месяц) 
  'elite',        // Элитный подписчик (1990₽/месяц)
  'vip_temp'      // Разовый VIP-доступ (890₽ на 7 дней)
]);

// Subscription status enum
export const subscriptionStatusEnum = pgEnum('subscription_status', [
  'active',
  'expired', 
  'cancelled',
  'pending_payment'
]);

// User subscriptions table
export const userSubscriptions = pgTable('user_subscriptions', {
  id: uuid('id').defaultRandom().primaryKey(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  
  // Subscription details
  tier: subscriptionTierEnum('tier').notNull(),
  status: subscriptionStatusEnum('status').default('pending_payment').notNull(),
  
  // Pricing and billing
  price: numeric('price', { precision: 10, scale: 2 }).notNull(),
  currency: varchar('currency', { length: 3 }).default('RUB').notNull(),
  
  // Subscription period
  startDate: timestamp('start_date').notNull(),
  endDate: timestamp('end_date').notNull(),
  
  // Auto-renewal
  autoRenew: boolean('auto_renew').default(false).notNull(),
  
  // Payment reference
  paymentReference: varchar('payment_reference', { length: 255 }),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Subscription features table - defines what each tier includes
export const subscriptionFeatures = pgTable('subscription_features', {
  id: uuid('id').defaultRandom().primaryKey(),
  tier: subscriptionTierEnum('tier').notNull(),
  
  // Feature limits and permissions
  maxStorageDays: integer('max_storage_days').notNull(), // -1 for unlimited
  processingTimeHours: integer('processing_time_hours').notNull(), // Max processing time
  supportResponseHours: integer('support_response_hours').notNull(), // Max support response time
  canParticipateInPromotions: boolean('can_participate_in_promotions').default(false).notNull(),
  canCombineOrders: boolean('can_combine_orders').default(false).notNull(),
  hasPriorityProcessing: boolean('has_priority_processing').default(false).notNull(),
  hasPersonalSupport: boolean('has_personal_support').default(false).notNull(),
  hasProductInspection: boolean('has_product_inspection').default(false).notNull(),
  
  // Metadata
  description: varchar('description', { length: 500 }),
  isActive: boolean('is_active').default(true).notNull(),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// User subscription history for tracking changes
export const subscriptionHistory = pgTable('subscription_history', {
  id: uuid('id').defaultRandom().primaryKey(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  subscriptionId: uuid('subscription_id').references(() => userSubscriptions.id, { onDelete: 'set null' }),
  
  // Change details
  action: varchar('action', { length: 50 }).notNull(), // created, renewed, cancelled, expired, upgraded, downgraded
  fromTier: subscriptionTierEnum('from_tier'),
  toTier: subscriptionTierEnum('to_tier'),
  
  // Payment details
  amount: numeric('amount', { precision: 10, scale: 2 }),
  paymentMethod: varchar('payment_method', { length: 100 }),
  
  // Metadata
  notes: varchar('notes', { length: 500 }),
  
  // Timestamp
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Zod schemas for validation
export const insertUserSubscriptionSchema = createInsertSchema(userSubscriptions);
export const selectUserSubscriptionSchema = createSelectSchema(userSubscriptions);
export const insertSubscriptionFeatureSchema = createInsertSchema(subscriptionFeatures);
export const selectSubscriptionFeatureSchema = createSelectSchema(subscriptionFeatures);
export const insertSubscriptionHistorySchema = createInsertSchema(subscriptionHistory);
export const selectSubscriptionHistorySchema = createSelectSchema(subscriptionHistory);

// Types
export type UserSubscription = typeof userSubscriptions.$inferSelect;
export type NewUserSubscription = typeof userSubscriptions.$inferInsert;
export type SubscriptionFeature = typeof subscriptionFeatures.$inferSelect;
export type NewSubscriptionFeature = typeof subscriptionFeatures.$inferInsert;
export type SubscriptionHistory = typeof subscriptionHistory.$inferSelect;
export type NewSubscriptionHistory = typeof subscriptionHistory.$inferInsert;