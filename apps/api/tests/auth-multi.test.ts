/**
 * Comprehensive Multi-Auth Testing Suite
 * Tests both email and phone authentication flows
 * Enterprise-level test coverage with edge cases
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import { Elysia } from "elysia";
import { authEnhancedRoutes } from "../src/routes/auth-enhanced";
import { 
  db, 
  users, 
  verificationTokens, 
  verificationRateLimit,
  smsLogs,
  emailLogs,
  eq 
} from "@lolita-fashion/db";
import { 
  RegistrationMethod,
  normalizePhoneNumber,
  formatPhoneForDisplay 
} from "@lolita-fashion/shared";

// Test app setup
const testApp = new Elysia().use(authEnhancedRoutes);

describe("Enhanced Multi-Auth System", () => {
  beforeAll(async () => {
    // Set NODE_ENV to test
    process.env.NODE_ENV = "test";
    process.env.FRONTEND_URL = "http://localhost:5173";
    process.env.JWT_SECRET = "test-jwt-secret-key";
  });

  beforeEach(async () => {
    // Clean up test data before each test
    await db.delete(verificationRateLimit);
    await db.delete(verificationTokens);
    await db.delete(smsLogs);
    await db.delete(emailLogs);
    await db.delete(users);
  });

  afterAll(async () => {
    // Final cleanup
    await db.delete(verificationRateLimit);
    await db.delete(verificationTokens);
    await db.delete(smsLogs);
    await db.delete(emailLogs);
    await db.delete(users);
  });

  describe("Email Registration Flow", () => {
    it("should register user with valid email", async () => {
      const testUser = {
        registrationMethod: "email" as const,
        email: `test${Date.now()}@example.com`,
        password: "SecurePass123",
        name: "Тест Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.1",
            "user-agent": "test-agent"
          },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toContain("Регистрация успешна");
      expect(data.data.user.email).toBe(testUser.email);
      expect(data.data.user.registrationMethod).toBe("email");
      expect(data.data.requiresVerification).toBe(true);
      expect(data.data.verificationMethod).toBe("email");

      // Verify user in database
      const dbUser = await db.query.users.findFirst({
        where: eq(users.email, testUser.email),
      });
      expect(dbUser).toBeDefined();
      expect(dbUser!.registrationMethod).toBe(RegistrationMethod.EMAIL);
      expect(dbUser!.emailVerified).toBe(false);

      // Verify verification token created
      const verificationRecord = await db.query.verificationTokens.findFirst({
        where: eq(verificationTokens.userId, dbUser!.id),
      });
      expect(verificationRecord).toBeDefined();
      expect(verificationRecord!.type).toBe("email_registration");
      expect(verificationRecord!.email).toBe(testUser.email);
    });

    it("should register user with email and optional phone", async () => {
      const testUser = {
        registrationMethod: "email" as const,
        email: `test${Date.now()}@example.com`,
        phone: "+79991234567",
        password: "SecurePass123",
        name: "Тест Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.1"
          },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.data.user.email).toBe(testUser.email);
      expect(data.data.user.phone).toBe(formatPhoneForDisplay(testUser.phone));

      // Verify normalized phone in database
      const dbUser = await db.query.users.findFirst({
        where: eq(users.email, testUser.email),
      });
      expect(dbUser!.phone).toBe(normalizePhoneNumber(testUser.phone));
      expect(dbUser!.contactPhone).toBe(normalizePhoneNumber(testUser.phone));
    });

    it("should reject duplicate email registration", async () => {
      const testUser = {
        registrationMethod: "email" as const,
        email: "duplicate@example.com",
        password: "SecurePass123",
        name: "Первый Пользователь",
      };

      // First registration
      await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      // Duplicate registration
      const duplicateUser = {
        ...testUser,
        name: "Второй Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(duplicateUser),
        })
      );

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("email уже существует");
    });

    it("should reject invalid email format", async () => {
      const testUser = {
        registrationMethod: "email" as const,
        email: "invalid-email",
        password: "SecurePass123",
        name: "Тест Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("корректный email");
    });
  });

  describe("Phone Registration Flow", () => {
    it("should register user with valid Russian phone", async () => {
      const testUser = {
        registrationMethod: "phone" as const,
        phone: "89991234567",
        password: "SecurePass123",
        name: "Тест Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.1"
          },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toContain("SMS с кодом отправлен");
      expect(data.data.user.phone).toBe(formatPhoneForDisplay(normalizePhoneNumber(testUser.phone)));
      expect(data.data.user.registrationMethod).toBe("phone");
      expect(data.data.requiresVerification).toBe(true);
      expect(data.data.verificationMethod).toBe("phone");

      // Verify user in database
      const dbUser = await db.query.users.findFirst({
        where: eq(users.phone, normalizePhoneNumber(testUser.phone)),
      });
      expect(dbUser).toBeDefined();
      expect(dbUser!.registrationMethod).toBe(RegistrationMethod.PHONE);
      expect(dbUser!.phoneVerified).toBe(false);
      expect(dbUser!.phone).toBe(normalizePhoneNumber(testUser.phone));

      // Verify SMS verification token created
      const verificationRecord = await db.query.verificationTokens.findFirst({
        where: eq(verificationTokens.userId, dbUser!.id),
      });
      expect(verificationRecord).toBeDefined();
      expect(verificationRecord!.type).toBe("phone_registration");
      expect(verificationRecord!.phone).toBe(normalizePhoneNumber(testUser.phone));
      expect(verificationRecord!.code).toMatch(/^\d{6}$/);

      // Verify SMS log created
      const smsLog = await db.query.smsLogs.findFirst({
        where: eq(smsLogs.phone, normalizePhoneNumber(testUser.phone)),
      });
      expect(smsLog).toBeDefined();
      expect(smsLog!.status).toBe("sent");
    });

    it("should handle different Russian phone formats", async () => {
      const phoneFormats = [
        "89991234567",
        "79991234567", 
        "+79991234567",
        "9991234567",
      ];

      for (const phoneFormat of phoneFormats) {
        const testUser = {
          registrationMethod: "phone" as const,
          phone: phoneFormat,
          password: "SecurePass123",
          name: "Тест Пользователь",
        };

        const response = await testApp.handle(
          new Request("http://localhost/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(testUser),
          })
        );

        expect(response.status).toBe(201);
        const data = await response.json();
        expect(data.success).toBe(true);

        // All formats should normalize to +79991234567
        const dbUser = await db.query.users.findFirst({
          where: eq(users.phone, "+79991234567"),
        });
        expect(dbUser).toBeDefined();

        // Cleanup for next iteration
        await db.delete(users).where(eq(users.id, dbUser!.id));
        await db.delete(verificationTokens).where(eq(verificationTokens.userId, dbUser!.id));
      }
    });

    it("should reject invalid phone format", async () => {
      const testUser = {
        registrationMethod: "phone" as const,
        phone: "123", // Too short
        password: "SecurePass123",
        name: "Тест Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("10 цифр");
    });

    it("should reject duplicate phone registration", async () => {
      const phone = "89991234567";
      const testUser = {
        registrationMethod: "phone" as const,
        phone,
        password: "SecurePass123",
        name: "Первый Пользователь",
      };

      // First registration
      await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      // Duplicate registration with different format
      const duplicateUser = {
        registrationMethod: "phone" as const,
        phone: "+79991234567", // Different format, same number
        password: "SecurePass123",
        name: "Второй Пользователь",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(duplicateUser),
        })
      );

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("телефоном уже существует");
    });
  });

  describe("Multi-Auth Login Flow", () => {
    beforeEach(async () => {
      // Create test users for login tests
      const emailUser = {
        email: "login-test@example.com",
        password: "$2a$12$kF1z8qGQZzXJ5KvLx8xDseq8rKjX9I4ZqE8zYjJ6v4zGlMQKU5OoS", // "SecurePass123"
        name: "Email User",
        registrationMethod: RegistrationMethod.EMAIL,
        status: "active" as const,
        role: "user" as const,
        emailVerified: true,
        phoneVerified: false,
      };

      const phoneUser = {
        phone: "+79991234567",
        password: "$2a$12$kF1z8qGQZzXJ5KvLx8xDseq8rKjX9I4ZqE8zYjJ6v4zGlMQKU5OoS", // "SecurePass123"
        name: "Phone User",
        registrationMethod: RegistrationMethod.PHONE,
        status: "active" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: true,
      };

      await db.insert(users).values([emailUser, phoneUser]);
    });

    it("should login with email credentials", async () => {
      const loginData = {
        loginMethod: "email" as const,
        email: "login-test@example.com",
        password: "SecurePass123",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/login", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.1"
          },
          body: JSON.stringify(loginData),
        })
      );

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toBe("Успешный вход в систему");
      expect(data.data.user.email).toBe(loginData.email);
      expect(data.data.token).toBeDefined();
    });

    it("should login with phone credentials", async () => {
      const loginData = {
        loginMethod: "phone" as const,
        phone: "89991234567", // Different format
        password: "SecurePass123",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/login", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.1"
          },
          body: JSON.stringify(loginData),
        })
      );

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toBe("Успешный вход в систему");
      expect(data.data.user.phone).toBe(formatPhoneForDisplay("+79991234567"));
      expect(data.data.token).toBeDefined();
    });

    it("should support legacy email-only login", async () => {
      const loginData = {
        email: "login-test@example.com",
        password: "SecurePass123",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(loginData),
        })
      );

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.data.user.email).toBe(loginData.email);
    });

    it("should reject invalid credentials", async () => {
      const loginData = {
        loginMethod: "email" as const,
        email: "login-test@example.com",
        password: "WrongPassword",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(loginData),
        })
      );

      expect(response.status).toBe(401);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toBe("Неверные данные для входа");
    });
  });

  describe("Email Verification", () => {
    it("should verify email with valid token", async () => {
      // Create user and verification token
      const [user] = await db.insert(users).values({
        email: "verify-test@example.com",
        password: "hashedPassword",
        name: "Test User",
        registrationMethod: RegistrationMethod.EMAIL,
        status: "pending" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: false,
      }).returning();

      const verificationToken = "test-verification-token";
      await db.insert(verificationTokens).values({
        userId: user.id,
        type: "email_registration",
        email: user.email!,
        token: verificationToken,
        code: "123456",
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        status: "pending",
      });

      const response = await testApp.handle(
        new Request("http://localhost/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: verificationToken }),
        })
      );

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toBe("Email успешно подтвержден");

      // Verify user status updated
      const updatedUser = await db.query.users.findFirst({
        where: eq(users.id, user.id),
      });
      expect(updatedUser!.emailVerified).toBe(true);
      expect(updatedUser!.status).toBe("active");
    });

    it("should reject expired verification token", async () => {
      const [user] = await db.insert(users).values({
        email: "verify-expired@example.com",
        password: "hashedPassword",
        name: "Test User",
        registrationMethod: RegistrationMethod.EMAIL,
        status: "pending" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: false,
      }).returning();

      const expiredToken = "expired-verification-token";
      await db.insert(verificationTokens).values({
        userId: user.id,
        type: "email_registration",
        email: user.email!,
        token: expiredToken,
        code: "123456",
        expiresAt: new Date(Date.now() - 1000), // Expired
        status: "pending",
      });

      const response = await testApp.handle(
        new Request("http://localhost/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: expiredToken }),
        })
      );

      expect(response.status).toBe(404);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("истекший токен");
    });
  });

  describe("Phone Verification", () => {
    it("should verify phone with correct SMS code", async () => {
      const [user] = await db.insert(users).values({
        phone: "+79991234567",
        password: "hashedPassword",
        name: "Test User",
        registrationMethod: RegistrationMethod.PHONE,
        status: "pending" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: false,
      }).returning();

      const verificationToken = "test-phone-token";
      const verificationCode = "123456";
      await db.insert(verificationTokens).values({
        userId: user.id,
        type: "phone_registration",
        phone: user.phone!,
        token: verificationToken,
        code: verificationCode,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        status: "pending",
        attemptCount: 0,
        maxAttempts: 3,
      });

      const response = await testApp.handle(
        new Request("http://localhost/auth/verify-phone", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            token: verificationToken,
            code: verificationCode
          }),
        })
      );

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toBe("Телефон успешно подтвержден");

      // Verify user status updated
      const updatedUser = await db.query.users.findFirst({
        where: eq(users.id, user.id),
      });
      expect(updatedUser!.phoneVerified).toBe(true);
      expect(updatedUser!.status).toBe("active");
    });

    it("should reject incorrect SMS code and increment attempt count", async () => {
      const [user] = await db.insert(users).values({
        phone: "+79991234567",
        password: "hashedPassword",
        name: "Test User",
        registrationMethod: RegistrationMethod.PHONE,
        status: "pending" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: false,
      }).returning();

      const verificationToken = "test-phone-token";
      const correctCode = "123456";
      const [verificationRecord] = await db.insert(verificationTokens).values({
        userId: user.id,
        type: "phone_registration",
        phone: user.phone!,
        token: verificationToken,
        code: correctCode,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        status: "pending",
        attemptCount: 0,
        maxAttempts: 3,
      }).returning();

      const response = await testApp.handle(
        new Request("http://localhost/auth/verify-phone", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            token: verificationToken,
            code: "654321" // Wrong code
          }),
        })
      );

      expect(response.status).toBe(401);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toBe("Неверный код подтверждения");

      // Verify attempt count incremented
      const updatedRecord = await db.query.verificationTokens.findFirst({
        where: eq(verificationTokens.id, verificationRecord.id),
      });
      expect(updatedRecord!.attemptCount).toBe(1);
    });

    it("should block verification after max attempts", async () => {
      const [user] = await db.insert(users).values({
        phone: "+79991234567",
        password: "hashedPassword",
        name: "Test User",
        registrationMethod: RegistrationMethod.PHONE,
        status: "pending" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: false,
      }).returning();

      const verificationToken = "test-phone-token";
      await db.insert(verificationTokens).values({
        userId: user.id,
        type: "phone_registration",
        phone: user.phone!,
        token: verificationToken,
        code: "123456",
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        status: "pending",
        attemptCount: 3, // Already at max
        maxAttempts: 3,
      });

      const response = await testApp.handle(
        new Request("http://localhost/auth/verify-phone", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            token: verificationToken,
            code: "123456"
          }),
        })
      );

      expect(response.status).toBe(401);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toBe("Превышено максимальное количество попыток");
    });
  });

  describe("Rate Limiting", () => {
    it("should rate limit registration attempts", async () => {
      const testUser = {
        registrationMethod: "email" as const,
        email: "rate-limit@example.com",
        password: "SecurePass123",
        name: "Rate Limit Test",
      };

      // Make 3 registration attempts (should reach limit)
      for (let i = 0; i < 3; i++) {
        await testApp.handle(
          new Request("http://localhost/auth/register", {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              "x-forwarded-for": "192.168.1.100"
            },
            body: JSON.stringify({
              ...testUser,
              email: `rate-limit-${i}@example.com`
            }),
          })
        );
      }

      // 4th attempt should be rate limited
      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.100"
          },
          body: JSON.stringify({
            ...testUser,
            email: "rate-limit-4@example.com"
          }),
        })
      );

      expect(response.status).toBe(429);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.error).toBe("RATE_LIMITED");
      expect(data.message).toContain("Слишком много попыток");
    });

    it("should rate limit login attempts", async () => {
      // Create test user
      await db.insert(users).values({
        email: "login-rate-limit@example.com",
        password: "$2a$12$kF1z8qGQZzXJ5KvLx8xDseq8rKjX9I4ZqE8zYjJ6v4zGlMQKU5OoS",
        name: "Rate Limit User",
        registrationMethod: RegistrationMethod.EMAIL,
        status: "active" as const,
        role: "user" as const,
        emailVerified: true,
        phoneVerified: false,
      });

      const loginData = {
        loginMethod: "email" as const,
        email: "login-rate-limit@example.com",
        password: "WrongPassword",
      };

      // Make 5 failed login attempts
      for (let i = 0; i < 5; i++) {
        await testApp.handle(
          new Request("http://localhost/auth/login", {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              "x-forwarded-for": "192.168.1.200"
            },
            body: JSON.stringify(loginData),
          })
        );
      }

      // 6th attempt should be rate limited
      const response = await testApp.handle(
        new Request("http://localhost/auth/login", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "x-forwarded-for": "192.168.1.200"
          },
          body: JSON.stringify(loginData),
        })
      );

      expect(response.status).toBe(429);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.error).toBe("RATE_LIMITED");
      expect(data.message).toContain("Слишком много попыток входа");
    });
  });

  describe("Cross-Method Validation", () => {
    it("should prevent phone registration with existing email contact", async () => {
      // Create email user first
      await db.insert(users).values({
        email: "existing@example.com",
        password: "hashedPassword",
        name: "Existing Email User",
        registrationMethod: RegistrationMethod.EMAIL,
        status: "active" as const,
        role: "user" as const,
        emailVerified: true,
        phoneVerified: false,
      });

      // Try to register with phone using same email as contact
      const testUser = {
        registrationMethod: "phone" as const,
        phone: "+79991234567",
        email: "existing@example.com", // Same email
        password: "SecurePass123",
        name: "Phone User",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("email уже существует");
    });

    it("should prevent email registration with existing phone contact", async () => {
      // Create phone user first
      await db.insert(users).values({
        phone: "+79991234567",
        password: "hashedPassword",
        name: "Existing Phone User",
        registrationMethod: RegistrationMethod.PHONE,
        status: "active" as const,
        role: "user" as const,
        emailVerified: false,
        phoneVerified: true,
      });

      // Try to register with email using same phone as contact
      const testUser = {
        registrationMethod: "email" as const,
        email: "test@example.com",
        phone: "89991234567", // Same phone, different format
        password: "SecurePass123",
        name: "Email User",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(data.success).toBe(false);
      expect(data.message).toContain("телефоном уже существует");
    });
  });

  describe("Data Integrity", () => {
    it("should maintain referential integrity between users and verification tokens", async () => {
      const testUser = {
        registrationMethod: "email" as const,
        email: "integrity-test@example.com",
        password: "SecurePass123",
        name: "Integrity Test",
      };

      const response = await testApp.handle(
        new Request("http://localhost/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(201);

      // Verify user and token are linked
      const dbUser = await db.query.users.findFirst({
        where: eq(users.email, testUser.email),
      });
      expect(dbUser).toBeDefined();

      const verificationRecord = await db.query.verificationTokens.findFirst({
        where: eq(verificationTokens.userId, dbUser!.id),
      });
      expect(verificationRecord).toBeDefined();
      expect(verificationRecord!.userId).toBe(dbUser!.id);
    });

    it("should properly normalize and store phone numbers", async () => {
      const phoneVariations = [
        { input: "89991234567", expected: "+79991234567" },
        { input: "+79991234567", expected: "+79991234567" },
        { input: "79991234567", expected: "+79991234567" },
        { input: "9991234567", expected: "+79991234567" },
      ];

      for (const { input, expected } of phoneVariations) {
        const testUser = {
          registrationMethod: "phone" as const,
          phone: input,
          password: "SecurePass123",
          name: "Phone Normalization Test",
        };

        const response = await testApp.handle(
          new Request("http://localhost/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(testUser),
          })
        );

        expect(response.status).toBe(201);

        // Verify normalized storage
        const dbUser = await db.query.users.findFirst({
          where: eq(users.phone, expected),
        });
        expect(dbUser).toBeDefined();
        expect(dbUser!.phone).toBe(expected);
        expect(dbUser!.contactPhone).toBe(expected);

        // Cleanup
        await db.delete(users).where(eq(users.id, dbUser!.id));
        await db.delete(verificationTokens).where(eq(verificationTokens.userId, dbUser!.id));
      }
    });
  });
});