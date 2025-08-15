import { z } from "zod";

// Subscription tier definitions according to technical specification
export const SUBSCRIPTION_TIERS = {
  free: {
    id: "free",
    name: "Обычный подписчик",
    price: 0,
    currency: "RUB",
    duration: null, // permanent
    description: "Редкие заказы, знакомство с сервисом",
    features: {
      maxStorageDays: 14,
      processingTimeHours: 120, // 5 рабочих дней
      supportResponseHours: 48,
      canParticipateInPromotions: false,
      canCombineOrders: false,
      hasPriorityProcessing: false,
      hasPersonalSupport: false,
      hasProductInspection: false,
    },
    limits: [
      "⏱️ Обработка заказов: до 5 рабочих дней",
      "📦 Хранение на складе: до 14 дней",
      "❌ Нет участия в акциях и скидках",
      "❌ Нет приоритета в очереди",
      "❌ Нет объединения посылок",
    ],
  },
  group: {
    id: "group",
    name: "Групповая подписка",
    price: 990,
    currency: "RUB",
    duration: 30, // days
    description: "Накопительные заказы, совместные покупки",
    features: {
      maxStorageDays: 90, // 3 месяца
      processingTimeHours: 72, // 2–4 рабочих дня
      supportResponseHours: 24,
      canParticipateInPromotions: true,
      canCombineOrders: true,
      hasPriorityProcessing: false,
      hasPersonalSupport: false,
      hasProductInspection: false,
    },
    benefits: [
      "📦 Хранение на складе: до 3 месяцев",
      "📮 Объединение заказов от разных продавцов",
      "⚡ Обработка: 2–4 рабочих дня",
      "🎯 Доступ к групповым акциям",
    ],
    limitations: ["❌ Нет приоритетной поддержки"],
  },
  elite: {
    id: "elite",
    name: "Элитный подписчик",
    price: 1990,
    currency: "RUB",
    duration: 30, // days
    description: "Активные клиенты, ценящие скорость и сервис",
    features: {
      maxStorageDays: -1, // без ограничений
      processingTimeHours: 24, // быстрая обработка
      supportResponseHours: 12, // быстрые ответы до 12 часов
      canParticipateInPromotions: true,
      canCombineOrders: true,
      hasPriorityProcessing: true,
      hasPersonalSupport: true,
      hasProductInspection: true,
    },
    benefits: [
      "⚡ Быстрые ответы: до 12 часов",
      "♾️ Хранение без ограничений",
      "🚀 Приоритетная отправка заказов",
      "🔐 Участие в закрытых акциях",
      "👤 Индивидуальная помощь и проверка товара",
      "🎧 Персональная поддержка",
    ],
  },
  vip_temp: {
    id: "vip_temp",
    name: "Разовый VIP-доступ",
    price: 890,
    currency: "RUB",
    duration: 7, // days
    description: "Срочные разовые заказы",
    features: {
      maxStorageDays: 30,
      processingTimeHours: 12, // экстренная обработка
      supportResponseHours: 6,
      canParticipateInPromotions: false,
      canCombineOrders: true,
      hasPriorityProcessing: true,
      hasPersonalSupport: true,
      hasProductInspection: true,
    },
    benefits: [
      "🚨 Экстренная обработка и приоритет",
      "📦 Хранение до 30 дней",
      "⭐ 1 заказ с максимальным вниманием",
      "⏰ Временное VIP-обслуживание",
    ],
  },
} as const;

export type SubscriptionTierId = keyof typeof SUBSCRIPTION_TIERS;

export interface SubscriptionFeatures {
  maxStorageDays: number; // -1 for unlimited
  processingTimeHours: number;
  supportResponseHours: number;
  canParticipateInPromotions: boolean;
  canCombineOrders: boolean;
  hasPriorityProcessing: boolean;
  hasPersonalSupport: boolean;
  hasProductInspection: boolean;
}

