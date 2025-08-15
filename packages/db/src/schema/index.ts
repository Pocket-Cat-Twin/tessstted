// Export all tables and schemas
export * from './users';
export * from './customers';
export * from './orders';
export * from './stories';
export * from './config';
export * from './subscriptions';
export * from './blog';
export * from './verification';
export * from './notifications';

// Export relations for Drizzle ORM
import { relations } from 'drizzle-orm';
import { users, userSessions } from './users';
import { customers, customerAddresses } from './customers';
import { orders, orderGoods, orderStatusHistory } from './orders';
import { stories } from './stories';
import { uploads, faqs, faqCategories } from './config';
import { userSubscriptions, subscriptionHistory } from './subscriptions';
import { blogCategories, storyCategoryRelations, storyTags, storyTagRelations } from './blog';
import { verificationTokens } from './verification';
import { notificationHistory, notificationPreferences, emailTemplates } from './notifications';

// User relations
export const usersRelations = relations(users, ({ many, one }) => ({
  sessions: many(userSessions),
  orders: many(orders),
  customers: many(customers),
  authoredStories: many(stories),
  uploads: many(uploads),
  orderStatusChanges: many(orderStatusHistory),
  subscriptions: many(userSubscriptions),
  subscriptionHistory: many(subscriptionHistory),
  verificationTokens: many(verificationTokens),
  notificationHistory: many(notificationHistory),
  notificationPreferences: one(notificationPreferences),
}));

export const userSessionsRelations = relations(userSessions, ({ one }) => ({
  user: one(users, {
    fields: [userSessions.userId],
    references: [users.id],
  }),
}));

// Customer relations
export const customersRelations = relations(customers, ({ many }) => ({
  addresses: many(customerAddresses),
  orders: many(orders),
}));

export const customerAddressesRelations = relations(customerAddresses, ({ one }) => ({
  customer: one(customers, {
    fields: [customerAddresses.customerId],
    references: [customers.id],
  }),
}));

// Order relations
export const ordersRelations = relations(orders, ({ many, one }) => ({
  user: one(users, {
    fields: [orders.userId],
    references: [users.id],
  }),
  customer: one(customers, {
    fields: [orders.customerId],
    references: [customers.id],
  }),
  goods: many(orderGoods),
  statusHistory: many(orderStatusHistory),
}));

export const orderGoodsRelations = relations(orderGoods, ({ one }) => ({
  order: one(orders, {
    fields: [orderGoods.orderId],
    references: [orders.id],
  }),
}));

export const orderStatusHistoryRelations = relations(orderStatusHistory, ({ one }) => ({
  order: one(orders, {
    fields: [orderStatusHistory.orderId],
    references: [orders.id],
  }),
  user: one(users, {
    fields: [orderStatusHistory.userId],
    references: [users.id],
  }),
}));

// Story relations
export const storiesRelations = relations(stories, ({ one, many }) => ({
  author: one(users, {
    fields: [stories.authorId],
    references: [users.id],
  }),
  categories: many(storyCategoryRelations),
  tags: many(storyTagRelations),
}));

// Upload relations
export const uploadsRelations = relations(uploads, ({ one }) => ({
  uploadedBy: one(users, {
    fields: [uploads.uploadedBy],
    references: [users.id],
  }),
}));

// Subscription relations
export const userSubscriptionsRelations = relations(userSubscriptions, ({ one, many }) => ({
  user: one(users, {
    fields: [userSubscriptions.userId],
    references: [users.id],
  }),
  history: many(subscriptionHistory),
}));

export const subscriptionHistoryRelations = relations(subscriptionHistory, ({ one }) => ({
  user: one(users, {
    fields: [subscriptionHistory.userId],
    references: [users.id],
  }),
  subscription: one(userSubscriptions, {
    fields: [subscriptionHistory.subscriptionId],
    references: [userSubscriptions.id],
  }),
}));

// Blog category relations
export const blogCategoriesRelations = relations(blogCategories, ({ many }) => ({
  stories: many(storyCategoryRelations),
}));

export const storyCategoryRelationsRelations = relations(storyCategoryRelations, ({ one }) => ({
  story: one(stories, {
    fields: [storyCategoryRelations.storyId],
    references: [stories.id],
  }),
  category: one(blogCategories, {
    fields: [storyCategoryRelations.categoryId],
    references: [blogCategories.id],
  }),
}));

// Story tag relations
export const storyTagsRelations = relations(storyTags, ({ many }) => ({
  stories: many(storyTagRelations),
}));

export const storyTagRelationsRelations = relations(storyTagRelations, ({ one }) => ({
  story: one(stories, {
    fields: [storyTagRelations.storyId],
    references: [stories.id],
  }),
  tag: one(storyTags, {
    fields: [storyTagRelations.tagId],
    references: [storyTags.id],
  }),
}));

// Verification token relations
export const verificationTokensRelations = relations(verificationTokens, ({ one }) => ({
  user: one(users, {
    fields: [verificationTokens.userId],
    references: [users.id],
  }),
}));

// Notification relations
export const notificationHistoryRelations = relations(notificationHistory, ({ one }) => ({
  user: one(users, {
    fields: [notificationHistory.userId],
    references: [users.id],
  }),
  subscription: one(userSubscriptions, {
    fields: [notificationHistory.subscriptionId],
    references: [userSubscriptions.id],
  }),
  order: one(orders, {
    fields: [notificationHistory.orderId],
    references: [orders.id],
  }),
}));

export const notificationPreferencesRelations = relations(notificationPreferences, ({ one }) => ({
  user: one(users, {
    fields: [notificationPreferences.userId],
    references: [users.id],
  }),
}));

// FAQ category relations
export const faqCategoriesRelations = relations(faqCategories, ({ many }) => ({
  faqs: many(faqs),
}));

export const faqsRelations = relations(faqs, ({ one }) => ({
  category: one(faqCategories, {
    fields: [faqs.categoryId],
    references: [faqCategories.id],
  }),
}));