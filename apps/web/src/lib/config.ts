// Централизованная конфигурация API endpoints
import { env } from "$env/dynamic/public";

/**
 * Конфигурация API endpoints с автоматической валидацией и fallback
 */
export const API_CONFIG = {
  /**
   * Определение базового URL API с защитой от ошибок конфигурации
   */
  BASE_URL: (() => {
    const envUrl = env.PUBLIC_API_URL;
    
    // Debug информация для диагностики
    console.log("🔍 API Config Debug:");
    console.log("  Raw PUBLIC_API_URL:", envUrl);
    console.log("  Environment keys:", Object.keys(env).filter(key => key.startsWith('PUBLIC')));
    
    if (envUrl) {
      // Убираем trailing slashes
      const cleanUrl = envUrl.replace(/\/+$/, '');
      
      // Гарантируем что URL заканчивается на /api/v1
      if (cleanUrl.endsWith('/api/v1')) {
        console.log("✅ Using configured API URL:", cleanUrl);
        return cleanUrl;
      } else {
        const correctedUrl = `${cleanUrl}/api/v1`;
        console.log("⚠️  Correcting API URL from", cleanUrl, "to", correctedUrl);
        return correctedUrl;
      }
    }
    
    // Fallback значение с предупреждением
    const fallbackUrl = "http://localhost:3001/api/v1";
    console.warn("⚠️  PUBLIC_API_URL not configured, using fallback:", fallbackUrl);
    console.warn("   Check your .env files for PUBLIC_API_URL setting");
    
    return fallbackUrl;
  })(),

  /**
   * Централизованные endpoint пути
   */
  ENDPOINTS: {
    // Health check (без /api/v1 префикса)
    HEALTH: "/health",
    
    // Authentication endpoints
    AUTH: {
      LOGIN: "/auth/login",
      REGISTER: "/auth/register",
      ME: "/auth/me",
      LOGOUT: "/auth/logout",
      REFRESH: "/auth/refresh",
      // Verification endpoints removed - no verification required
      // VERIFY_EMAIL: "/auth/verify-email",
      // VERIFY_PHONE: "/auth/verify-phone", 
      // RESEND_PHONE_VERIFICATION: "/auth/resend-phone-verification",
      FORGOT_PASSWORD: "/auth/forgot-password",
      RESET_PASSWORD: "/auth/reset-password",
    },

    // Configuration endpoints
    CONFIG: {
      BASE: "/config",
      KURS: "/config/kurs",
      FAQ: "/config/faq",
      SETTINGS: "/config/settings",
    },

    // Order management endpoints
    ORDERS: {
      BASE: "/orders",
      BY_ID: (id: string) => `/orders/${id}`,
      BY_NOMEROK: (nomerok: string) => `/orders/${nomerok}`,
      STATUS: (id: string) => `/orders/${id}/status`,
    },

    // Admin endpoints
    ADMIN: {
      ORDERS: "/admin/orders",
      ORDER_STATUS: (id: string) => `/admin/orders/${id}/status`,
      STATS: "/admin/stats",
      USERS: "/admin/users",
    },

    // Customer management
    CUSTOMERS: {
      BASE: "/customers",
      BY_ID: (id: string) => `/customers/${id}`,
      ADDRESSES: (id: string) => `/customers/${id}/addresses`,
    },

    // Stories/Blog endpoints
    STORIES: {
      BASE: "/stories",
      BY_LINK: (link: string) => `/stories/${link}`,
    },

    // Profile endpoints
    PROFILE: {
      BASE: "/profile",
      ADDRESSES: "/profile/addresses",
      ADDRESS_BY_ID: (id: string) => `/profile/addresses/${id}`,
      SUBSCRIPTION: "/profile/subscription",
      SUBSCRIPTION_HISTORY: "/profile/subscription/history",
    },

    // Subscription endpoints
    SUBSCRIPTIONS: {
      TIERS: "/subscriptions/tiers",
      STATUS: "/subscriptions/status",
      PURCHASE: "/subscriptions/purchase",
    },

    // File upload endpoints
    UPLOADS: {
      AVATAR: "/uploads/avatar",
      DOCUMENTS: "/uploads/documents",
      IMAGES: "/uploads/images",
    }
  },

  /**
   * Конфигурация запросов
   */
  REQUEST_CONFIG: {
    DEFAULT_TIMEOUT: 10000, // 10 секунд
    DEFAULT_RETRIES: 2,
    RETRY_DELAY_BASE: 500, // Базовая задержка для exponential backoff
    MAX_RETRY_DELAY: 5000, // Максимальная задержка
  },

  /**
   * Проверка доступности API
   */
  async validateConnection(): Promise<boolean> {
    try {
      const healthUrl = this.BASE_URL.replace('/api/v1', '') + this.ENDPOINTS.HEALTH;
      console.log("🔍 Validating API connection:", healthUrl);
      
      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: AbortSignal.timeout(this.REQUEST_CONFIG.DEFAULT_TIMEOUT)
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log("✅ API connection validated:", data);
        return true;
      } else {
        console.error("❌ API health check failed:", response.status, response.statusText);
        return false;
      }
    } catch (error) {
      console.error("❌ API connection validation failed:", error);
      return false;
    }
  },

  /**
   * Создание полного URL для endpoint
   */
  buildUrl(endpoint: string): string {
    return `${this.BASE_URL}${endpoint}`;
  },

  /**
   * Создание URL для health check (без /api/v1)
   */
  buildHealthUrl(): string {
    return this.BASE_URL.replace('/api/v1', '') + this.ENDPOINTS.HEALTH;
  }
};

/**
 * Типы для TypeScript
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  pagination?: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  retries?: number;
  timeout?: number;
  signal?: AbortSignal;
}

// Экспорт для обратной совместимости
export const API_BASE_URL = API_CONFIG.BASE_URL;
export const API_ENDPOINTS = API_CONFIG.ENDPOINTS;