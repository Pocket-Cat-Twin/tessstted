import { z } from "zod";

// User role enum
export enum UserRole {
  USER = "user",
  ADMIN = "admin",
}

// User status enum
export enum UserStatus {
  PENDING = "pending",
  ACTIVE = "active",
  BLOCKED = "blocked",
}

// Base user schema (legacy)
export const userSchemaLegacy = z.object({
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

// Registration method enum
export enum RegistrationMethod {
  EMAIL = "email",
  PHONE = "phone",
}

// Russian phone number validation regex
const RUSSIAN_PHONE_REGEX = /^\+?7[0-9]{10}$|^8[0-9]{10}$|^[0-9]{10}$/;

// Enhanced phone validation with Russian format support
const phoneSchema = z.string()
  .min(10, "Номер телефона должен содержать минимум 10 цифр")
  .max(15, "Номер телефона слишком длинный")
  .refine((phone) => {
    const digitsOnly = phone.replace(/\D/g, "");
    return digitsOnly.length >= 10 && digitsOnly.length <= 15;
  }, "Некорректный формат номера телефона")
  .transform((phone) => {
    // Normalize Russian phone numbers
    const digitsOnly = phone.replace(/\D/g, "");
    if (digitsOnly.startsWith("8") && digitsOnly.length === 11) {
      return "+7" + digitsOnly.slice(1);
    }
    if (digitsOnly.startsWith("7") && digitsOnly.length === 11) {
      return "+" + digitsOnly;
    }
    if (digitsOnly.length === 10) {
      return "+7" + digitsOnly;
    }
    return phone;
  });

// Base registration schema
const baseRegistrationSchema = z.object({
  password: z.string()
    .min(8, "Пароль должен содержать минимум 8 символов")
    .max(100, "Пароль слишком длинный")
    .regex(/^(?=.*[a-zA-Z])(?=.*\d)/, "Пароль должен содержать буквы и цифры"),
  name: z.string()
    .min(1, "Имя обязательно")
    .max(100, "Имя слишком длинное")
    .trim(),
  registrationMethod: z.nativeEnum(RegistrationMethod),
});

// Email registration schema
export const userRegistrationEmailSchema = baseRegistrationSchema.extend({
  email: z.string()
    .email("Введите корректный email адрес")
    .max(254, "Email слишком длинный")
    .toLowerCase(),
  registrationMethod: z.literal(RegistrationMethod.EMAIL),
  phone: z.string().optional(), // Optional secondary contact
});

// Phone registration schema
export const userRegistrationPhoneSchema = baseRegistrationSchema.extend({
  phone: phoneSchema,
  registrationMethod: z.literal(RegistrationMethod.PHONE),
  email: z.string().email().optional(), // Optional secondary contact
});

// Union type for all registration methods
export const userRegistrationSchema = z.discriminatedUnion("registrationMethod", [
  userRegistrationEmailSchema,
  userRegistrationPhoneSchema,
]);

// Base login schema
const baseLoginSchema = z.object({
  password: z.string().min(1, "Пароль обязателен"),
  loginMethod: z.nativeEnum(RegistrationMethod),
});

// Email login schema
export const userLoginEmailSchema = baseLoginSchema.extend({
  email: z.string()
    .email("Введите корректный email адрес")
    .toLowerCase(),
  loginMethod: z.literal(RegistrationMethod.EMAIL),
});

// Phone login schema
export const userLoginPhoneSchema = baseLoginSchema.extend({
  phone: phoneSchema,
  loginMethod: z.literal(RegistrationMethod.PHONE),
});

// Union type for all login methods
export const userLoginSchema = z.discriminatedUnion("loginMethod", [
  userLoginEmailSchema,
  userLoginPhoneSchema,
]);

// Legacy email-only login schema for backward compatibility
export const userLoginLegacySchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

// User profile update schema
export const userProfileUpdateSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  phone: z.string().optional(),
  avatar: z.string().url().optional(),
});

// Password reset schemas with multi-method support
const basePasswordResetRequestSchema = z.object({
  resetMethod: z.nativeEnum(RegistrationMethod),
});

export const passwordResetRequestEmailSchema = basePasswordResetRequestSchema.extend({
  email: z.string().email("Введите корректный email адрес").toLowerCase(),
  resetMethod: z.literal(RegistrationMethod.EMAIL),
});

export const passwordResetRequestPhoneSchema = basePasswordResetRequestSchema.extend({
  phone: phoneSchema,
  resetMethod: z.literal(RegistrationMethod.PHONE),
});

export const passwordResetRequestSchema = z.discriminatedUnion("resetMethod", [
  passwordResetRequestEmailSchema,
  passwordResetRequestPhoneSchema,
]);

