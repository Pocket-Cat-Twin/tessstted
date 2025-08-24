import { z } from "zod";

// Order status enum
export enum OrderStatus {
  CREATED = "created",
  PROCESSING = "processing",
  CHECKING = "checking",
  PAID = "paid",
  SHIPPED = "shipped",
  DELIVERED = "delivered",
  CANCELLED = "cancelled",
}

// Order good schema
export const orderGoodSchema = z.object({
  id: z.string().uuid(),
  orderId: z.string().uuid(),
  name: z.string().min(1).max(500),
  link: z.string().url().optional(),
  screenshot: z.string().optional(),
  quantity: z.number().int().positive(),
  priceYuan: z.number().positive(),
  commission: z.number().min(0),
  totalYuan: z.number().positive(),
  totalRuble: z.number().positive(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// Order schema
export const orderSchema = z.object({
  id: z.string().uuid(),
  nomerok: z.string().min(1).max(50), // Order number
  userId: z.string().uuid(),

  // Customer info
  customerName: z.string().min(1).max(100),
  customerPhone: z.string().min(1).max(50),
  customerEmail: z.string().email().optional(),

  // Delivery info
  deliveryAddress: z.string().min(1).max(1000),
  deliveryMethod: z.string().min(1).max(100),
  deliveryCost: z.number().min(0).default(0),

  // Payment info
  paymentMethod: z.string().min(1).max(100),
  paymentScreenshot: z.string().optional(),

  // Order calculations
  subtotalYuan: z.number().positive(),
  totalCommission: z.number().min(0),
  currentKurs: z.number().positive(),
  discount: z.number().min(0).default(0),
  totalYuan: z.number().positive(),
  totalRuble: z.number().positive(),

  // Status and dates
  status: z.nativeEnum(OrderStatus).default(OrderStatus.CREATED),
  notes: z.string().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),

  // Relations
  goods: z.array(orderGoodSchema).optional(),
  statusHistory: z.array(z.object({
    id: z.string().uuid(),
    orderId: z.string().uuid(),
    fromStatus: z.nativeEnum(OrderStatus),
    toStatus: z.nativeEnum(OrderStatus),
    comment: z.string().optional(),
    createdAt: z.date(),
    updatedAt: z.date(),
  })).optional(),
});

// Order creation schema
export const orderCreateSchema = z.object({
  customerName: z.string().min(1).max(100),
  customerPhone: z.string().min(1).max(50),
  customerEmail: z.string().email().optional(),
  deliveryAddress: z.string().min(1).max(1000),
  deliveryMethod: z.string().min(1).max(100),
  paymentMethod: z.string().min(1).max(100),
  goods: z
    .array(
      z.object({
        name: z.string().min(1).max(500),
        link: z.string().url().optional(),
        quantity: z.number().int().positive(),
        priceYuan: z.number().positive(),
      }),
    )
    .min(1),
});

// Order update schema
export const orderUpdateSchema = z.object({
  customerName: z.string().min(1).max(100).optional(),
  customerPhone: z.string().min(1).max(50).optional(),
  customerEmail: z.string().email().optional(),
  deliveryAddress: z.string().min(1).max(1000).optional(),
  deliveryMethod: z.string().min(1).max(100).optional(),
  deliveryCost: z.number().min(0).optional(),
  paymentMethod: z.string().min(1).max(100).optional(),
  paymentScreenshot: z.string().optional(),
  discount: z.number().min(0).optional(),
  status: z.nativeEnum(OrderStatus).optional(),
  notes: z.string().optional(),
});

// Order good creation schema
export const orderGoodCreateSchema = z.object({
  name: z.string().min(1).max(500),
  link: z.string().url().optional(),
  quantity: z.number().int().positive(),
  priceYuan: z.number().positive(),
});

// Order good update schema
export const orderGoodUpdateSchema = z.object({
  name: z.string().min(1).max(500).optional(),
  link: z.string().url().optional(),
  quantity: z.number().int().positive().optional(),
  priceYuan: z.number().positive().optional(),
});

// Order lookup schema
export const orderLookupSchema = z.object({
  nomerok: z.string().min(1),
});

// Types
export type Order = z.infer<typeof orderSchema>;
export type OrderGood = z.infer<typeof orderGoodSchema>;
export type OrderCreate = z.infer<typeof orderCreateSchema>;
export type OrderUpdate = z.infer<typeof orderUpdateSchema>;
export type OrderGoodCreate = z.infer<typeof orderGoodCreateSchema>;
export type OrderGoodUpdate = z.infer<typeof orderGoodUpdateSchema>;
export type OrderLookup = z.infer<typeof orderLookupSchema>;
