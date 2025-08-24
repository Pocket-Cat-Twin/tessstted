import { writable } from "svelte/store";
import { api } from "$lib/api/client-simple";
import type { StoryWithAuthor } from "@lolita-fashion/shared";

export interface StoriesStore {
  stories: StoryWithAuthor[];
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

const initialState: StoriesStore = {
  stories: [],
  loading: false,
  error: null,
  pagination: null,
};

export const storiesStore = writable<StoriesStore>(initialState);

// Actions
export const storiesActions = {
  async loadStories(page: number = 1, limit: number = 10) {
    storiesStore.update((state) => ({ ...state, loading: true, error: null }));

    try {
      const response = await api.getStories(page, limit);

      if (response.success) {
        const stories = response.data?.stories || [];
        const pagination = response.data?.pagination || {
          page,
          limit,
          total: stories.length,
          totalPages: Math.ceil(stories.length / limit),
          hasNext: false,
          hasPrev: page > 1,
        };

        storiesStore.update((state) => ({
          ...state,
          stories,
          pagination,
          loading: false,
        }));
      } else {
        throw new Error(response.message || "Failed to load stories");
      }
    } catch (error) {
      storiesStore.update((state) => ({
        ...state,
        error:
          error instanceof Error ? error.message : "Failed to load stories",
        loading: false,
      }));
    }
  },

  async loadStory(link: string): Promise<StoryWithAuthor | null> {
    try {
      const response = await api.getStory(link);

      if (response.success) {
        return response.data;
      } else {
        throw new Error(response.message || "Failed to load story");
      }
    } catch (error) {
      console.error("Error loading story:", error);
      return null;
    }
  },

  clearError() {
    storiesStore.update((state) => ({ ...state, error: null }));
  },

  reset() {
    storiesStore.set(initialState);
  },
};
