/**
 * Comprehensive Validation Testing Suite
 * Tests enhanced validation functions for multi-auth support
 * Covers Russian phone numbers, email validation, and form validation
 */

import { describe, it, expect } from "vitest";
import {
  validateEmail,
  validatePhone,
  validatePassword,
  validateConfirmPassword,
  validateName,
  validateSMSCode,
  validateLoginForm,
  validateRegisterForm,
  normalizePhoneNumber,
  formatPhoneForDisplay,
  applyPhoneMask,
  getPasswordStrength,
  detectAuthMethod,
  createFormValidator,
} from "./validation-enhanced";

describe("Enhanced Validation Functions", () => {
  describe("Email Validation", () => {
    it("should validate correct email addresses", () => {
      const validEmails = [
        "test@example.com",
        "user.name@domain.co.uk",
        "user+tag@example.org",
        "тест@домен.рф",
        "user123@test-domain.com",
      ];

      validEmails.forEach(email => {
        const result = validateEmail(email, true);
        expect(result.isValid).toBe(true);
        expect(result.error).toBeUndefined();
      });
    });

    it("should reject invalid email addresses", () => {
      const invalidEmails = [
        "invalid-email",
        "@domain.com",
        "user@",
        "user space@domain.com",
        "user..double@domain.com",
        "",
        "a".repeat(250) + "@domain.com", // Too long
      ];

      invalidEmails.forEach(email => {
        const result = validateEmail(email, true);
        expect(result.isValid).toBe(false);
        expect(result.error).toBeDefined();
      });
    });

    it("should handle optional email validation", () => {
      const result = validateEmail("", false);
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it("should require email when marked as required", () => {
      const result = validateEmail("", true);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe("Email адрес обязателен");
    });
  });

  describe("Russian Phone Validation", () => {
    it("should validate correct Russian phone numbers", () => {
      const validPhones = [
        "+79991234567",
        "79991234567", 
        "89991234567",
        "9991234567",
        "+7 (999) 123-45-67",
        "8 (999) 123-45-67",
        "+7-999-123-45-67",
        "8-999-123-45-67",
      ];

      validPhones.forEach(phone => {
        const result = validatePhone(phone, true);
        expect(result.isValid).toBe(true, `Phone ${phone} should be valid`);
        expect(result.error).toBeUndefined();
      });
    });

    it("should reject invalid phone numbers", () => {
      const invalidPhones = [
        "123", // Too short
        "12345678901234567890", // Too long
        "+1234567890", // Not Russian
        "abcdefghij", // Non-numeric
        "+7 (123) 456-78-90", // Invalid Russian mobile operator
        "", // Empty when required
      ];

      invalidPhones.forEach(phone => {
        const result = validatePhone(phone, true);
        expect(result.isValid).toBe(false, `Phone ${phone} should be invalid`);
        expect(result.error).toBeDefined();
      });
    });

    it("should handle optional phone validation", () => {
      const result = validatePhone("", false);
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it("should require phone when marked as required", () => {
      const result = validatePhone("", true);
      expect(result.isValid).toBe(false);
      expect(result.error).toBe("Номер телефона обязателен");
    });

    it("should validate Russian mobile operators", () => {
      const validOperators = [
        "+79991234567", // МТС
        "+79001234567", // МТС  
        "+79911234567", // Билайн
        "+79261234567", // Билайн
        "+79161234567", // МТС Москва
        "+79771234567", // Tele2
      ];

      validOperators.forEach(phone => {
        const result = validatePhone(phone, true);
        expect(result.isValid).toBe(true, `Operator in ${phone} should be valid`);
      });
    });
  });

  describe("Phone Number Utilities", () => {
    it("should normalize different phone formats", () => {
      const testCases = [
        { input: "89991234567", expected: "+79991234567" },
        { input: "79991234567", expected: "+79991234567" },
        { input: "+79991234567", expected: "+79991234567" },
        { input: "9991234567", expected: "+79991234567" },
        { input: "+7 (999) 123-45-67", expected: "+79991234567" },
        { input: "8 (999) 123-45-67", expected: "+79991234567" },
      ];

      testCases.forEach(({ input, expected }) => {
        const result = normalizePhoneNumber(input);
        expect(result).toBe(expected);
      });
    });

    it("should format phone numbers for display", () => {
      const testCases = [
        { input: "+79991234567", expected: "+7 (999) 123-45-67" },
        { input: "79991234567", expected: "+7 (999) 123-45-67" },
        { input: "invalid", expected: "invalid" }, // Should return as-is for invalid
      ];

      testCases.forEach(({ input, expected }) => {
        const result = formatPhoneForDisplay(input);
        expect(result).toBe(expected);
      });
    });

    it("should apply phone input mask correctly", () => {
      const testCases = [
        { input: "7", expected: "+7" },
        { input: "79", expected: "+7 (9" },
        { input: "7999", expected: "+7 (999" },
        { input: "7999123", expected: "+7 (999) 123" },
        { input: "79991234", expected: "+7 (999) 123-4" },
        { input: "799912345", expected: "+7 (999) 123-45" },
        { input: "79991234567", expected: "+7 (999) 123-45-67" },
        { input: "89991234567", expected: "+7 (999) 123-45-67" },
      ];

      testCases.forEach(({ input, expected }) => {
        const result = applyPhoneMask(input);
        expect(result).toBe(expected);
      });
    });
  });

  describe("Password Validation", () => {
    it("should validate strong passwords", () => {
      const validPasswords = [
        "SecurePass123",
        "MyPassword1",
        "Test123456",
        "Пароль123",
        "ComplexP@ss1",
      ];

      validPasswords.forEach(password => {
        const result = validatePassword(password);
        expect(result.isValid).toBe(true, `Password "${password}" should be valid`);
        expect(result.error).toBeUndefined();
      });
    });

    it("should reject weak passwords", () => {
      const invalidPasswords = [
        "", // Empty
        "123", // Too short
        "password", // No numbers
        "12345678", // No letters
        "a".repeat(129), // Too long
      ];

      invalidPasswords.forEach(password => {
        const result = validatePassword(password);
        expect(result.isValid).toBe(false, `Password "${password}" should be invalid`);
        expect(result.error).toBeDefined();
      });
    });

    it("should calculate password strength correctly", () => {
      const testCases = [
        { password: "123", expected: { label: "Слабый", color: "text-red-600" } },
        { password: "password123", expected: { label: "Средний", color: "text-yellow-600" } },
        { password: "SecureP@ss123", expected: { label: "Надежный", color: "text-green-600" } },
        { password: "", expected: { label: "", color: "" } },
      ];

      testCases.forEach(({ password, expected }) => {
        const result = getPasswordStrength(password);
        expect(result.label).toBe(expected.label);
        expect(result.color).toBe(expected.color);
        expect(result.score).toBeGreaterThanOrEqual(0);
      });
    });
  });

  describe("Confirm Password Validation", () => {
    it("should validate matching passwords", () => {
      const result = validateConfirmPassword("password123", "password123");
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it("should reject non-matching passwords", () => {
      const result = validateConfirmPassword("password123", "different456");
      expect(result.isValid).toBe(false);
      expect(result.error).toBe("Пароли не совпадают");
    });

    it("should require confirm password", () => {
      const result = validateConfirmPassword("password123", "");
      expect(result.isValid).toBe(false);
      expect(result.error).toBe("Подтверждение пароля обязательно");
    });
  });

  describe("Name Validation", () => {
    it("should validate correct names", () => {
      const validNames = [
        "Иван",
        "Мария Петровна",
        "John Doe",
        "Анна-Мария",
        "Jean-Pierre",
        "Екатерина Великая",
      ];

      validNames.forEach(name => {
        const result = validateName(name);
        expect(result.isValid).toBe(true, `Name "${name}" should be valid`);
        expect(result.error).toBeUndefined();
      });
    });

    it("should reject invalid names", () => {
      const invalidNames = [
        "", // Empty
        "A", // Too short
        "A".repeat(101), // Too long
        "Name123", // Contains numbers
        "Name@domain", // Contains special chars
        "Name_Test", // Contains underscore
      ];

      invalidNames.forEach(name => {
        const result = validateName(name);
        expect(result.isValid).toBe(false, `Name "${name}" should be invalid`);
        expect(result.error).toBeDefined();
      });
    });
  });

  describe("SMS Code Validation", () => {
    it("should validate correct SMS codes", () => {
      const validCodes = ["123456", "000000", "999999"];

      validCodes.forEach(code => {
        const result = validateSMSCode(code);
        expect(result.isValid).toBe(true);
        expect(result.error).toBeUndefined();
      });
    });

    it("should reject invalid SMS codes", () => {
      const invalidCodes = [
        "", // Empty
        "123", // Too short
        "1234567", // Too long
        "12345a", // Contains letters
        "12 34 56", // Contains spaces
      ];

      invalidCodes.forEach(code => {
        const result = validateSMSCode(code);
        expect(result.isValid).toBe(false, `Code "${code}" should be invalid`);
        expect(result.error).toBeDefined();
      });
    });
  });

  describe("Multi-Auth Login Form Validation", () => {
    it("should validate email login form", () => {
      const result = validateLoginForm("email", "test@example.com", "password123");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should validate phone login form", () => {
      const result = validateLoginForm("phone", "+79991234567", "password123");
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject invalid email login", () => {
      const result = validateLoginForm("email", "invalid-email", "password123");
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors[0]).toContain("корректный email");
    });

    it("should reject invalid phone login", () => {
      const result = validateLoginForm("phone", "123", "password123");
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors[0]).toContain("10 цифр");
    });

    it("should reject weak password in login", () => {
      const result = validateLoginForm("email", "test@example.com", "");
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors[0]).toContain("Пароль обязателен");
    });
  });

  describe("Multi-Auth Registration Form Validation", () => {
    it("should validate complete email registration", () => {
      const result = validateRegisterForm(
        "email",
        "test@example.com",
        "SecurePass123",
        "SecurePass123",
        "Тест Пользователь",
        "+79991234567" // Optional phone
      );
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should validate complete phone registration", () => {
      const result = validateRegisterForm(
        "phone",
        "+79991234567",
        "SecurePass123",
        "SecurePass123",
        "Тест Пользователь",
        "test@example.com" // Optional email
      );
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should validate email registration without optional phone", () => {
      const result = validateRegisterForm(
        "email",
        "test@example.com",
        "SecurePass123",
        "SecurePass123",
        "Тест Пользователь"
      );
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should validate phone registration without optional email", () => {
      const result = validateRegisterForm(
        "phone",
        "+79991234567",
        "SecurePass123",
        "SecurePass123",
        "Тест Пользователь"
      );
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject registration with mismatched passwords", () => {
      const result = validateRegisterForm(
        "email",
        "test@example.com",
        "password123",
        "different456",
        "Тест Пользователь"
      );
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain("Пароли не совпадают");
    });

    it("should reject registration with invalid primary contact", () => {
      const result = validateRegisterForm(
        "email",
        "invalid-email",
        "SecurePass123",
        "SecurePass123",
        "Тест Пользователь"
      );
      expect(result.isValid).toBe(false);
      expect(result.errors.some(error => error.includes("корректный email"))).toBe(true);
    });

    it("should reject registration with invalid secondary contact", () => {
      const result = validateRegisterForm(
        "email",
        "test@example.com",
        "SecurePass123",
        "SecurePass123",
        "Тест Пользователь",
        "123" // Invalid phone
      );
      expect(result.isValid).toBe(false);
      expect(result.errors.some(error => error.includes("10 цифр"))).toBe(true);
    });

    it("should collect all validation errors", () => {
      const result = validateRegisterForm(
        "email",
        "invalid-email",
        "weak",
        "different",
        "" // Empty name
      );
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThanOrEqual(3); // At least email, password, and name errors
    });
  });

  describe("Auth Method Detection", () => {
    it("should detect email addresses", () => {
      const emails = [
        "test@example.com",
        "user.name@domain.co.uk",
        "тест@домен.рф",
      ];

      emails.forEach(email => {
        const result = detectAuthMethod(email);
        expect(result).toBe("email");
      });
    });

    it("should detect phone numbers", () => {
      const phones = [
        "79991234567",
        "+79991234567",
        "89991234567",
        "9991234567",
      ];

      phones.forEach(phone => {
        const result = detectAuthMethod(phone);
        expect(result).toBe("phone");
      });
    });

    it("should return unknown for ambiguous input", () => {
      const ambiguous = [
        "",
        "123",
        "abc",
        "test",
        "user",
      ];

      ambiguous.forEach(input => {
        const result = detectAuthMethod(input);
        expect(result).toBe("unknown");
      });
    });
  });

  describe("Form Validator Helper", () => {
    it("should create working form validator", () => {
      const validator = createFormValidator();

      // Test validation
      expect(validator.validate("email", "test@example.com")).toBe(true);
      expect(validator.validate("email", "invalid")).toBe(false);

      // Test error tracking
      expect(validator.hasErrors()).toBe(true);
      const errors = validator.getErrors();
      expect(errors.email).toBeDefined();

      // Test clearing errors
      validator.clearError("email");
      expect(validator.hasErrors()).toBe(false);

      // Test multiple errors
      validator.validate("email", "invalid");
      validator.validate("password", "");
      expect(Object.keys(validator.getErrors())).toHaveLength(2);

      // Test clear all
      validator.clearAllErrors();
      expect(validator.hasErrors()).toBe(false);
    });

    it("should handle field validation with additional parameters", () => {
      const validator = createFormValidator();

      // Test password confirmation
      expect(validator.validate("confirmPassword", "password123", "password123")).toBe(true);
      expect(validator.validate("confirmPassword", "different", "password123")).toBe(false);

      // Test required phone
      expect(validator.validate("phone", "", undefined, true)).toBe(false);
      expect(validator.validate("phone", "", undefined, false)).toBe(true);
    });
  });

  describe("Edge Cases and Error Handling", () => {
    it("should handle null and undefined inputs gracefully", () => {
      // @ts-expect-error - Testing runtime behavior
      expect(validateEmail(null, false).isValid).toBe(true);
      // @ts-expect-error - Testing runtime behavior
      expect(validatePhone(undefined, false).isValid).toBe(true);
      // @ts-expect-error - Testing runtime behavior
      expect(validatePassword(null).isValid).toBe(false);
    });

    it("should handle extreme input lengths", () => {
      const veryLongString = "a".repeat(10000);
      
      expect(validateEmail(veryLongString + "@domain.com", true).isValid).toBe(false);
      expect(validatePassword(veryLongString).isValid).toBe(false);
      expect(validateName(veryLongString).isValid).toBe(false);
    });

    it("should handle special Unicode characters", () => {
      // Russian characters in names
      expect(validateName("Владимир").isValid).toBe(true);
      expect(validateName("Екатерина Фёдоровна").isValid).toBe(true);
      
      // Emoji and special chars should be rejected
      expect(validateName("Test 😀").isValid).toBe(false);
      expect(validateName("Name™").isValid).toBe(false);
    });

    it("should handle various phone number edge cases", () => {
      // Leading/trailing spaces
      expect(validatePhone("  +79991234567  ", true).isValid).toBe(true);
      
      // Multiple formatting characters
      expect(validatePhone("+7--999--123--45--67", true).isValid).toBe(true);
      
      // Mixed characters
      expect(validatePhone("+7abc9991234567", true).isValid).toBe(false);
    });
  });
});