// Legacy email-only reset schema
export const passwordResetRequestLegacySchema = z.object({
  email: z.string().email(),
});

export const passwordResetSchema = z.object({
  token: z.string(),
  password: z.string().min(8).max(100),
});

// Email verification schema (legacy)
export const emailVerificationSchemaLegacy = z.object({
  token: z.string(),
});

// Enhanced user schema with registration method tracking
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  name: z.string().min(1).max(100),
  registrationMethod: z.nativeEnum(RegistrationMethod),
  role: z.nativeEnum(UserRole).default(UserRole.USER),
  status: z.nativeEnum(UserStatus).default(UserStatus.PENDING),
  emailVerified: z.boolean().default(false),
  phoneVerified: z.boolean().default(false),
  avatar: z.string().url().optional(),
  // Contact information (can be different from auth credentials)
  contactEmail: z.string().email().optional(),
  contactPhone: z.string().optional(),
  lastLoginAt: z.date().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
}).refine(
  (data) => data.email || data.phone,
  {
    message: "Пользователь должен иметь email или телефон",
    path: ["email"],
  }
);

// Verification schemas
export const emailVerificationSchema = z.object({
  token: z.string().min(1, "Токен обязателен"),
});

export const phoneVerificationSchema = z.object({
  token: z.string().min(1, "Токен обязателен"),
  code: z.string()
    .length(6, "Код должен содержать 6 цифр")
    .regex(/^\d{6}$/, "Код должен содержать только цифры"),
});

// API Response schemas
export const authResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z.object({
    user: userSchema,
    token: z.string(),
    requiresVerification: z.boolean().optional(),
    verificationMethod: z.nativeEnum(RegistrationMethod).optional(),
  }).optional(),
  error: z.string().optional(),
});

// Types with enhanced type safety
export type User = z.infer<typeof userSchema>;
export type UserRegistration = z.infer<typeof userRegistrationSchema>;
export type UserRegistrationEmail = z.infer<typeof userRegistrationEmailSchema>;
export type UserRegistrationPhone = z.infer<typeof userRegistrationPhoneSchema>;
export type UserLogin = z.infer<typeof userLoginSchema>;
export type UserLoginEmail = z.infer<typeof userLoginEmailSchema>;
export type UserLoginPhone = z.infer<typeof userLoginPhoneSchema>;
export type UserLoginLegacy = z.infer<typeof userLoginLegacySchema>;
export type UserProfileUpdate = z.infer<typeof userProfileUpdateSchema>;
export type PasswordResetRequest = z.infer<typeof passwordResetRequestSchema>;
export type PasswordResetRequestEmail = z.infer<typeof passwordResetRequestEmailSchema>;
export type PasswordResetRequestPhone = z.infer<typeof passwordResetRequestPhoneSchema>;
export type PasswordResetRequestLegacy = z.infer<typeof passwordResetRequestLegacySchema>;
export type PasswordReset = z.infer<typeof passwordResetSchema>;
export type EmailVerification = z.infer<typeof emailVerificationSchema>;
export type PhoneVerification = z.infer<typeof phoneVerificationSchema>;
export type AuthResponse = z.infer<typeof authResponseSchema>;

// Type guards for authentication methods
export const isEmailRegistration = (data: UserRegistration): data is UserRegistrationEmail => {
  return data.registrationMethod === RegistrationMethod.EMAIL;
};

export const isPhoneRegistration = (data: UserRegistration): data is UserRegistrationPhone => {
  return data.registrationMethod === RegistrationMethod.PHONE;
};

export const isEmailLogin = (data: UserLogin): data is UserLoginEmail => {
  return data.loginMethod === RegistrationMethod.EMAIL;
};

export const isPhoneLogin = (data: UserLogin): data is UserLoginPhone => {
  return data.loginMethod === RegistrationMethod.PHONE;
};

// Utility functions for phone number handling
export const normalizePhoneNumber = (phone: string): string => {
  const digitsOnly = phone.replace(/\D/g, "");
  if (digitsOnly.startsWith("8") && digitsOnly.length === 11) {
    return "+7" + digitsOnly.slice(1);
  }
  if (digitsOnly.startsWith("7") && digitsOnly.length === 11) {
    return "+" + digitsOnly;
  }
  if (digitsOnly.length === 10) {
    return "+7" + digitsOnly;
  }
  return phone;
};

export const formatPhoneForDisplay = (phone: string): string => {
  const clean = phone.replace(/\D/g, "");
  if (clean.startsWith("7") && clean.length === 11) {
    const number = clean.slice(1);
    return `+7 (${number.slice(0, 3)}) ${number.slice(3, 6)}-${number.slice(6, 8)}-${number.slice(8, 10)}`;
  }
  return phone;
};
