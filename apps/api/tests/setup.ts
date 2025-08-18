import { beforeAll, afterAll } from "vitest";

// Global test setup
beforeAll(async () => {
  // Set test environment variables
  process.env.NODE_ENV = "test";
  process.env.JWT_SECRET = "test-jwt-secret-key";
  process.env.DATABASE_URL =
    process.env.DATABASE_URL ||
    "postgresql://postgres:postgres@localhost:5432/yuyu_lolita";

  // Disable rate limiting in tests
  process.env.DISABLE_RATE_LIMITING = "true";

  // Mock SMS and email services
  process.env.SMS_MOCK = "true";
  process.env.EMAIL_MOCK = "true";

  console.log("🧪 Test environment initialized");
});

afterAll(async () => {
  console.log("🧪 Test cleanup completed");
});

// Mock external services for testing
export const mockServices = {
  sms: {
    send: async (phone: string, message: string) => ({
      success: true,
      messageId: "test-sms-" + Date.now(),
    }),
  },
  email: {
    send: async (email: string, subject: string, content: string) => ({
      success: true,
      messageId: "test-email-" + Date.now(),
    }),
  },
  payment: {
    process: async (amount: number, method: string) => ({
      success: true,
      transactionId: "test-payment-" + Date.now(),
    }),
  },
};