export interface UserSubscriptionInfo {
  userId: string;
  currentTier: SubscriptionTierId;
  isActive: boolean;
  expiresAt: Date | null;
  features: SubscriptionFeatures;
  daysRemaining: number | null;
  autoRenew: boolean;
}

/**
 * Get subscription tier information by ID
 */
export function getSubscriptionTier(tierId: SubscriptionTierId) {
  return SUBSCRIPTION_TIERS[tierId];
}

/**
 * Get all subscription tiers
 */
export function getAllSubscriptionTiers() {
  return Object.values(SUBSCRIPTION_TIERS);
}

/**
 * Check if a subscription is currently active
 */
export function isSubscriptionActive(expiresAt: Date | null): boolean {
  if (!expiresAt) return true; // Free tier never expires
  return new Date() < expiresAt;
}

/**
 * Calculate days remaining in subscription
 */
export function getDaysRemaining(expiresAt: Date | null): number | null {
  if (!expiresAt) return null; // Free tier has no expiration

  const now = new Date();
  const diffTime = expiresAt.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  return Math.max(0, diffDays);
}

/**
 * Calculate subscription end date
 */
export function calculateSubscriptionEndDate(
  tierId: SubscriptionTierId,
  startDate: Date = new Date(),
): Date | null {
  const tier = getSubscriptionTier(tierId);

  if (!tier.duration) return null; // Free tier never expires

  const endDate = new Date(startDate);
  endDate.setDate(endDate.getDate() + tier.duration);

  return endDate;
}

/**
 * Get user's effective subscription tier (handles expired subscriptions)
 */
export function getEffectiveTier(
  currentTier: SubscriptionTierId,
  expiresAt: Date | null,
): SubscriptionTierId {
  if (currentTier === "free") return "free";

  if (isSubscriptionActive(expiresAt)) {
    return currentTier;
  }

  // Subscription expired, fall back to free
  return "free";
}

/**
 * Check if user can upgrade to a specific tier
 */
export function canUpgradeTo(
  currentTier: SubscriptionTierId,
  targetTier: SubscriptionTierId,
): boolean {
  const tiers: SubscriptionTierId[] = ["free", "group", "elite", "vip_temp"];
  const currentIndex = tiers.indexOf(currentTier);
  const targetIndex = tiers.indexOf(targetTier);

  // VIP temp is a special case - can be purchased from any tier
  if (targetTier === "vip_temp") return true;

  return targetIndex > currentIndex;
}

/**
 * Calculate subscription price with any applicable discounts
 */
export function calculateSubscriptionPrice(
  tierId: SubscriptionTierId,
  discountPercent: number = 0,
): number {
  const tier = getSubscriptionTier(tierId);
  const basePrice = tier.price;

  if (discountPercent <= 0) return basePrice;

  const discountAmount = (basePrice * discountPercent) / 100;
  return Math.max(0, basePrice - discountAmount);
}

/**
 * Validate subscription tier ID
 */
export function isValidSubscriptionTier(
  tierId: string,
): tierId is SubscriptionTierId {
  return tierId in SUBSCRIPTION_TIERS;
}

// Zod schemas for validation
export const subscriptionTierIdSchema = z.enum([
  "free",
  "group",
  "elite",
  "vip_temp",
]);

export const subscriptionFeaturesSchema = z.object({
  maxStorageDays: z.number().int(),
  processingTimeHours: z.number().int().positive(),
  supportResponseHours: z.number().int().positive(),
  canParticipateInPromotions: z.boolean(),
  canCombineOrders: z.boolean(),
  hasPriorityProcessing: z.boolean(),
  hasPersonalSupport: z.boolean(),
  hasProductInspection: z.boolean(),
});

export const userSubscriptionInfoSchema = z.object({
  userId: z.string().uuid(),
  currentTier: subscriptionTierIdSchema,
  isActive: z.boolean(),
  expiresAt: z.date().nullable(),
  features: subscriptionFeaturesSchema,
  daysRemaining: z.number().int().nullable(),
  autoRenew: z.boolean(),
});
