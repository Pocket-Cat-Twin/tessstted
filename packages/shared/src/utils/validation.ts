import { z } from 'zod';

/**
 * Utility function to validate data against a schema
 */
export function validateData<T>(schema: z.ZodSchema<T>, data: unknown): {
  success: boolean;
  data?: T;
  errors?: Record<string, string[]>;
} {
  try {
    const result = schema.parse(data);
    return { success: true, data: result };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: Record<string, string[]> = {};
      
      error.errors.forEach((err) => {
        const path = err.path.join('.');
        if (!errors[path]) {
          errors[path] = [];
        }
        errors[path].push(err.message);
      });
      
      return { success: false, errors };
    }
    
    return { 
      success: false, 
      errors: { general: ['Validation failed'] } 
    };
  }
}

/**
 * Safely parse data with a schema, returning null on failure
 */
export function safeParseData<T>(schema: z.ZodSchema<T>, data: unknown): T | null {
  try {
    return schema.parse(data);
  } catch {
    return null;
  }
}

/**
 * Create a partial schema from an existing schema
 */
export function createPartialSchema<T extends z.ZodRawShape>(
  schema: z.ZodObject<T>
): z.ZodObject<{ [K in keyof T]: z.ZodOptional<T[K]> }> {
  return schema.partial();
}

/**
 * Email validation regex
 */
export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Phone validation regex (international format)
 */
export const PHONE_REGEX = /^\+?[1-9]\d{1,14}$/;

/**
 * Password strength validation
 */
export function validatePasswordStrength(password: string): {
  isValid: boolean;
  score: number;
  requirements: {
    minLength: boolean;
    hasUppercase: boolean;
    hasLowercase: boolean;
    hasNumbers: boolean;
    hasSpecialChars: boolean;
  };
} {
  const requirements = {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumbers: /\d/.test(password),
    hasSpecialChars: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
  
  const score = Object.values(requirements).filter(Boolean).length;
  const isValid = score >= 4 && requirements.minLength;
  
  return { isValid, score, requirements };
}

/**
 * Sanitize string for URL slug
 */
export function createSlug(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Validate file type
 */
export function validateFileType(
  filename: string,
  allowedTypes: string[]
): boolean {
  const extension = filename.split('.').pop()?.toLowerCase();
  return extension ? allowedTypes.includes(extension) : false;
}

/**
 * Validate file size
 */
export function validateFileSize(size: number, maxSize: number): boolean {
  return size <= maxSize;
}

