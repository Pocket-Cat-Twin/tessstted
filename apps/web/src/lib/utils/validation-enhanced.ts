// Enhanced Form validation utilities with Multi-Auth Support
// Version: 2.0 - Enterprise-level validation with Russian localization

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface FieldValidation {
  field: string;
  isValid: boolean;
  error?: string;
}

export type AuthMethod = 'email' | 'phone';
export type RegistrationMethod = 'email' | 'phone';

// Email validation with enhanced Russian messages
export function validateEmail(email: string, required: boolean = true): FieldValidation {
  const result: FieldValidation = { field: "email", isValid: true };

  if (!email || email.trim() === "") {
    if (required) {
      result.isValid = false;
      result.error = "Email адрес обязателен";
    }
    return result;
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.trim())) {
    result.isValid = false;
    result.error = "Введите корректный email адрес";
    return result;
  }

  if (email.length > 254) {
    result.isValid = false;
    result.error = "Email адрес слишком длинный";
    return result;
  }

  return result;
}

// Enhanced Russian phone validation with normalization
export function validatePhone(phone: string, required: boolean = false): FieldValidation {
  const result: FieldValidation = { field: "phone", isValid: true };

  if (!phone || phone.trim() === "") {
    if (required) {
      result.isValid = false;
      result.error = "Номер телефона обязателен";
    }
    return result;
  }

  // Remove all non-digit characters
  const digitsOnly = phone.replace(/\D/g, "");

  // Russian phone number validation
  if (digitsOnly.length < 10) {
    result.isValid = false;
    result.error = "Номер телефона должен содержать минимум 10 цифр";
    return result;
  }

  if (digitsOnly.length > 15) {
    result.isValid = false;
    result.error = "Номер телефона слишком длинный";
    return result;
  }

  // Validate Russian phone format more strictly
  let normalizedDigits = digitsOnly;
  
  // Handle different Russian formats
  if (digitsOnly.startsWith("8") && digitsOnly.length === 11) {
    normalizedDigits = "7" + digitsOnly.slice(1);
  } else if (digitsOnly.startsWith("7") && digitsOnly.length === 11) {
    normalizedDigits = digitsOnly;
  } else if (digitsOnly.length === 10) {
    normalizedDigits = "7" + digitsOnly;
  }

  // Russian mobile operators validation
  const russianMobilePattern = /^7(9[0-9]{2}|8[0-9]{2}|7[0-9]{2}|6[0-9]{2}|5[0-9]{2})[0-9]{7}$/;
  if (!russianMobilePattern.test(normalizedDigits)) {
    result.isValid = false;
    result.error = "Введите корректный российский номер мобильного телефона";
    return result;
  }

  return result;
}

// Normalize Russian phone number for storage
export function normalizePhoneNumber(phone: string): string {
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
}

// Format phone for display with Russian formatting
export function formatPhoneForDisplay(phone: string): string {
  const clean = phone.replace(/\D/g, "");
  
  if (clean.startsWith("7") && clean.length === 11) {
    const number = clean.slice(1);
    return `+7 (${number.slice(0, 3)}) ${number.slice(3, 6)}-${number.slice(6, 8)}-${number.slice(8, 10)}`;
  }
  
  return phone;
}

// Phone input mask for better UX
export function applyPhoneMask(value: string): string {
  const digitsOnly = value.replace(/\D/g, '');
  
  if (digitsOnly.length === 0) return '';
  
  if (digitsOnly.startsWith('7') || digitsOnly.startsWith('8')) {
    const prefix = '+7';
    const number = digitsOnly.startsWith('8') ? digitsOnly.slice(1) : digitsOnly.slice(1);
    
    if (number.length === 0) return prefix;
    if (number.length <= 3) return `${prefix} (${number}`;
    if (number.length <= 6) return `${prefix} (${number.slice(0, 3)}) ${number.slice(3)}`;
    if (number.length <= 8) return `${prefix} (${number.slice(0, 3)}) ${number.slice(3, 6)}-${number.slice(6)}`;
    return `${prefix} (${number.slice(0, 3)}) ${number.slice(3, 6)}-${number.slice(6, 8)}-${number.slice(8, 10)}`;
  }
  
  if (digitsOnly.length === 10) {
    return `+7 (${digitsOnly.slice(0, 3)}) ${digitsOnly.slice(3, 6)}-${digitsOnly.slice(6, 8)}-${digitsOnly.slice(8, 10)}`;
  }
  
  return value;
}

