// Export all types from type modules
export * from "./user";
export * from "./order";
export * from "./story";
export * from "./api";
export * from "./config";

// FAQ type for now (placeholder until implemented)
export interface FAQ {
  id: string;
  question: string;
  answer: string;
  category?: string;
  order?: number;
  isPublished: boolean;
  createdAt: Date;
  updatedAt: Date;
}