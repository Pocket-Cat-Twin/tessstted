import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import app from "../../src/index";
import { db } from "@yuyu/db";
import { users, orders } from "@yuyu/db";
import { eq } from "drizzle-orm";

describe("Critical User Journey E2E Tests", () => {
  let server: any;
  let testUser: any;
  let authToken: string;

  beforeAll(async () => {
    // Clean up test data
    await db.delete(orders).where(orders.customerEmail.like("%e2etest%"));
    await db.delete(users).where(users.email.like("%e2etest%"));

    // Start server for testing
    server = app.listen(0);
  });

  afterAll(async () => {
    // Clean up test data
    await db.delete(orders).where(orders.customerEmail.like("%e2etest%"));
    await db.delete(users).where(users.email.like("%e2etest%"));

    if (server) {
      server.close();
    }
  });

  describe("Complete User Registration and Login Journey", () => {
    it("should complete full registration flow", async () => {
      const testEmail = "user@e2etest.com";
      const testPhone = "+1234567890e2e";
      const testPassword = "Test123!@#";

      // Step 1: Register user
      const registrationResponse = await request(app.server)
        .post("/api/v1/auth/register")
        .send({
          email: testEmail,
          password: testPassword,
          name: "E2E Test User",
          phone: testPhone,
        })
        .expect("Content-Type", /json/)
        .expect(200);

      expect(registrationResponse.body.success).toBe(true);

      // Step 2: Verify user is created but not verified
      const user = await db.query.users.findFirst({
        where: eq(users.email, testEmail),
      });

      expect(user).toBeDefined();
      expect(user?.verified).toBe(false);
      testUser = user;
    });

    it("should allow login after registration", async () => {
      const loginResponse = await request(app.server)
        .post("/api/v1/auth/login")
        .send({
          email: "user@e2etest.com",
          password: "Test123!@#",
        })
        .expect("Content-Type", /json/)
        .expect(200);

      expect(loginResponse.body.success).toBe(true);
      expect(loginResponse.body.data?.token).toBeDefined();
      expect(loginResponse.body.data?.user?.id).toBe(testUser.id);

      authToken = loginResponse.body.data.token;
    });

    it("should access protected routes with valid token", async () => {
      const profileResponse = await request(app.server)
        .get("/api/v1/user/profile")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(profileResponse.body.success).toBe(true);
      expect(profileResponse.body.data?.user?.email).toBe("user@e2etest.com");
    });
  });

  describe("Complete Order Creation Journey", () => {
    it("should create order with correct free tier commission", async () => {
      const orderData = {
        nomerok: "E2E-ORDER-001",
        customerName: "E2E Test Customer",
        customerEmail: "customer@e2etest.com",
        customerPhone: "+1987654321e2e",
        itemName: "E2E Test Lolita Dress",
        itemUrl: "https://example.com/dress",
        itemPrice: 10000, // 100.00 RUB
        size: "M",
        color: "Pink",
        notes: "E2E test order",
      };

      const createOrderResponse = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(orderData)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(createOrderResponse.body.success).toBe(true);

      const createdOrder = createOrderResponse.body.data;
      expect(createdOrder?.nomerok).toBe(orderData.nomerok);
      expect(createdOrder?.userId).toBe(testUser.id);

      // Verify commission calculation for free tier (10%)
      const expectedCommission = Math.round(orderData.itemPrice * 0.1);
      expect(createdOrder?.commission).toBe(expectedCommission);
      expect(createdOrder?.finalPrice).toBe(
        orderData.itemPrice + expectedCommission,
      );
    });

    it("should list user orders", async () => {
      const ordersResponse = await request(app.server)
        .get("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(ordersResponse.body.success).toBe(true);
      const userOrders = ordersResponse.body.data?.filter(
        (order: any) => order.customerEmail === "customer@e2etest.com",
      );

      expect(userOrders?.length).toBeGreaterThan(0);
    });
  });

  describe("Profile Management Journey", () => {
    it("should update user profile information", async () => {
      const profileData = {
        name: "Updated E2E Test User",
        phone: "+1234567890updated",
      };

      const updateResponse = await request(app.server)
        .patch("/api/v1/user/profile")
        .set("Authorization", `Bearer ${authToken}`)
        .send(profileData)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(updateResponse.body.success).toBe(true);

      // Verify profile was updated
      const profileResponse = await request(app.server)
        .get("/api/v1/user/profile")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(profileResponse.body.data?.user?.name).toBe(profileData.name);
    });
  });

  describe("Error Handling Journey", () => {
    it("should handle duplicate email registration gracefully", async () => {
      const duplicateResponse = await request(app.server)
        .post("/api/v1/auth/register")
        .send({
          email: "user@e2etest.com", // Already registered
          password: "Test123!@#",
          name: "Duplicate User",
        })
        .expect("Content-Type", /json/)
        .expect(400);

      expect(duplicateResponse.body.success).toBe(false);
    });

    it("should handle unauthorized access to protected routes", async () => {
      const unauthorizedResponse = await request(app.server)
        .get("/api/v1/orders")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(unauthorizedResponse.body.success).toBe(false);
    });

    it("should handle invalid order data", async () => {
      const invalidOrderResponse = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send({
          nomerok: "", // Invalid: empty
          customerEmail: "invalid-email", // Invalid format
          itemPrice: -100, // Invalid: negative
        })
        .expect("Content-Type", /json/)
        .expect(400);

      expect(invalidOrderResponse.body.success).toBe(false);
    });
  });

  describe("Data Consistency Journey", () => {
    it("should maintain data consistency across related operations", async () => {
      // Get user's current order count
      const initialOrdersResponse = await request(app.server)
        .get("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .expect(200);

      const initialOrderCount = initialOrdersResponse.body.data?.length || 0;

      // Create new order
      const newOrderResponse = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send({
          nomerok: "E2E-CONSISTENCY-001",
          customerName: "Consistency Test",
          customerEmail: "consistency@e2etest.com",
          customerPhone: "+1999999999e2e",
          itemName: "Consistency Test Item",
          itemUrl: "https://example.com/consistency",
          itemPrice: 5000,
          size: "S",
          color: "Red",
        })
        .expect(200);

      expect(newOrderResponse.body.success).toBe(true);

      // Verify order count increased
      const finalOrdersResponse = await request(app.server)
        .get("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .expect(200);

      const finalOrderCount = finalOrdersResponse.body.data?.length || 0;
      expect(finalOrderCount).toBe(initialOrderCount + 1);

      // Verify order appears in database
      const dbOrder = await db.query.orders.findFirst({
        where: eq(orders.nomerok, "E2E-CONSISTENCY-001"),
      });

      expect(dbOrder).toBeDefined();
      expect(dbOrder?.userId).toBe(testUser.id);
      expect(dbOrder?.customerEmail).toBe("consistency@e2etest.com");
    });
  });
});
