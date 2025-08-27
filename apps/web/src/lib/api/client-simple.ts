// Enterprise-grade API client with robust error handling and validation
import { API_CONFIG, type ApiResponse, type RequestOptions } from "../config";

// Инициализация API клиента с валидацией
console.log("🚀 Initializing Enterprise API Client");
console.log("📊 Configuration:", {
  baseUrl: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.REQUEST_CONFIG.DEFAULT_TIMEOUT,
  retries: API_CONFIG.REQUEST_CONFIG.DEFAULT_RETRIES,
});

// Автоматическая валидация подключения при инициализации
API_CONFIG.validateConnection().then(isConnected => {
  if (isConnected) {
    console.log("✅ API connection validated successfully");
  } else {
    console.error("❌ API connection validation failed - check server status");
  }
}).catch(error => {
  console.error("🚨 API validation error:", error);
});

/**
 * Utility функция для создания задержки
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Utility функция для exponential backoff
 */
function calculateRetryDelay(attempt: number): number {
  const baseDelay = API_CONFIG.REQUEST_CONFIG.RETRY_DELAY_BASE;
  const maxDelay = API_CONFIG.REQUEST_CONFIG.MAX_RETRY_DELAY;
  const calculatedDelay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
  return calculatedDelay;
}

/**
 * Utility функция для проверки статуса сети
 */
function isNetworkError(error: any): boolean {
  return error instanceof TypeError && error.message.includes('fetch');
}

/**
 * Utility функция для проверки тайм-аута
 */
function isTimeoutError(error: any): boolean {
  return error.name === 'AbortError' || error.message.includes('timeout');
}

/**
 * Enterprise API Client с расширенными возможностями:
 * - Автоматические retry с exponential backoff
 * - Детальное логирование запросов и ошибок
 * - Валидация ответов сервера
 * - Управление тайм-аутами
 * - Централизованная обработка ошибок
 */
class ApiClient {
  private baseUrl: string;
  private defaultTimeout: number;
  private defaultRetries: number;
  private requestCounter: number = 0;

  constructor(baseUrl: string = API_CONFIG.BASE_URL) {
    this.baseUrl = baseUrl;
    this.defaultTimeout = API_CONFIG.REQUEST_CONFIG.DEFAULT_TIMEOUT;
    this.defaultRetries = API_CONFIG.REQUEST_CONFIG.DEFAULT_RETRIES;
    
    console.log("🔧 API Client initialized:", {
      baseUrl: this.baseUrl,
      timeout: this.defaultTimeout,
      retries: this.defaultRetries
    });
  }

