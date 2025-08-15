import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { api } from '$lib/api/client-simple';

// Customer type definitions
export interface Customer {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  createdAt: string;
  updatedAt: string;
  addresses?: CustomerAddress[];
}

export interface CustomerAddress {
  id: string;
  customerId: string;
  addressType: string;
  fullAddress: string;
  city?: string;
  postalCode?: string;
  country: string;
  isDefault: boolean;
  createdAt: string;
}

export interface NewCustomer {
  name: string;
  email?: string;
  phone?: string;
  address?: {
    fullAddress: string;
    city?: string;
    postalCode?: string;
    country?: string;
  };
}

interface CustomersState {
  customers: Customer[];
  selectedCustomer: Customer | null;
  loading: boolean;
  searchTerm: string;
  initialized: boolean;
}

const initialState: CustomersState = {
  customers: [],
  selectedCustomer: null,
  loading: false,
  searchTerm: '',
  initialized: false
};

function createCustomersStore() {
  const { subscribe, set, update } = writable<CustomersState>(initialState);

  return {
    subscribe,
    
    // Initialize store
    init: async () => {
      if (!browser) return;
      
      update(state => ({ ...state, loading: true }));
      
      try {
        const response = await api.getCustomers();
        if (response.success && response.data) {
          update(state => ({ 
            ...state, 
            customers: response.data, 
            loading: false, 
            initialized: true 
          }));
        } else {
          update(state => ({ 
            ...state, 
            customers: [], 
            loading: false, 
            initialized: true 
          }));
        }
      } catch (error) {
        console.error('Failed to load customers:', error);
        update(state => ({ 
          ...state, 
          customers: [], 
          loading: false, 
          initialized: true 
        }));
      }
    },

    // Load all customers
    loadCustomers: async () => {
      update(state => ({ ...state, loading: true }));
      
      try {
        const response = await api.getCustomers();
        if (response.success && response.data) {
          update(state => ({ 
            ...state, 
            customers: response.data, 
            loading: false 
          }));
          return { success: true };
        } else {
          update(state => ({ ...state, loading: false }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        update(state => ({ ...state, loading: false }));
        return { success: false, message: error.message };
      }
    },

    // Get customer by ID with addresses
    getCustomer: async (customerId: string) => {
      try {
        const response = await api.getCustomer(customerId);
        if (response.success && response.data) {
          return { success: true, data: response.data };
        } else {
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        return { success: false, message: error.message };
      }
    },

    // Create new customer
    createCustomer: async (customerData: NewCustomer) => {
      update(state => ({ ...state, loading: true }));
      
      try {
        const response = await api.createCustomer(customerData);
        if (response.success && response.data) {
          update(state => ({ 
            ...state, 
            customers: [...state.customers, response.data], 
            loading: false 
          }));
          return { success: true, data: response.data };
        } else {
          update(state => ({ ...state, loading: false }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        update(state => ({ ...state, loading: false }));
        return { success: false, message: error.message };
      }
    },

    // Update customer
    updateCustomer: async (customerId: string, customerData: Partial<Customer>) => {
      update(state => ({ ...state, loading: true }));
      
      try {
        const response = await api.updateCustomer(customerId, customerData);
        if (response.success && response.data) {
          update(state => ({ 
            ...state, 
            customers: state.customers.map(c => 
              c.id === customerId ? { ...c, ...response.data } : c
            ),
            selectedCustomer: state.selectedCustomer?.id === customerId 
              ? { ...state.selectedCustomer, ...response.data } 
              : state.selectedCustomer,
            loading: false 
          }));
          return { success: true, data: response.data };
        } else {
          update(state => ({ ...state, loading: false }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        update(state => ({ ...state, loading: false }));
        return { success: false, message: error.message };
      }
    },

    // Delete customer
    deleteCustomer: async (customerId: string) => {
      update(state => ({ ...state, loading: true }));
      
      try {
        const response = await api.deleteCustomer(customerId);
        if (response.success) {
          update(state => ({ 
            ...state, 
            customers: state.customers.filter(c => c.id !== customerId),
            selectedCustomer: state.selectedCustomer?.id === customerId 
              ? null 
              : state.selectedCustomer,
            loading: false 
          }));
          return { success: true };
        } else {
          update(state => ({ ...state, loading: false }));
          return { success: false, message: response.message };
        }
      } catch (error: any) {
        update(state => ({ ...state, loading: false }));
        return { success: false, message: error.message };
      }
    },

    // Select customer
    selectCustomer: (customer: Customer | null) => {
      update(state => ({ ...state, selectedCustomer: customer }));
    },

    // Search customers
    setSearchTerm: (searchTerm: string) => {
      update(state => ({ ...state, searchTerm }));
    },

    // Get filtered customers based on search term
    getFilteredCustomers: () => {
      let filteredCustomers: Customer[] = [];
      subscribe(state => {
        filteredCustomers = state.customers.filter(customer =>
          customer.name.toLowerCase().includes(state.searchTerm.toLowerCase()) ||
          (customer.email && customer.email.toLowerCase().includes(state.searchTerm.toLowerCase())) ||
          (customer.phone && customer.phone.includes(state.searchTerm))
        );
      })();
      return filteredCustomers;
    },

    // Clear state
    clear: () => {
      set(initialState);
    }
  };
}

export const customersStore = createCustomersStore();

// Export actions for convenience
export const customersActions = {
  init: customersStore.init,
  loadCustomers: customersStore.loadCustomers,
  getCustomer: customersStore.getCustomer,
  createCustomer: customersStore.createCustomer,
  updateCustomer: customersStore.updateCustomer,
  deleteCustomer: customersStore.deleteCustomer,
  selectCustomer: customersStore.selectCustomer,
  setSearchTerm: customersStore.setSearchTerm,
  getFilteredCustomers: customersStore.getFilteredCustomers,
  clear: customersStore.clear
};