// Enhanced password validation with strength requirements
export function validatePassword(password: string): FieldValidation {
  const result: FieldValidation = { field: "password", isValid: true };

  if (!password || password.trim() === "") {
    result.isValid = false;
    result.error = "Пароль обязателен";
    return result;
  }

  if (password.length < 8) {
    result.isValid = false;
    result.error = "Пароль должен содержать минимум 8 символов";
    return result;
  }

  if (password.length > 128) {
    result.isValid = false;
    result.error = "Пароль слишком длинный (максимум 128 символов)";
    return result;
  }

  // Check for at least one number and one letter
  const hasNumber = /\d/.test(password);
  const hasLetter = /[a-zA-Zа-яА-Я]/.test(password);

  if (!hasNumber || !hasLetter) {
    result.isValid = false;
    result.error = "Пароль должен содержать буквы и цифры";
    return result;
  }

  return result;
}

// Password strength calculation with Russian labels
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!password) return { score: 0, label: "", color: "" };

  let score = 0;

  // Length
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;

  // Character types
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^a-zA-Z0-9]/.test(password)) score += 1;

  // Variety
  if (
    password.length >= 8 &&
    /[a-zA-Z]/.test(password) &&
    /[0-9]/.test(password)
  )
    score += 1;

  if (score <= 2) {
    return { score, label: "Слабый", color: "text-red-600" };
  } else if (score <= 4) {
    return { score, label: "Средний", color: "text-yellow-600" };
  } else {
    return { score, label: "Надежный", color: "text-green-600" };
  }
}

// Confirm password validation
export function validateConfirmPassword(
  password: string,
  confirmPassword: string,
): FieldValidation {
  const result: FieldValidation = { field: "confirmPassword", isValid: true };

  if (!confirmPassword || confirmPassword.trim() === "") {
    result.isValid = false;
    result.error = "Подтверждение пароля обязательно";
    return result;
  }

  if (password !== confirmPassword) {
    result.isValid = false;
    result.error = "Пароли не совпадают";
    return result;
  }

  return result;
}

// Name validation with Russian names support
export function validateName(name: string): FieldValidation {
  const result: FieldValidation = { field: "name", isValid: true };

  if (!name || name.trim() === "") {
    result.isValid = false;
    result.error = "Имя обязательно";
    return result;
  }

  if (name.trim().length < 2) {
    result.isValid = false;
    result.error = "Имя должно содержать минимум 2 символа";
    return result;
  }

  if (name.trim().length > 100) {
    result.isValid = false;
    result.error = "Имя слишком длинное (максимум 100 символов)";
    return result;
  }

  // Allow Russian and Latin characters, spaces, hyphens
  const namePattern = /^[a-zA-Zа-яА-ЯёЁ\s\-]+$/;
  if (!namePattern.test(name.trim())) {
    result.isValid = false;
    result.error = "Имя может содержать только буквы, пробелы и дефисы";
    return result;
  }

  return result;
}

// SMS verification code validation
export function validateSMSCode(code: string): FieldValidation {
  const result: FieldValidation = { field: "smsCode", isValid: true };

  if (!code || code.trim() === "") {
    result.isValid = false;
    result.error = "Код подтверждения обязателен";
    return result;
  }

  if (code.length !== 6) {
    result.isValid = false;
    result.error = "Код должен содержать 6 цифр";
    return result;
  }

  if (!/^\d{6}$/.test(code)) {
    result.isValid = false;
    result.error = "Код должен содержать только цифры";
    return result;
  }

  return result;
}

