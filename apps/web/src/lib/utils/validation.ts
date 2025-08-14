// Form validation utilities

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface FieldValidation {
  field: string;
  isValid: boolean;
  error?: string;
}

// Email validation
export function validateEmail(email: string): FieldValidation {
  const result: FieldValidation = { field: 'email', isValid: true };
  
  if (!email || email.trim() === '') {
    result.isValid = false;
    result.error = 'Email обязателен';
    return result;
  }
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.trim())) {
    result.isValid = false;
    result.error = 'Введите корректный email адрес';
    return result;
  }
  
  if (email.length > 254) {
    result.isValid = false;
    result.error = 'Email слишком длинный';
    return result;
  }
  
  return result;
}

// Password validation
export function validatePassword(password: string): FieldValidation {
  const result: FieldValidation = { field: 'password', isValid: true };
  
  if (!password || password.trim() === '') {
    result.isValid = false;
    result.error = 'Пароль обязателен';
    return result;
  }
  
  if (password.length < 8) {
    result.isValid = false;
    result.error = 'Пароль должен содержать минимум 8 символов';
    return result;
  }
  
  if (password.length > 128) {
    result.isValid = false;
    result.error = 'Пароль слишком длинный';
    return result;
  }
  
  // Check for at least one number and one letter
  const hasNumber = /\d/.test(password);
  const hasLetter = /[a-zA-Zа-яА-Я]/.test(password);
  
  if (!hasNumber || !hasLetter) {
    result.isValid = false;
    result.error = 'Пароль должен содержать буквы и цифры';
    return result;
  }
  
  return result;
}

// Password strength calculation
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!password) return { score: 0, label: '', color: '' };
  
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
  if (password.length >= 8 && /[a-zA-Z]/.test(password) && /[0-9]/.test(password)) score += 1;
  
  if (score <= 2) {
    return { score, label: 'Слабый', color: 'text-red-600' };
  } else if (score <= 4) {
    return { score, label: 'Средний', color: 'text-yellow-600' };
  } else {
    return { score, label: 'Надежный', color: 'text-green-600' };
  }
}

// Confirm password validation
export function validateConfirmPassword(password: string, confirmPassword: string): FieldValidation {
  const result: FieldValidation = { field: 'confirmPassword', isValid: true };
  
  if (!confirmPassword || confirmPassword.trim() === '') {
    result.isValid = false;
    result.error = 'Подтверждение пароля обязательно';
    return result;
  }
  
  if (password !== confirmPassword) {
    result.isValid = false;
    result.error = 'Пароли не совпадают';
    return result;
  }
  
  return result;
}

// Name validation
export function validateName(name: string): FieldValidation {
  const result: FieldValidation = { field: 'name', isValid: true };
  
  if (!name || name.trim() === '') {
    result.isValid = false;
    result.error = 'Имя обязательно';
    return result;
  }
  
  if (name.trim().length < 2) {
    result.isValid = false;
    result.error = 'Имя должно содержать минимум 2 символа';
    return result;
  }
  
  if (name.trim().length > 100) {
    result.isValid = false;
    result.error = 'Имя слишком длинное';
    return result;
  }
  
  return result;
}

// Phone validation (optional)
export function validatePhone(phone: string): FieldValidation {
  const result: FieldValidation = { field: 'phone', isValid: true };
  
  if (!phone || phone.trim() === '') {
    return result; // Phone is optional
  }
  
  // Remove all non-digit characters
  const digitsOnly = phone.replace(/\D/g, '');
  
  if (digitsOnly.length < 10) {
    result.isValid = false;
    result.error = 'Номер телефона должен содержать минимум 10 цифр';
    return result;
  }
  
  if (digitsOnly.length > 15) {
    result.isValid = false;
    result.error = 'Номер телефона слишком длинный';
    return result;
  }
  
  return result;
}

// Complete form validation
export function validateLoginForm(email: string, password: string): ValidationResult {
  const errors: string[] = [];
  
  const emailValidation = validateEmail(email);
  if (!emailValidation.isValid && emailValidation.error) {
    errors.push(emailValidation.error);
  }
  
  const passwordValidation = validatePassword(password);
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.push(passwordValidation.error);
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

export function validateRegisterForm(
  email: string,
  password: string,
  confirmPassword: string,
  name: string,
  phone?: string
): ValidationResult {
  const errors: string[] = [];
  
  const emailValidation = validateEmail(email);
  if (!emailValidation.isValid && emailValidation.error) {
    errors.push(emailValidation.error);
  }
  
  const passwordValidation = validatePassword(password);
  if (!passwordValidation.isValid && passwordValidation.error) {
    errors.push(passwordValidation.error);
  }
  
  const confirmPasswordValidation = validateConfirmPassword(password, confirmPassword);
  if (!confirmPasswordValidation.isValid && confirmPasswordValidation.error) {
    errors.push(confirmPasswordValidation.error);
  }
  
  const nameValidation = validateName(name);
  if (!nameValidation.isValid && nameValidation.error) {
    errors.push(nameValidation.error);
  }
  
  if (phone) {
    const phoneValidation = validatePhone(phone);
    if (!phoneValidation.isValid && phoneValidation.error) {
      errors.push(phoneValidation.error);
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

// Real-time validation for individual fields
export function validateField(field: string, value: string, additionalValue?: string): FieldValidation {
  switch (field) {
    case 'email':
      return validateEmail(value);
    case 'password':
      return validatePassword(value);
    case 'confirmPassword':
      return validateConfirmPassword(additionalValue || '', value);
    case 'name':
      return validateName(value);
    case 'phone':
      return validatePhone(value);
    default:
      return { field, isValid: true };
  }
}