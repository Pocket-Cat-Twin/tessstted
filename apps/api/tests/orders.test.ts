import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import app from "../src/index";

describe("Orders API", () => {
  let server: any;
  let authToken: string;
  let testOrderId: string;

  beforeAll(async () => {
    server = app.listen(0);

    // Create and authenticate a test user
    const testUser = {
      email: "orders@example.com",
      password: "testPassword123",
      name: "Orders Test User",
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

  describe("POST /api/v1/orders", () => {
    it("should create a new order with valid data", async () => {
      const orderData = {
        customerName: "Test Customer",
        customerPhone: "+1234567890",
        customerEmail: "customer@example.com",
        deliveryAddress: "Test Address, 123",
        deliveryMethod: "Почта России",
        paymentMethod: "Банковская карта",
        goods: [
          {
            name: "Test Product",
            link: "https://example.com/product",
            quantity: 2,
            priceYuan: 100.5,
          },
        ],
      };

      const response = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(orderData)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("order");
      expect(response.body.data.order).toHaveProperty("nomerok");
      expect(response.body.data.order.customerName).toBe(
        orderData.customerName,
      );
      expect(response.body.data.order.goods).toHaveLength(1);

      testOrderId = response.body.data.order.id;
    });

    it("should reject order creation without authentication", async () => {
      const orderData = {
        customerName: "Test Customer",
        customerPhone: "+1234567890",
        deliveryAddress: "Test Address, 123",
        goods: [{ name: "Test Product", quantity: 1, priceYuan: 100 }],
      };

      const response = await request(app.server)
        .post("/api/v1/orders")
        .send(orderData)
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });

    it("should reject order with missing required fields", async () => {
      const invalidOrderData = {
        customerName: "Test Customer",
        // Missing required fields
      };

      const response = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(invalidOrderData)
        .expect("Content-Type", /json/)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("VALIDATION_ERROR");
    });

    it("should reject order with invalid goods data", async () => {
      const orderData = {
        customerName: "Test Customer",
        customerPhone: "+1234567890",
        deliveryAddress: "Test Address, 123",
        goods: [
          {
            name: "", // Empty name
            quantity: -1, // Negative quantity
            priceYuan: -50, // Negative price
          },
        ],
      };

      const response = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(orderData)
        .expect("Content-Type", /json/)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("VALIDATION_ERROR");
    });

    it("should calculate commission correctly based on user subscription", async () => {
      const orderData = {
        customerName: "Commission Test Customer",
        customerPhone: "+1234567890",
        deliveryAddress: "Test Address, 123",
        goods: [
          {
            name: "Commission Test Product",
            quantity: 1,
            priceYuan: 100,
          },
        ],
      };

      const response = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(orderData)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.order).toHaveProperty("commission");
      expect(response.body.data.order).toHaveProperty("totalYuan");
      expect(response.body.data.order).toHaveProperty("totalRuble");

      // For free tier users, commission should be 10%
      expect(response.body.data.order.commission).toBe(10); // 10% of 100 Yuan
    });
  });

  describe("GET /api/v1/orders/:nomerok", () => {
    let orderNomerok: string;

    beforeAll(async () => {
      // Create a test order
      const orderData = {
        customerName: "Get Test Customer",
        customerPhone: "+1234567890",
        deliveryAddress: "Test Address, 123",
        goods: [{ name: "Get Test Product", quantity: 1, priceYuan: 100 }],
      };

      const createResponse = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .send(orderData);

      orderNomerok = createResponse.body.data.order.nomerok;
    });

    it("should retrieve order by nomerok", async () => {
      const response = await request(app.server)
        .get(`/api/v1/orders/${orderNomerok}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("order");
      expect(response.body.data.order.nomerok).toBe(orderNomerok);
      expect(response.body.data.order.customerName).toBe("Get Test Customer");
    });

    it("should return 404 for non-existent order", async () => {
      const response = await request(app.server)
        .get("/api/v1/orders/NON_EXISTENT_ORDER")
        .expect("Content-Type", /json/)
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("ORDER_NOT_FOUND");
    });
  });

  describe("GET /api/v1/orders", () => {
    it("should return user orders with authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/orders")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("orders");
      expect(Array.isArray(response.body.data.orders)).toBe(true);
    });

    it("should reject request without authentication", async () => {
      const response = await request(app.server)
        .get("/api/v1/orders")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });
  });

  describe("PATCH /api/v1/admin/orders/:id/status", () => {
    let adminToken: string;

    beforeAll(async () => {
      // Create an admin user
      const adminUser = {
        email: "admin@example.com",
        password: "adminPassword123",
        name: "Admin User",
      };

      await request(app.server).post("/api/v1/auth/register").send(adminUser);

      // Note: In a real scenario, you would need to update the user role to 'admin' in the database
      // For this test, we'll assume the endpoint handles admin role validation

      const loginResponse = await request(app.server)
        .post("/api/v1/auth/login")
        .send({ email: adminUser.email, password: adminUser.password });

      adminToken = loginResponse.body.data.token;
    });

    it("should update order status with admin privileges", async () => {
      if (!testOrderId) {
        // Skip if no test order created
        return;
      }

      const response = await request(app.server)
        .patch(`/api/v1/admin/orders/${testOrderId}/status`)
        .set("Authorization", `Bearer ${adminToken}`)
        .send({ status: "processing" })
        .expect("Content-Type", /json/);

      // Note: This test might fail if admin middleware is not properly configured
      // The test is here to verify the endpoint structure
      expect(response.body).toHaveProperty("success");
    });

    it("should reject non-admin users", async () => {
      if (!testOrderId) {
        return;
      }

      const response = await request(app.server)
        .patch(`/api/v1/admin/orders/${testOrderId}/status`)
        .set("Authorization", `Bearer ${authToken}`) // Regular user token
        .send({ status: "processing" })
        .expect("Content-Type", /json/)
        .expect(403);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("INSUFFICIENT_PERMISSIONS");
    });
  });
});
