// Shared utilities
export const generateId = (): string => {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
};

export const formatDate = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
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
  subtotalYuan: number;
  commission: number;
  totalCommission: number;
  total: number;
  totalYuan: number;
  totalRuble: number;
  commissionRate: number;
}

export const calculateOrderTotals = (
  goods: any[],
  exchangeRate: number,
  commissionRateOverride?: number
): OrderTotals => {
  // Calculate subtotal from goods
  const subtotalYuan = goods.reduce((sum, item) => sum + (item.quantity * item.priceYuan || 0), 0);
  
  // Use override commission rate or default
  const commissionRate = commissionRateOverride || 0.10; // Default 10%
  
  const totalCommission = subtotalYuan * commissionRate;
  const totalYuan = subtotalYuan + totalCommission;
  const totalRuble = totalYuan * exchangeRate;
  
  return {
    subtotal: subtotalYuan,
    subtotalYuan,
    commission: totalCommission,
    totalCommission,
    total: totalYuan,
    totalYuan,
    totalRuble,
    commissionRate,
  };
};
