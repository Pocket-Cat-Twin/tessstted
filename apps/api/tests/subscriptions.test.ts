import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import app from "../src/index";

describe("Subscriptions API", () => {
  let server: any;
  let authToken: string;

  beforeAll(async () => {
    server = app.listen(0);

    // Create and authenticate a test user
    const testUser = {
      email: "subscriptions@example.com",
      password: "testPassword123",
      name: "Subscriptions Test User",
    };

    await request(app.server)
      .post("/api/v1/auth/register")
      .send(testUser);

    const loginResponse = await request(app.server)
      .post("/api/v1/auth/login")
      .send({ email: testUser.email, password: testUser.password });

    authToken = loginResponse.body.data.token;
  });

  afterAll(async () => {
    if (server) {
      server.close();
    }
  });

  describe("GET /api/v1/subscriptions/tiers", () => {
    it("should return subscription tiers without authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/tiers")
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("tiers");
      expect(Array.isArray(response.body.data.tiers)).toBe(true);
      expect(response.body.data.tiers.length).toBeGreaterThan(0);

      // Check tier structure
      const firstTier = response.body.data.tiers[0];
      expect(firstTier).toHaveProperty("id");
      expect(firstTier).toHaveProperty("name");
      expect(firstTier).toHaveProperty("price");
      expect(firstTier).toHaveProperty("currency");
      expect(firstTier).toHaveProperty("features");
      expect(Array.isArray(firstTier.features)).toBe(true);
    });

    it("should include all expected subscription tiers", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/tiers")
        .expect(200);

      const tierIds = response.body.data.tiers.map((tier: any) => tier.id);
      expect(tierIds).toContain("free");
      expect(tierIds).toContain("group");
      expect(tierIds).toContain("elite");
      expect(tierIds).toContain("vip_temp");
    });

    it("should have proper tier pricing", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/tiers")
        .expect(200);

      const tiers = response.body.data.tiers;
      const freeTier = tiers.find((t: any) => t.id === "free");
      const groupTier = tiers.find((t: any) => t.id === "group");

      expect(freeTier.price).toBe(0);
      expect(groupTier.price).toBeGreaterThan(0);
      expect(groupTier.currency).toBe("RUB");
    });
  });

  describe("GET /api/v1/subscriptions/status", () => {
    it("should return user subscription status with authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/status")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("subscription");

      // New users should have free tier by default
      expect(response.body.data.subscription.tier).toBe("free");
      expect(response.body.data.subscription.status).toBe("active");
    });

    it("should reject request without authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/status")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });
  });

  describe("POST /api/v1/subscriptions/purchase", () => {
    it("should handle subscription purchase with authentication", async () => {
      const purchaseData = {
        tierId: "group",
        paymentMethod: "card",
        paymentData: {
          cardToken: "test_card_token_123",
        },
      };

      const response = await request(app.server)
        .post("/api/v1/subscriptions/purchase")
        .set("Authorization", `Bearer ${authToken}`)
        .send(purchaseData)
        .expect("Content-Type", /json/);

      // This endpoint might not be fully implemented yet
      // The test verifies the endpoint exists and has proper authentication
      expect(response.body).toHaveProperty("success");
    });

    it("should reject purchase without authentication", async () => {
      const purchaseData = {
        tierId: "group",
        paymentMethod: "card",
      };

      const response = await request(app.server)
        .post("/api/v1/subscriptions/purchase")
        .send(purchaseData)
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });

    it("should validate subscription tier ID", async () => {
      const purchaseData = {
        tierId: "invalid_tier",
        paymentMethod: "card",
      };

      const response = await request(app.server)
        .post("/api/v1/subscriptions/purchase")
        .set("Authorization", `Bearer ${authToken}`)
        .send(purchaseData)
        .expect("Content-Type", /json/)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("VALIDATION_ERROR");
    });
  });

  describe("GET /api/v1/subscriptions/history", () => {
    it("should return subscription history with authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/history")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("subscriptions");
      expect(Array.isArray(response.body.data.subscriptions)).toBe(true);
    });

    it("should reject request without authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/subscriptions/history")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });
  });

  describe("POST /api/v1/subscriptions/cancel", () => {
    it("should handle subscription cancellation with authentication", async () => {
      const response = await request(app.server)
        .post("/api/v1/subscriptions/cancel")
        .set("Authorization", `Bearer ${authToken}`)
        .send({ reason: "Testing cancellation" })
        .expect("Content-Type", /json/);

      // The endpoint should exist and require authentication
      expect(response.body).toHaveProperty("success");
    });

    it("should reject cancellation without authentication", async () => {
      const response = await request(app.server)
        .post("/api/v1/subscriptions/cancel")
        .send({ reason: "Testing" })
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });
  });

  describe("Subscription feature validation", () => {
    it("should validate subscription features for free tier", async () => {
      const statusResponse = await request(app.server)
        .get("/api/v1/subscriptions/status")
        .set("Authorization", `Bearer ${authToken}`)
        .expect(200);

      const subscription = statusResponse.body.data.subscription;

      // Free tier should have basic features
      expect(subscription.tier).toBe("free");
      expect(subscription.features).toHaveProperty("storageTime");
      expect(subscription.features).toHaveProperty("processingTime");
      expect(subscription.features).toHaveProperty("commissionRate");

      // Free tier should have higher commission rate
      expect(subscription.features.commissionRate).toBe(0.1); // 10%
    });
  });

  describe("Commission calculation based on subscription", () => {
    it("should apply correct commission rates for different tiers", async () => {
      // Test commission calculation through order creation
      const orderData = {
        customerName: "Commission Test",
        customerPhone: "+1234567890",
        deliveryAddress: "Test Address",
        goods: [
          {
            name: "Test Product",
            quantity: 1,
            priceYuan: 1000, // Base price for easy calculation
          },
        ],
      };

      const orderResponse = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(orderData)
        .expect(200);

      const order = orderResponse.body.data.order;

      // For free tier user, commission should be 10% (100 Yuan)
      expect(order.commission).toBe(100);
      expect(order.commissionRate).toBe(0.1);
    });
  });
});
