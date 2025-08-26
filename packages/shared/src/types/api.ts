import { z } from "zod";

// Generic API response schema
export const apiResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z.any().optional(),
  error: z.string().optional(),
  errors: z.record(z.string(), z.array(z.string())).optional(),
});

// Pagination schema
export const paginationSchema = z.object({
  page: z.number().int().min(1).default(1),
  limit: z.number().int().min(1).max(100).default(10),
  total: z.number().int().min(0),
  totalPages: z.number().int().min(0),
  hasNext: z.boolean(),
  hasPrev: z.boolean(),
});

// Paginated response schema
export const paginatedResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z.array(z.any()),
  pagination: paginationSchema,
  error: z.string().optional(),
});

// File upload schema
export const fileUploadSchema = z.object({
  originalName: z.string(),
  filename: z.string(),
  path: z.string(),
  mimetype: z.string(),
  size: z.number().int().positive(),
  url: z.string().url(),
});

// Auth token schema
export const authTokenSchema = z.object({
  token: z.string(),
  refreshToken: z.string().optional(),
  expiresAt: z.date(),
  user: z.any(), // Will be typed as User in implementation
});

// Login request schema
export const loginRequestSchema = z.object({
  loginMethod: z.enum(["email", "phone"]),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  password: z.string().min(1),
}).refine(
  (data) => {
    if (data.loginMethod === "email") {
      return !!data.email;
    } else if (data.loginMethod === "phone") {
      return !!data.phone;
    }
    return false;
  },
  {
    message: "Email is required for email login, phone is required for phone login",
    path: ["loginMethod"],
  }
);

// Login response schema
export const loginResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  error: z.string().optional(),
  data: z.object({
    token: z.string(),
    user: z.object({
      id: z.string(),
      email: z.string().optional(),
      phone: z.string().optional(),
      name: z.string(),
      role: z.string(),
      status: z.string(),
    }),
  }).optional(),
});

// Registration request schema  
export const registrationRequestSchema = z.object({
  registrationMethod: z.enum(["email", "phone"]),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  password: z.string().min(6),
  name: z.string().min(1),
  fullName: z.string().optional(),
}).refine(
  (data) => {
    if (data.registrationMethod === "email") {
      return !!data.email;
    } else if (data.registrationMethod === "phone") {
      return !!data.phone;
    }
    return false;
  },
  {
    message: "Email is required for email registration, phone is required for phone registration",
    path: ["registrationMethod"],
  }
);

// Error codes enum
export enum ErrorCode {
  VALIDATION_ERROR = "VALIDATION_ERROR",
  AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR",
  AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR",
  NOT_FOUND_ERROR = "NOT_FOUND_ERROR",
  DUPLICATE_ERROR = "DUPLICATE_ERROR",
  INTERNAL_ERROR = "INTERNAL_ERROR",
  RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR",
  FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR",
}

// API error schema
export const apiErrorSchema = z.object({
  code: z.nativeEnum(ErrorCode),
  message: z.string(),
  details: z.any().optional(),
  statusCode: z.number().int().min(100).max(599),
});

// Search schema
export const searchSchema = z.object({
  query: z.string().min(1).max(100),
  page: z.number().int().min(1).default(1),
  limit: z.number().int().min(1).max(100).default(10),
  sortBy: z.string().optional(),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
});

// Bulk operation schema
export const bulkOperationSchema = z.object({
  operation: z.enum(["delete", "update", "archive"]),
  ids: z.array(z.string().uuid()),
  data: z.any().optional(),
});

// Types
export type ApiResponse<T = any> = z.infer<typeof apiResponseSchema> & {
  data?: T;
};

export type PaginatedResponse<T = any> = z.infer<
  typeof paginatedResponseSchema
> & {
  data: T[];
};

export type Pagination = z.infer<typeof paginationSchema>;
export type FileUpload = z.infer<typeof fileUploadSchema>;
export type AuthToken = z.infer<typeof authTokenSchema>;
export type ApiError = z.infer<typeof apiErrorSchema>;
export type Search = z.infer<typeof searchSchema>;
export type BulkOperation = z.infer<typeof bulkOperationSchema>;

// Auth types
export type LoginRequest = z.infer<typeof loginRequestSchema>;
export type LoginResponse = z.infer<typeof loginResponseSchema>;
export type RegistrationRequest = z.infer<typeof registrationRequestSchema>;
