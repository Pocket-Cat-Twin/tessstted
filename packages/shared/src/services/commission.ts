import { z } from "zod";

// Commission calculation service according to the technical specification

export interface CommissionCalculationInput {
  priceYuan: number;
  exchangeRate: number;
  quantity?: number;
}

export interface CommissionCalculationResult {
  originalPriceYuan: number;
  originalPriceRuble: number;
  commissionYuan: number;
  commissionRuble: number;
  finalPriceRuble: number;
  commissionRate: number;
  calculationType: "percentage_low" | "percentage_standard" | "flat_fee_high";
}

/**
 * Calculate commission according to the technical specification:
 *
 * 1. For items 100-1000 CNY: Price CNY × Exchange Rate × 1.15 = Final Price RUB
 * 2. For items <100 CNY: Price CNY × Exchange Rate × 1.10 = Final Price RUB
 * 3. For items >1000 CNY: (Price CNY + 15) × Exchange Rate = Final Price RUB
 *
 * Commission is applied ONCE per item, regardless of quantity
 */
export function calculateCommission(
  input: CommissionCalculationInput,
): CommissionCalculationResult {
  const { priceYuan, exchangeRate, quantity = 1 } = input;

  // Validate input
  if (priceYuan <= 0 || exchangeRate <= 0) {
    throw new Error("Price and exchange rate must be positive numbers");
  }

  const originalPriceRuble = priceYuan * exchangeRate;
  let finalPriceRuble: number;
  let commissionYuan: number;
  let commissionRate: number;
  let calculationType: CommissionCalculationResult["calculationType"];

  if (priceYuan < 100) {
    // For items <100 CNY: 10% markup
    finalPriceRuble = originalPriceRuble * 1.1;
    commissionRate = 0.1;
    commissionYuan = priceYuan * 0.1;
    calculationType = "percentage_low";
  } else if (priceYuan >= 100 && priceYuan <= 1000) {
    // For items 100-1000 CNY: 15% markup
    finalPriceRuble = originalPriceRuble * 1.15;
    commissionRate = 0.15;
    commissionYuan = priceYuan * 0.15;
    calculationType = "percentage_standard";
  } else {
    // For items >1000 CNY: +15 CNY flat fee
    commissionYuan = 15;
    finalPriceRuble = (priceYuan + commissionYuan) * exchangeRate;
    commissionRate = commissionYuan / priceYuan; // Calculate equivalent rate for display
    calculationType = "flat_fee_high";
  }

  const commissionRuble = commissionYuan * exchangeRate;

  return {
    originalPriceYuan: priceYuan,
    originalPriceRuble: Number(originalPriceRuble.toFixed(2)),
    commissionYuan: Number(commissionYuan.toFixed(2)),
    commissionRuble: Number(commissionRuble.toFixed(2)),
    finalPriceRuble: Number(finalPriceRuble.toFixed(2)),
    commissionRate: Number(commissionRate.toFixed(4)),
    calculationType,
  };
}

/**
 * Calculate total commission for multiple items
 */
export function calculateTotalCommission(
  items: Array<{ priceYuan: number; quantity: number }>,
  exchangeRate: number,
): {
  items: Array<
    CommissionCalculationResult & { quantity: number; totalFinalPrice: number }
  >;
  totals: {
    originalPriceYuan: number;
    originalPriceRuble: number;
    totalCommissionYuan: number;
    totalCommissionRuble: number;
    totalFinalPriceRuble: number;
  };
} {
  let totalOriginalYuan = 0;
  let totalOriginalRuble = 0;
  let totalCommissionYuan = 0;
  let totalCommissionRuble = 0;
  let totalFinalPriceRuble = 0;

  const calculatedItems = items.map((item) => {
    // Commission is applied once per item, regardless of quantity
    const commission = calculateCommission({
      priceYuan: item.priceYuan,
      exchangeRate,
    });

    const totalFinalPrice = commission.finalPriceRuble * item.quantity;

    // Accumulate totals
    totalOriginalYuan += item.priceYuan * item.quantity;
    totalOriginalRuble += commission.originalPriceRuble * item.quantity;
    totalCommissionYuan += commission.commissionYuan * item.quantity;
    totalCommissionRuble += commission.commissionRuble * item.quantity;
    totalFinalPriceRuble += totalFinalPrice;

    return {
      ...commission,
      quantity: item.quantity,
      totalFinalPrice: Number(totalFinalPrice.toFixed(2)),
    };
  });

  return {
    items: calculatedItems,
    totals: {
      originalPriceYuan: Number(totalOriginalYuan.toFixed(2)),
      originalPriceRuble: Number(totalOriginalRuble.toFixed(2)),
      totalCommissionYuan: Number(totalCommissionYuan.toFixed(2)),
      totalCommissionRuble: Number(totalCommissionRuble.toFixed(2)),
      totalFinalPriceRuble: Number(totalFinalPriceRuble.toFixed(2)),
    },
  };
}

// Zod schemas for validation
export const commissionCalculationInputSchema = z.object({
  priceYuan: z.number().positive(),
  exchangeRate: z.number().positive(),
  quantity: z.number().int().positive().optional(),
});

export const commissionCalculationResultSchema = z.object({
  originalPriceYuan: z.number(),
  originalPriceRuble: z.number(),
  commissionYuan: z.number(),
  commissionRuble: z.number(),
  finalPriceRuble: z.number(),
  commissionRate: z.number(),
  calculationType: z.enum([
    "percentage_low",
    "percentage_standard",
    "flat_fee_high",
  ]),
});