// Multi-auth login validation
export function validateLoginForm(
  loginMethod: AuthMethod,
  emailOrPhone: string,
  password: string,
): ValidationResult {
  const errors: string[] = [];

  if (loginMethod === 'email') {
    const emailValidation = validateEmail(emailOrPhone, true);
    if (!emailValidation.isValid && emailValidation.error) {
      errors.push(emailValidation.error);
    }
  } else {
    const phoneValidation = validatePhone(emailOrPhone, true);
    if (!phoneValidation.isValid && phoneValidation.error) {
      errors.push(phoneValidation.error);
    }
  }

  const passwordValidation = validatePassword(password);
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.push(passwordValidation.error);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// Legacy email-only login validation
export function validateLoginFormLegacy(
  email: string,
  password: string,
): ValidationResult {
  const errors: string[] = [];

  const emailValidation = validateEmail(email, true);
  if (!emailValidation.isValid && emailValidation.error) {
    errors.push(emailValidation.error);
  }

  const passwordValidation = validatePassword(password);
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.push(passwordValidation.error);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// Multi-auth registration validation
export function validateRegisterForm(
  registrationMethod: RegistrationMethod,
  primaryContact: string,
  password: string,
  confirmPassword: string,
  name: string,
  secondaryContact?: string,
): ValidationResult {
  const errors: string[] = [];

  // Validate primary contact method
  if (registrationMethod === 'email') {
    const emailValidation = validateEmail(primaryContact, true);
    if (!emailValidation.isValid && emailValidation.error) {
      errors.push(emailValidation.error);
    }
    
    // Validate optional phone
    if (secondaryContact) {
      const phoneValidation = validatePhone(secondaryContact, false);
      if (!phoneValidation.isValid && phoneValidation.error) {
        errors.push(phoneValidation.error);
      }
    }
  } else {
    const phoneValidation = validatePhone(primaryContact, true);
    if (!phoneValidation.isValid && phoneValidation.error) {
      errors.push(phoneValidation.error);
    }
    
    // Validate optional email
    if (secondaryContact) {
      const emailValidation = validateEmail(secondaryContact, false);
      if (!emailValidation.isValid && emailValidation.error) {
        errors.push(emailValidation.error);
      }
    }
  }

  const passwordValidation = validatePassword(password);
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.push(passwordValidation.error);
  }

  const confirmPasswordValidation = validateConfirmPassword(
    password,
    confirmPassword,
  );
  if (!confirmPasswordValidation.isValid && confirmPasswordValidation.error) {
    errors.push(confirmPasswordValidation.error);
  }

  const nameValidation = validateName(name);
  if (!nameValidation.isValid && nameValidation.error) {
    errors.push(nameValidation.error);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// Legacy email-based registration validation
export function validateRegisterFormLegacy(
  email: string,
  password: string,
  confirmPassword: string,
  name: string,
  phone?: string,
): ValidationResult {
  const errors: string[] = [];

  const emailValidation = validateEmail(email, true);
  if (!emailValidation.isValid && emailValidation.error) {
    errors.push(emailValidation.error);
  }

  const passwordValidation = validatePassword(password);
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.push(passwordValidation.error);
  }

  const confirmPasswordValidation = validateConfirmPassword(
    password,
    confirmPassword,
  );
  if (!confirmPasswordValidation.isValid && confirmPasswordValidation.error) {
    errors.push(confirmPasswordValidation.error);
  }

  const nameValidation = validateName(name);
  if (!nameValidation.isValid && nameValidation.error) {
    errors.push(nameValidation.error);
  }

  if (phone) {
    const phoneValidation = validatePhone(phone, false);
    if (!phoneValidation.isValid && phoneValidation.error) {
      errors.push(phoneValidation.error);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// Real-time validation for individual fields with enhanced support
export function validateField(
  field: string,
  value: string,
  additionalValue?: string,
  required?: boolean,
): FieldValidation {
  switch (field) {
    case "email":
      return validateEmail(value, required);
    case "password":
      return validatePassword(value);
    case "confirmPassword":
      return validateConfirmPassword(additionalValue || "", value);
    case "name":
      return validateName(value);
    case "phone":
      return validatePhone(value, required);
    case "smsCode":
      return validateSMSCode(value);
    default:
      return { field, isValid: true };
  }
}

// Utility function to determine auth method from input
export function detectAuthMethod(input: string): AuthMethod | 'unknown' {
  if (!input || input.trim() === '') return 'unknown';
  
  // Check if it looks like an email
  if (input.includes('@')) {
    return 'email';
  }
  
  // Check if it looks like a phone number
  const digitsOnly = input.replace(/\D/g, '');
  if (digitsOnly.length >= 10 && digitsOnly.length <= 15) {
    return 'phone';
  }
  
  return 'unknown';
}

// Form state management helper
export function createFormValidator() {
  const errors: Record<string, string> = {};
  
  return {
    validate(field: string, value: string, additionalValue?: string, required?: boolean): boolean {
      const validation = validateField(field, value, additionalValue, required);
      if (!validation.isValid && validation.error) {
        errors[field] = validation.error;
      } else {
        delete errors[field];
      }
      return validation.isValid;
    },
    
    getErrors(): Record<string, string> {
      return { ...errors };
    },
    
    hasErrors(): boolean {
      return Object.keys(errors).length > 0;
    },
    
    clearError(field: string): void {
      delete errors[field];
    },
    
    clearAllErrors(): void {
      Object.keys(errors).forEach(key => delete errors[key]);
    }
  };
}