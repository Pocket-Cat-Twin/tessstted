import { writable } from 'svelte/store';
import { api } from '$lib/api/client-simple';
import type { Order, OrderCreate } from '@yuyu/shared';

interface OrdersState {
  orders: Order[];
  currentOrder: Order | null;
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  } | null;
}

const initialState: OrdersState = {
  orders: [],
  currentOrder: null,
  loading: false,
  error: null,
  pagination: null
};

function createOrdersStore() {
  const { subscribe, set, update } = writable<OrdersState>(initialState);

  const lookupOrder = async (nomerok: string) => {
    update(state => ({ ...state, loading: true, error: null }));
    
    try {
      const response = await api.lookupOrder(nomerok);
      if (response.success) {
        update(state => ({ 
          ...state, 
          loading: false,
          currentOrder: response.data.order
        }));
        
        return { success: true, order: response.data.order };
      } else {
        update(state => ({ 
          ...state, 
          loading: false, 
          error: response.message || 'Заказ не найден' 
        }));
        return { success: false, message: response.message };
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Ошибка поиска заказа';
      update(state => ({ 
        ...state, 
        loading: false, 
        error: errorMessage 
      }));
      return { success: false, message: errorMessage };
    }
  };

  return {
    subscribe,

    // Create new order
    create: async (orderData: OrderCreate) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const response = await api.createOrder(orderData);
        if (response.success) {
          update(state => ({ 
            ...state, 
            loading: false,
            currentOrder: response.data.order
          }));
          
          return { 
            success: true, 
            order: response.data.order,
            lookupUrl: response.data.lookupUrl
          };
        } else {
          update(state => ({ 
            ...state, 
            loading: false, 
            error: response.message || 'Ошибка создания заказа' 
          }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        const errorMessage = error.message || 'Ошибка подключения к серверу';
        update(state => ({ 
          ...state, 
          loading: false, 
          error: errorMessage 
        }));
        return { success: false, message: errorMessage };
      }
    },

    // Lookup order by nomerok
    lookup: lookupOrder,

    // Alias for lookup method
    getByNumber: lookupOrder,

    // Load orders (admin)
    loadOrders: async (params: { 
      page?: number; 
      limit?: number; 
      status?: string; 
      search?: string; 
    } = {}) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const response = await api.getOrders(params);
        if (response.success) {
          update(state => ({ 
            ...state, 
            loading: false,
            orders: response.data,
            pagination: response.pagination
          }));
          
          return { success: true };
        } else {
          update(state => ({ 
            ...state, 
            loading: false, 
            error: response.message || 'Ошибка загрузки заказов' 
          }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        const errorMessage = error.message || 'Ошибка загрузки заказов';
        update(state => ({ 
          ...state, 
          loading: false, 
          error: errorMessage 
        }));
        return { success: false, message: errorMessage };
      }
    },

    // Get order by ID (admin)
    getOrder: async (id: string) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const response = await api.getOrder(id);
        if (response.success) {
          update(state => ({ 
            ...state, 
            loading: false,
            currentOrder: response.data.order
          }));
          
          return { success: true, order: response.data.order };
        } else {
          update(state => ({ 
            ...state, 
            loading: false, 
            error: response.message || 'Заказ не найден' 
          }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        const errorMessage = error.message || 'Ошибка загрузки заказа';
        update(state => ({ 
          ...state, 
          loading: false, 
          error: errorMessage 
        }));
        return { success: false, message: errorMessage };
      }
    },

    // Update order (admin)
    updateOrder: async (id: string, updateData: any) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const response = await api.updateOrder(id, updateData);
        if (response.success) {
          update(state => ({ 
            ...state, 
            loading: false,
            currentOrder: response.data.order,
            orders: state.orders.map(order => 
              order.id === id ? response.data.order : order
            )
          }));
          
          return { success: true, order: response.data.order };
        } else {
          update(state => ({ 
            ...state, 
            loading: false, 
            error: response.message || 'Ошибка обновления заказа' 
          }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        const errorMessage = error.message || 'Ошибка обновления заказа';
        update(state => ({ 
          ...state, 
          loading: false, 
          error: errorMessage 
        }));
        return { success: false, message: errorMessage };
      }
    },

    // Delete order (admin)
    deleteOrder: async (id: string) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const response = await api.deleteOrder(id);
        if (response.success) {
          update(state => ({ 
            ...state, 
            loading: false,
            orders: state.orders.filter(order => order.id !== id)
          }));
          
          return { success: true };
        } else {
          update(state => ({ 
            ...state, 
            loading: false, 
            error: response.message || 'Ошибка удаления заказа' 
          }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        const errorMessage = error.message || 'Ошибка удаления заказа';
        update(state => ({ 
          ...state, 
          loading: false, 
          error: errorMessage 
        }));
        return { success: false, message: errorMessage };
      }
    },

    // Clear current order
    clearCurrent: () => {
      update(state => ({ ...state, currentOrder: null }));
    },

    // Clear error
    clearError: () => {
      update(state => ({ ...state, error: null }));
    },

    // Reset store
    reset: () => {
      set(initialState);
    }
  };
}

export const ordersStore = createOrdersStore();