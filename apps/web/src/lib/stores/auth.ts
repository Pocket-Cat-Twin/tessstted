import { writable } from "svelte/store";
import { browser } from "$app/environment";
import { api } from "$lib/api/client-simple";
import type { User } from "@lolita-fashion/shared";

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
      console.log('🔄 Auth init STARTING');
      
      if (!browser) {
        console.log('❌ Auth init SKIPPED - not in browser');
        return;
      }

      // Check if already initializing or initialized to prevent loops
      let currentState: AuthState;
      const unsubscribe = subscribe((state) => { currentState = state; });
      unsubscribe();

      if (currentState!.loading) {
        console.log('⚠️ Auth init already in progress, skipping...');
        return;
      }

      if (currentState!.initialized) {
        console.log('✅ Auth already initialized, skipping...');
        return;
      }

      console.log('🔄 Auth init proceeding, setting loading=true');
      update((state) => ({ ...state, loading: true }));

      try {
        console.log('🔍 Calling getCurrentUser API...');
        const response = await api.getCurrentUser();
        console.log('📥 Auth init response received:', response);
        
        if (response.success && response.user) {
          console.log('✅ Auth init SUCCESS - user found:', {
            id: response.user.id,
            email: response.user.email,
            name: response.user.name
          });
          
          update((state) => ({
            ...state,
            user: response.user,
            loading: false,
            initialized: true,
          }));
          
          console.log('🎉 Auth state updated with user data');
        } else {
          console.log('❌ Auth init FAILED - no user:', response.error || 'No user data');
          
          update((state) => ({
            ...state,
            user: null,
            loading: false,
            initialized: true,
          }));
          
          console.log('🔄 Auth state updated - no user');
        }
      } catch (error) {
        console.error('💥 Auth init ERROR:', error);
        
        update((state) => ({
          ...state,
          user: null,
          loading: false,
          initialized: true,
        }));
        
        console.log('🔄 Auth state updated after error');
      }
      
      console.log('✨ Auth init COMPLETED');
    },

    // Login
    login: async (loginData: {
      loginMethod: 'email' | 'phone';
      email?: string;
      phone?: string;
      password: string;
    }) => {
      const { loginMethod, email, phone, password } = loginData;
      update((state) => ({ ...state, loading: true }));

      try {
        const response = await api.login({ loginMethod, email, phone, password });
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

    // Legacy login method for backward compatibility
    loginLegacy: async (email: string, password: string) => {
      return await authStore.login({
        loginMethod: 'email',
        email,
        password
      });
    },

    // Register
    register: async (userData: {
      registrationMethod: 'email' | 'phone';
      email?: string;
      phone?: string;
      password: string;
      name: string;
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