  /**
   * Основной метод для выполнения HTTP запросов с полной защитой от ошибок
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestOptions = {},
  ): Promise<ApiResponse<T>> {
    const requestId = ++this.requestCounter;
    const maxRetries = options.retries ?? this.defaultRetries;
    const timeout = options.timeout ?? this.defaultTimeout;
    const url = `${this.baseUrl}${endpoint}`;
    
    console.log(`🌐 [${requestId}] Starting API request:`, {
      url,
      method: options.method || 'GET',
      maxRetries,
      timeout
    });

    let lastError: any;
    let lastResponse: Response | null = null;
    
    // Основной цикл с retry логикой
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const isRetry = attempt > 0;
      
      try {
        if (isRetry) {
          const retryDelay = calculateRetryDelay(attempt - 1);
          console.log(`⏳ [${requestId}] Retry ${attempt}/${maxRetries} after ${retryDelay}ms delay`);
          await delay(retryDelay);
        }
        
        // Создание AbortController для тайм-аута
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
          controller.abort();
        }, timeout);
        
        console.log(`🔄 [${requestId}] Making request (attempt ${attempt + 1}/${maxRetries + 1}): ${url}`);
        
        // Выполнение HTTP запроса
        const response = await fetch(url, {
          method: options.method || 'GET',
          headers: {
            "Content-Type": "application/json",
            ...options.headers,
          },
          body: options.body,
          signal: options.signal || controller.signal,
          ...options,
        });
        
        clearTimeout(timeoutId);
        lastResponse = response;
        
        console.log(`📊 [${requestId}] Response received:`, {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries())
        });

        // Проверка статуса ответа
        if (!response.ok) {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          let errorData: any = null;
          
          try {
            const contentType = response.headers.get('content-type');
            if (contentType?.includes('application/json')) {
              errorData = await response.json();
              console.log(`📄 [${requestId}] Error response data:`, errorData);
            } else {
              const textData = await response.text();
              console.log(`📄 [${requestId}] Error response text:`, textData);
              errorMessage += ` - ${textData}`;
            }
          } catch (parseError) {
            console.warn(`⚠️  [${requestId}] Failed to parse error response:`, parseError);
          }

          // Определяем, стоит ли делать retry для данной ошибки
          const shouldRetry = this.shouldRetryForStatus(response.status) && attempt < maxRetries;
          
          if (shouldRetry) {
            console.log(`🔄 [${requestId}] HTTP ${response.status} - will retry`);
            lastError = new Error(errorMessage);
            continue;
          } else {
            console.error(`❌ [${requestId}] HTTP ${response.status} - no retry`);
            
            return {
              success: false,
              error: `HTTP_${response.status}`,
              message: errorData?.message || errorData?.error || errorMessage,
              data: errorData
            };
          }
        }

        // Успешный ответ - парсим JSON
        let responseData: any;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType?.includes('application/json')) {
            responseData = await response.json();
          } else {
            const textData = await response.text();
            console.warn(`⚠️  [${requestId}] Non-JSON response:`, textData);
            responseData = { data: textData, success: true };
          }
        } catch (parseError) {
          console.error(`❌ [${requestId}] Failed to parse JSON response:`, parseError);
          return {
            success: false,
            error: "JSON_PARSE_ERROR",
            message: "Server returned invalid JSON",
          };
        }

        console.log(`✅ [${requestId}] Request successful:`, {
          success: responseData.success,
          dataKeys: responseData.data ? Object.keys(responseData.data) : 'no data',
        });
        
        return responseData;
        
      } catch (error: any) {
        lastError = error;
        
        console.error(`❌ [${requestId}] Request failed (attempt ${attempt + 1}):`, {
          error: error.message,
          name: error.name,
          stack: error.stack
        });

        // Определяем, стоит ли делать retry для данной ошибки
        const shouldRetry = this.shouldRetryForError(error) && attempt < maxRetries;
        
        if (!shouldRetry) {
          break;
        }
      }
    }

    // Все попытки исчерпаны
    console.error(`🚨 [${requestId}] All ${maxRetries + 1} attempts failed. Last error:`, lastError);
    
    return {
      success: false,
      error: this.categorizeError(lastError),
      message: this.getErrorMessage(lastError, lastResponse),
    };
  }
  
  /**
   * Определяет, стоит ли делать retry для данного HTTP статуса
   */
  private shouldRetryForStatus(status: number): boolean {
    // Retry только для server errors и некоторых client errors
    return status >= 500 || status === 408 || status === 429;
  }
  
  /**
   * Определяет, стоит ли делать retry для данной ошибки
   */
  private shouldRetryForError(error: any): boolean {
    return isNetworkError(error) || isTimeoutError(error) || error.code === 'ECONNRESET';
  }
  
  /**
   * Категоризирует ошибку для удобного отображения
   */
  private categorizeError(error: any): string {
    if (isTimeoutError(error)) return "TIMEOUT_ERROR";
    if (isNetworkError(error)) return "NETWORK_ERROR";
    if (error?.code === 'ECONNRESET') return "CONNECTION_RESET";
    if (error?.code === 'ECONNREFUSED') return "CONNECTION_REFUSED";
    return "UNKNOWN_ERROR";
  }
  
  /**
   * Создает понятное сообщение об ошибке
   */
  private getErrorMessage(error: any, response: Response | null): string {
    if (isTimeoutError(error)) {
      return `Request timed out after ${this.defaultTimeout}ms. Check your network connection or try again later.`;
    }
    
    if (isNetworkError(error)) {
      return "Failed to connect to server. Check if the server is running and your network connection.";
    }
    
    if (error?.code === 'ECONNREFUSED') {
      return "Connection refused. The server may be down or unreachable.";
    }
    
    if (response) {
      return `Server responded with error: ${response.status} ${response.statusText}`;
    }
    
    return error?.message || "An unexpected error occurred";
  }

  // Config methods - используем централизованные endpoints
  async getConfig() {
    return this.request(API_CONFIG.ENDPOINTS.CONFIG.BASE);
  }

  async getKurs() {
    return this.request(API_CONFIG.ENDPOINTS.CONFIG.KURS);
  }
  
  async getFaq() {
    return this.request(API_CONFIG.ENDPOINTS.CONFIG.FAQ);
  }

