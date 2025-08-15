/**
 * Currency conversion utilities
 */

/**
 * Convert Yuan to Rubles using current exchange rate
 */
export function convertYuanToRuble(yuan: number, kurs: number): number {
  return Math.round(yuan * kurs * 100) / 100;
}

/**
 * Convert Rubles to Yuan using current exchange rate
 */
export function convertRubleToYuan(ruble: number, kurs: number): number {
  return Math.round((ruble / kurs) * 100) / 100;
}

/**
 * Calculate commission based on amount and rate
 */
export function calculateCommission(amount: number, rate: number): number {
  return Math.round(amount * rate * 100) / 100;
}

/**
 * Calculate total with commission
 */
export function calculateTotalWithCommission(
  amount: number,
  commissionRate: number
): number {
  const commission = calculateCommission(amount, commissionRate);
  return Math.round((amount + commission) * 100) / 100;
}

/**
 * Calculate order totals
 */
export function calculateOrderTotals(
  goods: Array<{
    quantity: number;
    priceYuan: number;
  }>,
  kurs: number,
  commissionRate: number,
  deliveryCost: number = 0,
  discount: number = 0
): {
  subtotalYuan: number;
  totalCommission: number;
  totalYuan: number;
  totalRuble: number;
  finalTotal: number;
} {
  // Calculate subtotal in Yuan
  const subtotalYuan = goods.reduce(
    (sum, good) => sum + good.quantity * good.priceYuan,
    0
  );
  
  // Calculate total commission
  const totalCommission = calculateCommission(subtotalYuan, commissionRate);
  
  // Calculate total in Yuan (with commission)
  const totalYuan = subtotalYuan + totalCommission;
  
  // Convert to Rubles
  const totalRuble = convertYuanToRuble(totalYuan, kurs);
  
  // Calculate final total (with delivery and discount)
  const finalTotal = Math.max(0, totalRuble + deliveryCost - discount);
  
  return {
    subtotalYuan: Math.round(subtotalYuan * 100) / 100,
    totalCommission: Math.round(totalCommission * 100) / 100,
    totalYuan: Math.round(totalYuan * 100) / 100,
    totalRuble: Math.round(totalRuble * 100) / 100,
    finalTotal: Math.round(finalTotal * 100) / 100,
  };
}

/**
 * Format currency amount
 */
export function formatCurrency(
  amount: number,
  currency: 'RUB' | 'CNY' = 'RUB',
  locale: string = 'ru-RU'
): string {
  const currencySymbols = {
    RUB: '₽',
    CNY: '¥',
  };
  
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
    .format(amount)
    .replace(currency, currencySymbols[currency]);
}

/**
 * Parse currency string to number
 */
export function parseCurrency(currencyString: string): number {
  const cleaned = currencyString.replace(/[^\d.,]/g, '');
  const normalized = cleaned.replace(',', '.');
  return parseFloat(normalized) || 0;
}

/**
 * Get current exchange rate from external API
 * (This would be implemented in the API layer)
 */
export async function fetchCurrentKurs(): Promise<number> {
  // This is a placeholder - actual implementation would be in the API
  // For now, return a default value
  return 13.5; // Default CNY to RUB rate
}

/**
 * Validate currency amount
 */
export function isValidCurrencyAmount(amount: number): boolean {
  return Number.isFinite(amount) && amount >= 0 && amount <= 999999999;
}

/**
 * Round currency amount to appropriate precision
 */
export function roundCurrency(amount: number, precision: number = 2): number {
  const factor = Math.pow(10, precision);
  return Math.round(amount * factor) / factor;
}