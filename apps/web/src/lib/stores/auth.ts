import { writable } from "svelte/store";
import { browser } from "$app/environment";
import { api } from "$lib/api/client-simple";
import type { User } from "@yuyu/shared";

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
}

const initialState: AuthState = {
  user: null,
  loading: false,
  initialized: false,
};

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>(initialState);

  return {
    subscribe,

    // Initialize auth state
    init: async () => {
      if (!browser) return;

      update((state) => ({ ...state, loading: true }));

      try {
        const response = await api.getCurrentUser();
        if (response.success && response.data?.user) {
          update((state) => ({
            ...state,
            user: response.data.user,
            loading: false,
            initialized: true,
          }));
        } else {
          update((state) => ({
            ...state,
            user: null,
            loading: false,
            initialized: true,
          }));
        }
      } catch (_error) {
        update((state) => ({
          ...state,
          user: null,
          loading: false,
          initialized: true,
        }));
      }
    },

    // Login
    login: async (email: string, password: string) => {
      update((state) => ({ ...state, loading: true }));

      try {
        const response = await api.login(email, password);
        if (response.success && response.data) {
          // Store token
          if (browser && response.data.token) {
            localStorage.setItem("auth_token", response.data.token);
          }

          update((state) => ({
            ...state,
            user: response.data.user,
            loading: false,
          }));

          return { success: true };
        } else {
          update((state) => ({ ...state, loading: false }));
          return {
            success: false,
            message: response.message || "Ошибка входа",
          };
        }
      } catch (error: any) {
        update((state) => ({ ...state, loading: false }));
        return {
          success: false,
          message: error.message || "Ошибка подключения к серверу",
        };
      }
    },

    // Register
    register: async (userData: {
      email: string;
      password: string;
      name: string;
      phone?: string;
    }) => {
      update((state) => ({ ...state, loading: true }));

      try {
        const response = await api.register(userData);
        update((state) => ({ ...state, loading: false }));

        if (response.success) {
          return { success: true, message: response.message };
        } else {
          return {
            success: false,
            message: response.message || "Ошибка регистрации",
          };
        }
      } catch (error: any) {
        update((state) => ({ ...state, loading: false }));
        return {
          success: false,
          message: error.message || "Ошибка подключения к серверу",
        };
      }
    },

    // Logout
    logout: async () => {
      update((state) => ({ ...state, loading: true }));

      try {
        await api.logout();

        // Clear token
        if (browser) {
          localStorage.removeItem("auth_token");
        }

        update((state) => ({
          ...state,
          user: null,
          loading: false,
        }));

        return { success: true };
      } catch (_error) {
        // Even if logout fails on server, clear local state
        if (browser) {
          localStorage.removeItem("auth_token");
        }

        update((state) => ({
          ...state,
          user: null,
          loading: false,
        }));

        return { success: true };
      }
    },

    // Update user profile
    updateProfile: async (profileData: Partial<User>) => {
      update((state) => ({ ...state, loading: true }));

      try {
        // API call would go here
        update((state) => ({
          ...state,
          user: state.user ? { ...state.user, ...profileData } : null,
          loading: false,
        }));

        return { success: true };
      } catch (error: any) {
        update((state) => ({ ...state, loading: false }));
        return { success: false, message: error.message };
      }
    },

    // Clear state
    clear: () => {
      set(initialState);
      if (browser) {
        localStorage.removeItem("auth_token");
      }
    },
  };
}

export const authStore = createAuthStore();
