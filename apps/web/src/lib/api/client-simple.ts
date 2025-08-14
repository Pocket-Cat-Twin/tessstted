// Simplified API client for development
const API_BASE_URL = 'http://localhost:3001/api/v1';

interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      return {
        success: false,
        error: 'NETWORK_ERROR',
        message: 'Failed to connect to server',
      };
    }
  }

  // Config methods
  async getConfig() {
    return this.request('/config');
  }

  async getKurs() {
    return this.request('/config/kurs');
  }

  // Auth methods
  async login(email: string, password: string) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async register(userData: {
    email: string;
    password: string;
    name: string;
    phone?: string;
  }) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getCurrentUser() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'NO_TOKEN',
        message: 'No authentication token',
      };
    }

    return this.request('/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async logout() {
    this.removeToken();
    return { success: true };
  }

  // Order methods
  async createOrder(orderData: any) {
    return this.request('/orders', {
      method: 'POST',
      body: JSON.stringify(orderData),
    });
  }

  async lookupOrder(nomerok: string) {
    return this.request(`/orders/${nomerok}`);
  }

  // Stories methods
  async getStories(page: number = 1, limit: number = 10) {
    return this.request(`/stories`);
  }
  
  async getStory(link: string) {
    return this.request(`/stories/${link}`);
  }

  // Admin methods
  async getAdminOrders() {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'NO_TOKEN',
        message: 'No authentication token',
      };
    }

    return this.request('/admin/orders', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async updateOrderStatus(orderId: string, status: string) {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'NO_TOKEN', 
        message: 'No authentication token',
      };
    }

    return this.request(`/admin/orders/${orderId}/status`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ status }),
    });
  }

  // Token management
  private getToken(): string | null {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  private setToken(token: string) {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  private removeToken() {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }
}

export const api = new ApiClient();
export default api;