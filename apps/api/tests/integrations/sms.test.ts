import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import { smsService } from "../../src/services/sms";
import { db, smsLogs } from "@lolita-fashion/db";

// Mock external SMS provider
vi.mock("../../src/services/sms", async () => {
  const actual = (await vi.importActual("../../src/services/sms")) as any;
  return {
    ...actual,
    // Mock the external API call but keep the internal logic
    sendSMSViaProvider: vi
      .fn()
      .mockImplementation(async (phone: string, _message: string) => {
        // Simulate different provider responses
        if (phone.includes("fail")) {
          throw new Error("SMS provider error");
        }
        if (phone.includes("invalid")) {
          return {
            success: false,
            error: "Invalid phone number",
            providerId: null,
          };
        }
        return {
          success: true,
          providerId: "mock_provider_id_" + Date.now(),
          cost: "0.50",
        };
      }),
  };
});

describe("SMS Integration Tests", () => {
  beforeAll(async () => {
    // Set up test environment
    process.env.SMS_PROVIDER = "mock";
    process.env.SMS_API_KEY = "test_api_key";
  });

  afterAll(async () => {
    // Clean up test SMS logs
    await db.delete(smsLogs).where(smsLogs.phone.like("%test%"));
  });

  describe("sendSMS", () => {
    it("should send SMS successfully and log the transaction", async () => {
      const testPhone = "+1234567890test";
      const testMessage = "Test SMS message";

      const result = await smsService.sendSMS(testPhone, testMessage, "test");

      expect(result.success).toBe(true);
      expect(result.providerId).toBeDefined();
      expect(result.messageId).toBeDefined();

      // Verify SMS log was created
      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.phone, testPhone),
      });

      expect(logEntry).toBeDefined();
      expect(logEntry?.phone).toBe(testPhone);
      expect(logEntry?.message).toBe(testMessage);
      expect(logEntry?.status).toBe("sent");
      expect(logEntry?.provider).toBe("mock");
    });

    it("should handle SMS provider failures gracefully", async () => {
      const testPhone = "+1234567890fail";
      const testMessage = "This SMS should fail";

      const result = await smsService.sendSMS(testPhone, testMessage, "test");

      expect(result.success).toBe(false);
      expect(result.error).toContain("SMS provider error");

      // Verify failed SMS log was created
      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.phone, testPhone),
      });

      expect(logEntry).toBeDefined();
      expect(logEntry?.status).toBe("failed");
      expect(logEntry?.statusMessage).toContain("SMS provider error");
    });

    it("should validate phone numbers before sending", async () => {
      const invalidPhone = "invalid_phone";
      const testMessage = "Test message";

      const result = await smsService.sendSMS(
        invalidPhone,
        testMessage,
        "test",
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain("Invalid phone number");
    });

    it("should handle rate limiting for SMS sending", async () => {
      const testPhone = "+1234567890rate_limit";
      const testMessage = "Rate limit test";

      // Send multiple SMS in quick succession
      const promises = Array(10)
        .fill(null)
        .map(() =>
          smsService.sendSMS(testPhone, testMessage, "rate_limit_test"),
        );

      const results = await Promise.all(promises);

      // At least some should succeed
      const successCount = results.filter((r) => r.success).length;
      expect(successCount).toBeGreaterThan(0);

      // Some might be rate limited
      const rateLimitedCount = results.filter(
        (r) => !r.success && r.error?.includes("rate limit"),
      ).length;

      // Either all succeed (if no rate limiting) or some are rate limited
      expect(successCount + rateLimitedCount).toBe(10);
    });
  });

  describe("sendVerificationSMS", () => {
    it("should send verification SMS with proper formatting", async () => {
      const testPhone = "+1234567890verification";
      const verificationCode = "123456";

      const result = await smsService.sendVerificationSMS(
        testPhone,
        verificationCode,
      );

      expect(result.success).toBe(true);

      // Verify the message contains the verification code
      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.phone, testPhone),
      });

      expect(logEntry?.message).toContain(verificationCode);
      expect(logEntry?.message).toContain("verification");
    });

    it("should generate proper verification code format", async () => {
      const testPhone = "+1234567890format_test";

      const result = await smsService.sendVerificationSMS(testPhone);

      expect(result.success).toBe(true);
      expect(result.code).toBeDefined();
      expect(result.code).toMatch(/^\d{6}$/); // 6-digit code

      // Verify log contains the generated code
      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.phone, testPhone),
      });

      expect(logEntry?.message).toContain(result.code!);
    });
  });

  describe("SMS templates", () => {
    it("should format order notification SMS correctly", async () => {
      const testPhone = "+1234567890order";
      const orderData = {
        nomerok: "TEST123456",
        status: "processing",
        customerName: "John Doe",
      };

      const result = await smsService.sendOrderNotificationSMS(
        testPhone,
        orderData,
      );

      expect(result.success).toBe(true);

      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.phone, testPhone),
      });

      expect(logEntry?.message).toContain(orderData.nomerok);
      expect(logEntry?.message).toContain(orderData.status);
    });

    it("should format subscription notification SMS correctly", async () => {
      const testPhone = "+1234567890subscription";
      const subscriptionData = {
        tier: "premium",
        expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days from now
      };

      const result = await smsService.sendSubscriptionNotificationSMS(
        testPhone,
        subscriptionData,
      );

      expect(result.success).toBe(true);

      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.phone, testPhone),
      });

      expect(logEntry?.message).toContain(subscriptionData.tier);
      expect(logEntry?.message).toContain("expires");
    });
  });

  describe("SMS delivery tracking", () => {
    it("should update SMS status when delivery confirmation is received", async () => {
      const testPhone = "+1234567890delivery";
      const testMessage = "Delivery tracking test";

      const result = await smsService.sendSMS(
        testPhone,
        testMessage,
        "delivery_test",
      );
      expect(result.success).toBe(true);

      // Simulate delivery confirmation webhook
      await smsService.updateSMSStatus(result.providerId!, "delivered");

      // Verify status was updated
      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.providerId, result.providerId!),
      });

      expect(logEntry?.status).toBe("delivered");
      expect(logEntry?.deliveredAt).toBeDefined();
    });

    it("should handle delivery failures", async () => {
      const testPhone = "+1234567890delivery_fail";
      const testMessage = "Delivery failure test";

      const result = await smsService.sendSMS(
        testPhone,
        testMessage,
        "delivery_fail_test",
      );
      expect(result.success).toBe(true);

      // Simulate delivery failure webhook
      await smsService.updateSMSStatus(
        result.providerId!,
        "failed",
        "Invalid number",
      );

      // Verify status was updated
      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.providerId, result.providerId!),
      });

      expect(logEntry?.status).toBe("failed");
      expect(logEntry?.statusMessage).toBe("Invalid number");
      expect(logEntry?.failedAt).toBeDefined();
    });
  });

  describe("SMS cost tracking", () => {
    it("should track SMS costs correctly", async () => {
      const testPhone = "+1234567890cost";
      const testMessage = "Cost tracking test";

      const result = await smsService.sendSMS(
        testPhone,
        testMessage,
        "cost_test",
      );
      expect(result.success).toBe(true);

      const logEntry = await db.query.smsLogs.findFirst({
        where: (table, { eq }) => eq(table.providerId, result.providerId!),
      });

      expect(logEntry?.cost).toBeDefined();
      expect(parseFloat(logEntry!.cost!)).toBeGreaterThan(0);
    });

    it("should calculate total SMS costs for a period", async () => {
      const testPhones = [
        "+1234567890cost1",
        "+1234567890cost2",
        "+1234567890cost3",
      ];

      // Send multiple SMS
      for (const phone of testPhones) {
        await smsService.sendSMS(
          phone,
          "Cost calculation test",
          "cost_calculation",
        );
      }

      // Calculate total cost for today
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      const totalCost = await smsService.calculateSMSCostForPeriod(
        today,
        new Date(),
      );

      expect(totalCost).toBeGreaterThan(0);
      expect(totalCost).toBe(testPhones.length * 0.5); // Mock cost is 0.50 per SMS
    });
  });
});
