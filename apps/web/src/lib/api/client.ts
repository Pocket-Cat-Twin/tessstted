import type { ApiResponse, PaginatedResponse } from "@yuyu/shared";

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = "/api/v1") {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: Omit<RequestInit, 'body'> & { body?: string } = {},
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    const config: Omit<RequestInit, 'body'> & { body?: string } = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      credentials: "include", // Include cookies
      ...options,
    };

    // Add auth token if available
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("auth_token");
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        };
      }
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new ApiError(
          data.message || "Request failed",
          response.status,
          data,
        );
      }

      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError("Network error", 500, { originalError: error });
    }
  }

  // Auth methods
  async login(email: string, password: string) {
    return this.request<{ token: string; user: any }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async register(userData: {
    email: string;
    password: string;
    name: string;
    phone?: string;
  }) {
    return this.request<{ user: any }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
  }

  async logout() {
    return this.request("/auth/logout", { method: "POST" });
  }

  async getCurrentUser() {
    return this.request<{ user: any }>("/auth/me");
  }

  async verifyEmail(token: string) {
    return this.request("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  async forgotPassword(email: string) {
    return this.request("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  async resetPassword(token: string, password: string) {
    return this.request("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    });
  }

  // Order methods
  async createOrder(orderData: any) {
    return this.request<{ order: any; lookupUrl: string }>("/orders", {
      method: "POST",
      body: JSON.stringify(orderData),
    });
  }

  async lookupOrder(nomerok: string) {
    return this.request<{ order: any }>(
      `/orders/lookup/${encodeURIComponent(nomerok)}`,
    );
  }

  async getOrders(
    params: {
      page?: number;
      limit?: number;
      status?: string;
      search?: string;
    } = {},
  ) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });

    return this.request<PaginatedResponse<any>>(`/orders?${searchParams}`);
  }

  async getOrder(id: string) {
    return this.request<{ order: any }>(`/orders/${id}`);
  }

  async updateOrder(id: string, updateData: any) {
    return this.request<{ order: any }>(`/orders/${id}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });
  }

  async deleteOrder(id: string) {
    return this.request(`/orders/${id}`, { method: "DELETE" });
  }

  // Story methods
  async getStories(params: { page?: number; limit?: number } = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });

    return this.request<PaginatedResponse<any>>(`/stories?${searchParams}`);
  }

  async getStory(link: string) {
    return this.request<{ story: any }>(`/stories/${encodeURIComponent(link)}`);
  }

  async createStory(storyData: any) {
    return this.request<{ story: any }>("/stories", {
      method: "POST",
      body: JSON.stringify(storyData),
    });
  }

  async updateStory(id: string, updateData: any) {
    return this.request<{ story: any }>(`/stories/admin/${id}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });
  }

  async deleteStory(id: string) {
    return this.request(`/stories/${id}`, { method: "DELETE" });
  }

  // Config methods
  async getPublicConfig() {
    return this.request<{ config: Record<string, string> }>("/config/public");
  }

  async getCurrentKurs() {
    return this.request<{ kurs: number }>("/config/kurs");
  }

  async getFaqs() {
    return this.request<{ faqs: any[] }>("/config/faq");
  }

  async getConfig() {
    return this.request<{ configs: any[] }>("/config");
  }

  async updateConfig(key: string, value: string, description?: string) {
    return this.request<{ config: any }>(`/config/${key}`, {
      method: "PUT",
      body: JSON.stringify({ value, description }),
    });
  }

  // User methods
  async getUsers(
    params: {
      page?: number;
      limit?: number;
      role?: string;
      status?: string;
      search?: string;
    } = {},
  ) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });

    return this.request<PaginatedResponse<any>>(`/users?${searchParams}`);
  }

  async getUser(id: string) {
    return this.request<{ user: any }>(`/users/${id}`);
  }

  async updateUser(id: string, updateData: any) {
    return this.request<{ user: any }>(`/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });
  }

  async blockUser(id: string, reason?: string) {
    return this.request(`/users/${id}/block`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async unblockUser(id: string) {
    return this.request(`/users/${id}/unblock`, { method: "POST" });
  }

  async deleteUser(id: string) {
    return this.request(`/users/${id}`, { method: "DELETE" });
  }

  // Upload methods
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<{ upload: any }>("/uploads", {
      method: "POST",
      body: formData,
      headers: {}, // Let browser set content-type for FormData
    });
  }

  async uploadFiles(files: File[]) {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    return this.request<{ uploads: any[]; failed: any[] }>(
      "/uploads/multiple",
      {
        method: "POST",
        body: formData,
        headers: {}, // Let browser set content-type for FormData
      },
    );
  }

  async getUploads(params: { page?: number; limit?: number } = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });

    return this.request<PaginatedResponse<any>>(`/uploads?${searchParams}`);
  }

  async deleteUpload(id: string) {
    return this.request(`/uploads/${id}`, { method: "DELETE" });
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Create singleton instance
export const api = new ApiClient();
