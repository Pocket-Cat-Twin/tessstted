import { z } from "zod";

// Config schema
export const configSchema = z.object({
  id: z.string().uuid(),
  key: z.string().min(1).max(100),
  value: z.string(),
  description: z.string().optional(),
  type: z.enum(["string", "number", "boolean", "json"]).default("string"),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// Config update schema
export const configUpdateSchema = z.object({
  value: z.string(),
  description: z.string().optional(),
});

// Specific config schemas
export const currencyKursSchema = z.object({
  currentKurs: z.number().positive(),
});

export const commissionRateSchema = z.object({
  defaultCommissionRate: z.number().min(0).max(1),
});

export const siteSettingsSchema = z.object({
  siteName: z.string().min(1).max(100),
  siteDescription: z.string().max(500),
  contactEmail: z.string().email(),
  contactPhone: z.string(),
  telegramLink: z.string().url(),
  vkLink: z.string().url(),
});

// FAQ schema
export const faqSchema = z.object({
  id: z.string().uuid(),
  question: z.string().min(1).max(500),
  answer: z.string().min(1),
  order: z.number().int().min(0).default(0),
  isActive: z.boolean().default(true),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export const faqCreateSchema = z.object({
  question: z.string().min(1).max(500),
  answer: z.string().min(1),
  order: z.number().int().min(0).default(0),
  isActive: z.boolean().default(true),
});

export const faqUpdateSchema = z.object({
  question: z.string().min(1).max(500).optional(),
  answer: z.string().min(1).optional(),
  order: z.number().int().min(0).optional(),
  isActive: z.boolean().optional(),
});

// Types
export type Config = z.infer<typeof configSchema>;
export type ConfigUpdate = z.infer<typeof configUpdateSchema>;
export type CurrencyKurs = z.infer<typeof currencyKursSchema>;
export type CommissionRate = z.infer<typeof commissionRateSchema>;
export type SiteSettings = z.infer<typeof siteSettingsSchema>;
export type FAQ = z.infer<typeof faqSchema>;
export type FAQCreate = z.infer<typeof faqCreateSchema>;
export type FAQUpdate = z.infer<typeof faqUpdateSchema>;
