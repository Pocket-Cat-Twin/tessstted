// Shared utilities
export const generateId = (): string => {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
};

export const formatDate = (date: Date): string => {
  return date.toISOString();
};

// Currency formatting
export const formatCurrency = (amount: number, currency = 'RUB'): string => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

// Order calculations
export interface OrderTotals {
  subtotal: number;
  commission: number;
  total: number;
  commissionRate: number;
}

export const calculateOrderTotals = (
  totalPriceCny: number,
  tier: 'basic' | 'premium' | 'vip' | 'elite' | null = null
): OrderTotals => {
  // Commission rates by subscription tier
  let commissionRate = 0.10; // Default 10%
  
  if (tier) {
    switch (tier) {
      case 'basic':
        commissionRate = 0.08; // 8%
        break;
      case 'premium':
        commissionRate = 0.06; // 6%
        break;
      case 'vip':
        commissionRate = 0.04; // 4%
        break;
      case 'elite':
        commissionRate = 0.02; // 2%
        break;
    }
  }
  
  const commission = totalPriceCny * commissionRate;
  const total = totalPriceCny + commission;
  
  return {
    subtotal: totalPriceCny,
    commission,
    total,
    commissionRate,
  };
};
