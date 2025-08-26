// Shared types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// Error codes enum
export enum ErrorCode {
  VALIDATION_ERROR = "VALIDATION_ERROR",
  NOT_FOUND_ERROR = "NOT_FOUND_ERROR", 
  UNAUTHORIZED_ERROR = "UNAUTHORIZED_ERROR",
  FORBIDDEN_ERROR = "FORBIDDEN_ERROR",
  DUPLICATE_ERROR = "DUPLICATE_ERROR",
  CONFLICT_ERROR = "CONFLICT_ERROR",
  INTERNAL_ERROR = "INTERNAL_ERROR",
}
