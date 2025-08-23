import { writable } from "svelte/store";
import { browser } from "$app/environment";
import { api } from "$lib/api/client-simple";

interface ConfigState {
  config: Record<string, string>;
  kurs: number;
  faqs: any[];
  loading: boolean;
  initialized: boolean;
}

const initialState: ConfigState = {
  config: {},
  kurs: 13.5,
  faqs: [],
  loading: false,
  initialized: false,
};

function createConfigStore() {
  const { subscribe, update } = writable<ConfigState>(initialState);

  return {
    subscribe,

    // Initialize config
    init: async () => {
      if (!browser) return;

      update((state) => ({ ...state, loading: true }));

      try {
        // Load public config, kurs, and FAQs in parallel
        const [configResponse, kursResponse] = await Promise.all([
          api.getConfig(),
          api.getKurs(),
        ]);

        update((state) => ({
          ...state,
          config: configResponse.success ? configResponse.data.config : {},
          kurs: kursResponse.success ? kursResponse.data.kurs : 13.5,
          faqs: [],
          loading: false,
          initialized: true,
        }));
      } catch (error) {
        console.error("Failed to load config:", error);
        update((state) => ({
          ...state,
          loading: false,
          initialized: true,
        }));
      }
    },

    // Update currency rate
    updateKurs: async () => {
      try {
        const response = await api.getKurs();
        if (response.success) {
          update((state) => ({
            ...state,
            kurs: response.data.kurs,
          }));
        }
      } catch (error) {
        console.error("Failed to update kurs:", error);
      }
    },

    // Get config value
    get: (key: string, defaultValue: string = "") => {
      let currentConfig: Record<string, string> = {};
      subscribe((state) => {
        currentConfig = state.config;
      })();
      return currentConfig[key] || defaultValue;
    },

    // Refresh all config
    refresh: async () => {
      update((state) => ({ ...state, loading: true }));

      try {
        const [configResponse, kursResponse] = await Promise.all([
          api.getConfig(),
          api.getKurs(),
        ]);

        update((state) => ({
          ...state,
          config: configResponse.success
            ? configResponse.data.config
            : state.config,
          kurs: kursResponse.success ? kursResponse.data.kurs : state.kurs,
          faqs: [],
          loading: false,
        }));
      } catch (error) {
        console.error("Failed to refresh config:", error);
        update((state) => ({ ...state, loading: false }));
      }
    },
  };
}

export const configStore = createConfigStore();

// Export actions for convenience
export const configActions = {
  init: configStore.init,
  updateKurs: configStore.updateKurs,
  refresh: configStore.refresh,
  get: configStore.get,
};
