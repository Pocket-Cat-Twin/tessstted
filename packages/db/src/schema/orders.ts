import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  numeric,
  integer,
  pgEnum,
  boolean,
} from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "./users";
import { customers } from "./customers";

// Order status enum
export const orderStatusEnum = pgEnum("order_status", [
  "created",
  "processing",
  "checking",
  "paid",
  "shipped",
  "delivered",
  "cancelled",
]);

// Orders table
export const orders = pgTable("orders", {
  id: uuid("id").defaultRandom().primaryKey(),
  nomerok: varchar("nomerok", { length: 50 }).notNull().unique(),
  userId: uuid("user_id").references(() => users.id, { onDelete: "set null" }),
  customerId: uuid("customer_id").references(() => customers.id, {
    onDelete: "set null",
  }),

  // Customer information
  customerName: varchar("customer_name", { length: 100 }).notNull(),
  customerPhone: varchar("customer_phone", { length: 50 }).notNull(),
  customerEmail: varchar("customer_email", { length: 255 }),

  // Delivery information
  deliveryAddress: text("delivery_address").notNull(),
  deliveryMethod: varchar("delivery_method", { length: 100 }).notNull(),
  deliveryCost: numeric("delivery_cost", { precision: 10, scale: 2 })
    .default("0")
    .notNull(),

  // Payment information
  paymentMethod: varchar("payment_method", { length: 100 }).notNull(),
  paymentScreenshot: text("payment_screenshot"),

  // Order calculations
  subtotalYuan: numeric("subtotal_yuan", { precision: 10, scale: 2 }).notNull(),
  totalCommission: numeric("total_commission", {
    precision: 10,
    scale: 2,
  }).notNull(),
  currentKurs: numeric("current_kurs", { precision: 8, scale: 4 }).notNull(),
  discount: numeric("discount", { precision: 10, scale: 2 })
    .default("0")
    .notNull(),
  totalYuan: numeric("total_yuan", { precision: 10, scale: 2 }).notNull(),
  totalRuble: numeric("total_ruble", { precision: 10, scale: 2 }).notNull(),

  // Status and metadata
  status: orderStatusEnum("status").default("created").notNull(),
  notes: text("notes"),
  isArchived: boolean("is_archived").default(false).notNull(),

  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Order goods table
export const orderGoods = pgTable("order_goods", {
  id: uuid("id").defaultRandom().primaryKey(),
  orderId: uuid("order_id")
    .notNull()
    .references(() => orders.id, { onDelete: "cascade" }),

  // Product information
  name: varchar("name", { length: 500 }).notNull(),
  link: text("link"),
  screenshot: text("screenshot"),

  // Pricing and quantities
  quantity: integer("quantity").notNull(),
  priceYuan: numeric("price_yuan", { precision: 10, scale: 2 }).notNull(),
  commission: numeric("commission", { precision: 10, scale: 2 }).notNull(),
  totalYuan: numeric("total_yuan", { precision: 10, scale: 2 }).notNull(),
  totalRuble: numeric("total_ruble", { precision: 10, scale: 2 }).notNull(),

  // Timestamps
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Order status history for tracking changes
export const orderStatusHistory = pgTable("order_status_history", {
  id: uuid("id").defaultRandom().primaryKey(),
  orderId: uuid("order_id")
    .notNull()
    .references(() => orders.id, { onDelete: "cascade" }),
  userId: uuid("user_id").references(() => users.id, { onDelete: "set null" }),

  fromStatus: orderStatusEnum("from_status"),
  toStatus: orderStatusEnum("to_status").notNull(),
  comment: text("comment"),

  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Zod schemas for validation
export const insertOrderSchema = createInsertSchema(orders);
export const selectOrderSchema = createSelectSchema(orders);
export const insertOrderGoodSchema = createInsertSchema(orderGoods);
export const selectOrderGoodSchema = createSelectSchema(orderGoods);
export const insertOrderStatusHistorySchema =
  createInsertSchema(orderStatusHistory);
export const selectOrderStatusHistorySchema =
  createSelectSchema(orderStatusHistory);

// Types
export type Order = typeof orders.$inferSelect;
export type NewOrder = typeof orders.$inferInsert;
export type OrderGood = typeof orderGoods.$inferSelect;
export type NewOrderGood = typeof orderGoods.$inferInsert;
export type OrderStatusHistory = typeof orderStatusHistory.$inferSelect;
export type NewOrderStatusHistory = typeof orderStatusHistory.$inferInsert;
