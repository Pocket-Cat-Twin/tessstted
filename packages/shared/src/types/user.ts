import { z } from 'zod';

// User role enum
export enum UserRole {
  USER = 'user',
  ADMIN = 'admin'
}

// User status enum
export enum UserStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  BLOCKED = 'blocked'
}

// Base user schema
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1).max(100),
  phone: z.string().optional(),
  role: z.nativeEnum(UserRole).default(UserRole.USER),
  status: z.nativeEnum(UserStatus).default(UserStatus.PENDING),
  emailVerified: z.boolean().default(false),
  avatar: z.string().url().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// User registration schema
export const userRegistrationSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(100),
  name: z.string().min(1).max(100),
  phone: z.string().optional(),
});

// User login schema
export const userLoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

// User profile update schema
export const userProfileUpdateSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  phone: z.string().optional(),
  avatar: z.string().url().optional(),
});

// Password reset schemas
export const passwordResetRequestSchema = z.object({
  email: z.string().email(),
});

export const passwordResetSchema = z.object({
  token: z.string(),
  password: z.string().min(8).max(100),
});

// Email verification schema
export const emailVerificationSchema = z.object({
  token: z.string(),
});

// Types
export type User = z.infer<typeof userSchema>;
export type UserRegistration = z.infer<typeof userRegistrationSchema>;
export type UserLogin = z.infer<typeof userLoginSchema>;
export type UserProfileUpdate = z.infer<typeof userProfileUpdateSchema>;
export type PasswordResetRequest = z.infer<typeof passwordResetRequestSchema>;
export type PasswordReset = z.infer<typeof passwordResetSchema>;
export type EmailVerification = z.infer<typeof emailVerificationSchema>;