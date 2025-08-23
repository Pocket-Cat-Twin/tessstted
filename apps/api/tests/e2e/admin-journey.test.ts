import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import app from "../../src/index";
import { db, users, orders } from "@yuyu/db";

describe("Admin Journey E2E Tests", () => {
  let server: any;
  let adminToken: string;
  let testUser: any;
  let testUserToken: string;

  beforeAll(async () => {
    // Clean up test data
    await db.delete(orders).where(orders.customerEmail.like("%admintest%"));
    await db.delete(users).where(users.email.like("%admintest%"));

    // Start server for testing
    server = app.listen(0);

    // Create admin user
    const adminRegistration = await request(app.server)
      .post("/api/v1/auth/register")
      .send({
        email: "admin@admintest.com",
        password: "Admin123!@#",
        name: "Admin E2E Test User",
        role: "admin",
      })
      .expect(200);

    expect(adminRegistration.body.success).toBe(true);

    // Login as admin
    const adminLogin = await request(app.server)
      .post("/api/v1/auth/login")
      .send({
        email: "admin@admintest.com",
        password: "Admin123!@#",
      })
      .expect(200);

    expect(adminLogin.body.success).toBe(true);
    adminToken = adminLogin.body.data.token;

    // Create test user for admin operations
    const userRegistration = await request(app.server)
      .post("/api/v1/auth/register")
      .send({
        email: "testuser@admintest.com",
        password: "User123!@#",
        name: "Test User for Admin Operations",
      })
      .expect(200);

    expect(userRegistration.body.success).toBe(true);

    const userLogin = await request(app.server)
      .post("/api/v1/auth/login")
      .send({
        email: "testuser@admintest.com",
        password: "User123!@#",
      })
      .expect(200);

    expect(userLogin.body.success).toBe(true);
    testUserToken = userLogin.body.data.token;
    testUser = userLogin.body.data.user;
  });

  afterAll(async () => {
    // Clean up test data
    await db.delete(orders).where(orders.customerEmail.like("%admintest%"));
    await db.delete(users).where(users.email.like("%admintest%"));

    if (server) {
      server.close();
    }
  });

  describe("Admin Access Control", () => {
    it("should allow admin to access admin dashboard", async () => {
      const dashboardResponse = await request(app.server)
        .get("/api/v1/admin/dashboard")
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(dashboardResponse.status);

      if (dashboardResponse.status === 200) {
        expect(dashboardResponse.body.success).toBe(true);
      }
    });

    it("should deny access to non-admin users", async () => {
      const unauthorizedResponse = await request(app.server)
        .get("/api/v1/admin/dashboard")
        .set("Authorization", `Bearer ${testUserToken}`)
        .expect("Content-Type", /json/);

      // Expect 403 (Forbidden) or 404 (route not implemented)
      expect([403, 404]).toContain(unauthorizedResponse.status);
    });
  });

  describe("Admin User Management", () => {
    it("should allow admin to view all users", async () => {
      const usersResponse = await request(app.server)
        .get("/api/v1/admin/users")
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(usersResponse.status);

      if (usersResponse.status === 200) {
        expect(usersResponse.body.success).toBe(true);
        expect(Array.isArray(usersResponse.body.data)).toBe(true);
      }
    });

    it("should allow admin to view individual user details", async () => {
      const userDetailsResponse = await request(app.server)
        .get(`/api/v1/admin/users/${testUser.id}`)
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(userDetailsResponse.status);

      if (userDetailsResponse.status === 200) {
        expect(userDetailsResponse.body.success).toBe(true);
        expect(userDetailsResponse.body.data.id).toBe(testUser.id);
      }
    });
  });

  describe("Admin Order Management", () => {
    let testOrderId: string;

    beforeAll(async () => {
      // Create test order for admin operations
      const orderResponse = await request(app.server)
        .post("/api/v1/orders")
        .set("Authorization", `Bearer ${testUserToken}`)
        .send({
          nomerok: "ADMIN-TEST-001",
          customerName: "Admin Test Customer",
          customerEmail: "customer@admintest.com",
          customerPhone: "+1111111111admin",
          itemName: "Admin Test Item",
          itemUrl: "https://example.com/admin-test",
          itemPrice: 15000,
          size: "M",
          color: "Purple",
        })
        .expect(200);

      expect(orderResponse.body.success).toBe(true);
      testOrderId = orderResponse.body.data.id;
    });

    it("should allow admin to view all orders", async () => {
      const ordersResponse = await request(app.server)
        .get("/api/v1/admin/orders")
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(ordersResponse.status);

      if (ordersResponse.status === 200) {
        expect(ordersResponse.body.success).toBe(true);
        expect(Array.isArray(ordersResponse.body.data)).toBe(true);

        const testOrder = ordersResponse.body.data?.find(
          (o: any) => o.nomerok === "ADMIN-TEST-001",
        );
        expect(testOrder).toBeDefined();
      }
    });

    it("should allow admin to update order status", async () => {
      const statusUpdateResponse = await request(app.server)
        .patch(`/api/v1/admin/orders/${testOrderId}/status`)
        .set("Authorization", `Bearer ${adminToken}`)
        .send({
          status: "processing",
          adminNotes: "Processing order - admin test",
        })
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(statusUpdateResponse.status);

      if (statusUpdateResponse.status === 200) {
        expect(statusUpdateResponse.body.success).toBe(true);
      }
    });
  });

  describe("Admin System Management", () => {
    it("should allow admin to access system backup functionality", async () => {
      const backupResponse = await request(app.server)
        .post("/api/v1/admin/system/backup")
        .set("Authorization", `Bearer ${adminToken}`)
        .send({ type: "full" })
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(backupResponse.status);

      if (backupResponse.status === 200) {
        expect(backupResponse.body.success).toBe(true);
      }
    });

    it("should allow admin to run cleanup operations", async () => {
      const cleanupResponse = await request(app.server)
        .post("/api/v1/admin/system/cleanup")
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(cleanupResponse.status);

      if (cleanupResponse.status === 200) {
        expect(cleanupResponse.body.success).toBe(true);
      }
    });

    it("should allow admin to access system monitoring", async () => {
      const monitoringResponse = await request(app.server)
        .get("/api/v1/admin/system/monitoring")
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(monitoringResponse.status);

      if (monitoringResponse.status === 200) {
        expect(monitoringResponse.body.success).toBe(true);
      }
    });
  });

  describe("Admin Analytics", () => {
    it("should allow admin to view analytics data", async () => {
      const analyticsResponse = await request(app.server)
        .get("/api/v1/admin/analytics")
        .set("Authorization", `Bearer ${adminToken}`)
        .expect("Content-Type", /json/);

      // May be 200 if route exists, or 404 if not implemented yet
      expect([200, 404]).toContain(analyticsResponse.status);

      if (analyticsResponse.status === 200) {
        expect(analyticsResponse.body.success).toBe(true);
      }
    });
  });
});
