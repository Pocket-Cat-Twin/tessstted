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
    send: async (_phone: string, _message: string) => ({
      success: true,
      messageId: "test-sms-" + Date.now(),
    }),
  },
  email: {
    send: async (_email: string, _subject: string, _content: string) => ({
      success: true,
      messageId: "test-email-" + Date.now(),
    }),
  },
  payment: {
    process: async (_amount: number, _method: string) => ({
      success: true,
      transactionId: "test-payment-" + Date.now(),
    }),
  },
};