  // Auth methods - с улучшенной валидацией и логированием
  async login(loginData: {
    loginMethod: 'email' | 'phone';
    email?: string;
    phone?: string;
    password: string;
  }) {
    const { loginMethod, email, phone, password } = loginData;
    const identifier = loginMethod === 'email' ? email : phone;
    console.log("🔐 Attempting login with", loginMethod, "for:", identifier);
    
    if (!password) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Password is required",
      };
    }
    
    if (loginMethod === 'email' && !email) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Email is required for email login",
      };
    }
    
    if (loginMethod === 'phone' && !phone) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Phone number is required for phone login",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.AUTH.LOGIN, {
      method: "POST",
      body: JSON.stringify(loginData),
    });
  }

  async register(userData: {
    registrationMethod: 'email' | 'phone';
    email?: string;
    phone?: string;
    password: string;
    name: string;
  }) {
    const { registrationMethod, email, phone, password, name } = userData;
    const identifier = registrationMethod === 'email' ? email : phone;
    console.log("📝 Attempting registration with", registrationMethod, "for:", identifier);
    
    if (!password || !name) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Password and name are required",
      };
    }
    
    if (registrationMethod === 'email' && !email) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Email is required for email registration",
      };
    }
    
    if (registrationMethod === 'phone' && !phone) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Phone number is required for phone registration",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.AUTH.REGISTER, {
      method: "POST",
      body: JSON.stringify(userData),
    });
  }

  // Legacy methods for backward compatibility
  async loginLegacy(email: string, password: string) {
    return this.login({
      loginMethod: 'email',
      email,
      password
    });
  }

  async registerLegacy(userData: {
    email: string;
    password: string;
    name: string;
    phone?: string;
  }) {
    return this.register({
      registrationMethod: 'email',
      email: userData.email,
      password: userData.password,
      name: userData.name,
      phone: userData.phone,
    });
  }

  async getCurrentUser() {
    const token = this.getToken();
    if (!token) {
      console.warn("⚠️ No auth token found for getCurrentUser");
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request(API_CONFIG.ENDPOINTS.AUTH.ME, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async logout() {
    console.log("💪 Logging out user");
    this.removeToken();
    return { 
      success: true, 
      message: "Logged out successfully" 
    };
  }

  // Order methods - с валидацией параметров
  async createOrder(orderData: any) {
    console.log("🛍️ Creating new order:", { customerName: orderData?.customerName });
    
    if (!orderData) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Order data is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.ORDERS.BASE, {
      method: "POST",
      body: JSON.stringify(orderData),
    });
  }

  async lookupOrder(nomerok: string) {
    console.log("🔍 Looking up order:", nomerok);
    
    if (!nomerok) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Order number is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.ORDERS.BY_NOMEROK(nomerok));
  }

  // Stories methods - с параметрами пагинации
  async getStories(page: number = 1, limit: number = 10) {
    console.log("📚 Fetching stories:", { page, limit });
    
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    
    return this.request(`${API_CONFIG.ENDPOINTS.STORIES.BASE}?${params}`);
  }

  async getStory(link: string) {
    console.log("📖 Fetching story:", link);
    
    if (!link) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Story link is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.STORIES.BY_LINK(link));
  }

  // Admin methods - с авторизацией и валидацией
  async getAdminOrders() {
    const token = this.getToken();
    if (!token) {
      console.warn("⚠️ No auth token for admin operation");
      return {
        success: false,
        error: "NO_TOKEN",
        message: "Authentication required for admin operations",
      };
    }

    return this.request(API_CONFIG.ENDPOINTS.ADMIN.ORDERS, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async updateOrderStatus(orderId: string, status: string) {
    console.log("⚙️ Updating order status:", { orderId, status });
    
    const token = this.getToken();
    if (!token) {
      console.warn("⚠️ No auth token for admin operation");
      return {
        success: false,
        error: "NO_TOKEN",
        message: "Authentication required for admin operations",
      };
    }
    
    if (!orderId || !status) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Order ID and status are required",
      };
    }

    return this.request(API_CONFIG.ENDPOINTS.ADMIN.ORDER_STATUS(orderId), {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ status }),
    });
  }

  // Customer methods - с валидацией ID
  async getCustomers() {
    console.log("👥 Fetching customers list");
    return this.request(API_CONFIG.ENDPOINTS.CUSTOMERS.BASE);
  }

  async getCustomer(customerId: string) {
    console.log("👤 Fetching customer:", customerId);
    
    if (!customerId) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Customer ID is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.CUSTOMERS.BY_ID(customerId));
  }

  async createCustomer(customerData: {
    name: string;
    email?: string;
    phone?: string;
    address?: {
      fullAddress: string;
      city?: string;
      postalCode?: string;
      country?: string;
    };
  }) {
    console.log("🆕 Creating new customer:", { name: customerData.name, email: customerData.email });
    
    if (!customerData.name) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Customer name is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.CUSTOMERS.BASE, {
      method: "POST",
      body: JSON.stringify(customerData),
    });
  }

  async updateCustomer(
    customerId: string,
    customerData: {
      name: string;
      email?: string;
      phone?: string;
    },
  ) {
    console.log("✏️ Updating customer:", customerId);
    
    if (!customerId || !customerData.name) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Customer ID and name are required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.CUSTOMERS.BY_ID(customerId), {
      method: "PUT",
      body: JSON.stringify(customerData),
    });
  }

  async deleteCustomer(customerId: string) {
    console.log("🗑️ Deleting customer:", customerId);
    
    if (!customerId) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Customer ID is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.CUSTOMERS.BY_ID(customerId), {
      method: "DELETE",
    });
  }

  async getCustomerAddresses(customerId: string) {
    console.log("📦 Fetching customer addresses:", customerId);
    
    if (!customerId) {
      return {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Customer ID is required",
      };
    }
    
    return this.request(API_CONFIG.ENDPOINTS.CUSTOMERS.ADDRESSES(customerId));
  }

  async addCustomerAddress(
    customerId: string,
    addressData: {
      addressType?: string;
      fullAddress: string;
      city?: string;
      postalCode?: string;
      country?: string;
      isDefault?: boolean;
    },
  ) {
    return this.request(`/customers/${customerId}/addresses`, {
      method: "POST",
      body: JSON.stringify(addressData),
    });
  }

  // Order methods
  async getOrders(params: { page?: number; limit?: number } = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });
    return this.request(`/orders?${searchParams}`);
  }

  async getOrder(id: string) {
    return this.request(`/orders/${id}`);
  }

  async updateOrder(id: string, updateData: any) {
    return this.request(`/orders/${id}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });
  }

  async deleteOrder(id: string) {
    return this.request(`/orders/${id}`, { method: "DELETE" });
  }

  // Profile methods
  async getProfile() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request("/profile", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async updateProfile(profileData: {
    name?: string;
    fullName?: string;
    contactPhone?: string;
    contactEmail?: string;
    avatar?: string;
  }) {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    // Filter out undefined values to avoid validation errors
    const cleanProfileData = Object.fromEntries(
      Object.entries(profileData).filter(([_, value]) => value !== undefined)
    );

    return this.request("/profile", {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(cleanProfileData),
    });
  }

  async getAddresses() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request("/profile/addresses", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async addAddress(addressData: {
    fullAddress: string;
    city: string;
    postalCode?: string;
    country?: string;
    addressComments?: string;
    isDefault?: boolean;
  }) {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request("/profile/addresses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(addressData),
    });
  }

  async updateAddress(
    addressId: string,
    addressData: {
      fullAddress?: string;
      city?: string;
      postalCode?: string;
      country?: string;
      addressComments?: string;
      isDefault?: boolean;
    },
  ) {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request(`/profile/addresses/${addressId}`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(addressData),
    });
  }

  async deleteAddress(addressId: string) {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request(`/profile/addresses/${addressId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async getSubscription() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request("/profile/subscription", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async getSubscriptionHistory() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request("/profile/subscription/history", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  // Subscription tiers (public)
  async getSubscriptionTiers() {
    return this.request("/subscriptions/tiers");
  }

  async getSubscriptionStatus() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: "NO_TOKEN",
        message: "No authentication token",
      };
    }

    return this.request("/subscriptions/status", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  // Token management - с дополнительным логированием
  private getToken(): string | null {
    if (typeof localStorage !== "undefined") {
      const token = localStorage.getItem("auth_token");
      if (token) {
        console.log("🔑 Found auth token in localStorage");
      }
      return token;
    }
    console.warn("⚠️ localStorage not available - token management disabled");
    return null;
  }

  private setToken(token: string): void {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("auth_token", token);
      console.log("🔑 Auth token saved to localStorage");
    } else {
      console.warn("⚠️ localStorage not available - cannot save token");
    }
  }

  private removeToken(): void {
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem("auth_token");
      console.log("🚫 Auth token removed from localStorage");
    } else {
      console.warn("⚠️ localStorage not available - cannot remove token");
    }
  }

  // Verification methods removed - no verification required
  // Legacy placeholders for backward compatibility
  async verifyPhone(data: { token: string; code: string }) {
    console.warn("⚠️ Verification methods are deprecated - users are auto-activated");
    return {
      success: true,
      message: "User already verified - no action needed"
    };
  }

  async resendPhoneVerification(data: { token: string }) {
    console.warn("⚠️ Verification methods are deprecated - users are auto-activated");
    return {
      success: true,
      message: "No verification needed - user already active"
    };
  }
  
  // Методы для диагностики и валидации системы
  
  /**
   * Проверка здоровья API сервера
   */
  async checkHealth(): Promise<ApiResponse> {
    console.log("❤️‍🩹 Checking API health");
    
    try {
      const healthUrl = API_CONFIG.buildHealthUrl();
      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: AbortSignal.timeout(5000) // Короткий тайм-аут для health check
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log("✅ API health check passed:", data);
        return { success: true, data };
      } else {
        console.error("❌ API health check failed:", response.status);
        return {
          success: false,
          error: `HTTP_${response.status}`,
          message: `Health check failed: ${response.statusText}`
        };
      }
    } catch (error: any) {
      console.error("❌ API health check error:", error);
      return {
        success: false,
        error: "HEALTH_CHECK_FAILED",
        message: error.message || "Failed to check API health"
      };
    }
  }
  
  /**
   * Валидация конфигурации API клиента
   */
  async validateConfiguration(): Promise<{
    isValid: boolean;
    issues: string[];
    recommendations: string[];
  }> {
    console.log("🔍 Validating API client configuration");
    
    const issues: string[] = [];
    const recommendations: string[] = [];
    
    // Проверка основного URL
    if (!this.baseUrl) {
      issues.push("Base URL is not configured");
    } else if (!this.baseUrl.startsWith('http')) {
      issues.push("Base URL must start with http:// or https://");
    } else if (this.baseUrl.endsWith('/')) {
      issues.push("Base URL should not end with trailing slash");
      recommendations.push("Remove trailing slash from your PUBLIC_API_URL environment variable");
    }
    
    // Проверка тайм-аутов
    if (this.defaultTimeout < 1000) {
      issues.push("Request timeout is too low (< 1 second)");
      recommendations.push("Increase timeout to at least 5 seconds");
    } else if (this.defaultTimeout > 30000) {
      issues.push("Request timeout is very high (> 30 seconds)");
      recommendations.push("Consider reducing timeout for better user experience");
    }
    
    // Проверка retry конфигурации
    if (this.defaultRetries < 0) {
      issues.push("Retry count cannot be negative");
    } else if (this.defaultRetries > 5) {
      issues.push("Retry count is very high (> 5)");
      recommendations.push("Consider reducing retry count to avoid long delays");
    }
    
    // Проверка localStorage
    if (typeof localStorage === "undefined") {
      issues.push("localStorage is not available (token management disabled)");
      recommendations.push("Ensure application runs in browser environment");
    }
    
    const result = {
      isValid: issues.length === 0,
      issues,
      recommendations
    };
    
    console.log("📊 Configuration validation result:", result);
    return result;
  }
  
  /**
   * Полная диагностика системы
   */
  async runFullDiagnostics(this: ApiClient): Promise<{
    configuration: Awaited<ReturnType<typeof this.validateConfiguration>>;
    health: ApiResponse;
    summary: {
      overallStatus: 'healthy' | 'warning' | 'error';
      criticalIssues: number;
      warnings: number;
      uptime: boolean;
    };
  }> {
    console.log("🔬 Running full system diagnostics");
    
    const [configValidation, healthCheck] = await Promise.all([
      this.validateConfiguration(),
      this.checkHealth()
    ]);
    
    const criticalIssues = configValidation.issues.length + (healthCheck.success ? 0 : 1);
    const warnings = configValidation.recommendations.length;
    const uptime = healthCheck.success;
    
    let overallStatus: 'healthy' | 'warning' | 'error';
    if (criticalIssues > 0) {
      overallStatus = 'error';
    } else if (warnings > 0) {
      overallStatus = 'warning';
    } else {
      overallStatus = 'healthy';
    }
    
    const result = {
      configuration: configValidation,
      health: healthCheck,
      summary: {
        overallStatus,
        criticalIssues,
        warnings,
        uptime
      }
    };
    
    console.log("📊 Full diagnostics completed:", result.summary);
    return result;
  }
}

export const api = new ApiClient();
export default api;
