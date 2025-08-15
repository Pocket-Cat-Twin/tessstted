import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Elysia } from "elysia";
import app from "../src/index";

describe("Authentication API", () => {
  beforeAll(async () => {
    // Set NODE_ENV to test
    process.env.NODE_ENV = "test";
  });

  afterAll(async () => {
    // Clean up
  });

  describe("POST /api/v1/auth/register", () => {
    it("should register a new user with valid data", async () => {
      const testUser = {
        email: `test${Date.now()}@example.com`,
        password: "testPassword123",
        name: "Test User",
        phone: "+1234567890",
      };

      const response = await app.handle(
        new Request("http://localhost/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testUser),
        })
      );

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.message).toContain("success");
      expect(data.data).toHaveProperty("user");
      expect(data.data.user.email).toBe(testUser.email);
    });

    it("should reject registration with invalid email", async () => {
      const invalidUser = {
        email: "invalid-email",
        password: "testPassword123",
        name: "Test User",
      };

      try {
        await app.handle(
          new Request("http://localhost/api/v1/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(invalidUser),
          })
        );
        // Should not reach here
        expect(true).toBe(false);
      } catch (error: any) {
        console.log("Validation error:", error);
        expect(error).toBeDefined();
        expect(error.message || error.summary).toContain("email");
      }
    });

    it("should reject registration with weak password", async () => {
      const invalidUser = {
        email: "test2@example.com",
        password: "123", // Too short
        name: "Test User",
      };

      const response = await request(app.server)
        .post("/api/v1/auth/register")
        .send(invalidUser)
        .expect("Content-Type", /json/)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("VALIDATION_ERROR");
    });

    it("should reject duplicate email registration", async () => {
      const testUser = {
        email: "duplicate@example.com",
        password: "testPassword123",
        name: "Test User",
      };

      // First registration
      await request(app.server)
        .post("/api/v1/auth/register")
        .send(testUser)
        .expect(200);

      // Duplicate registration
      const response = await request(app.server)
        .post("/api/v1/auth/register")
        .send(testUser)
        .expect("Content-Type", /json/)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("USER_EXISTS");
    });
  });

  describe("POST /api/v1/auth/login", () => {
    beforeAll(async () => {
      // Create a test user for login tests
      const testUser = {
        email: "login@example.com",
        password: "testPassword123",
        name: "Login Test User",
      };

      await request(app.server).post("/api/v1/auth/register").send(testUser);
    });

    it("should login with valid credentials", async () => {
      const credentials = {
        email: "login@example.com",
        password: "testPassword123",
      };

      const response = await request(app.server)
        .post("/api/v1/auth/login")
        .send(credentials)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("token");
      expect(response.body.data).toHaveProperty("user");
      expect(response.body.data.user.email).toBe(credentials.email);
    });

    it("should reject login with invalid email", async () => {
      const credentials = {
        email: "nonexistent@example.com",
        password: "testPassword123",
      };

      const response = await request(app.server)
        .post("/api/v1/auth/login")
        .send(credentials)
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("INVALID_CREDENTIALS");
    });

    it("should reject login with invalid password", async () => {
      const credentials = {
        email: "login@example.com",
        password: "wrongPassword",
      };

      const response = await request(app.server)
        .post("/api/v1/auth/login")
        .send(credentials)
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("INVALID_CREDENTIALS");
    });

    it("should reject login with missing fields", async () => {
      const response = await request(app.server)
        .post("/api/v1/auth/login")
        .send({ email: "login@example.com" }) // Missing password
        .expect("Content-Type", /json/)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("VALIDATION_ERROR");
    });
  });

  describe("GET /api/v1/auth/me", () => {
    let authToken: string;

    beforeAll(async () => {
      // Create and login a test user
      const testUser = {
        email: "me@example.com",
        password: "testPassword123",
        name: "Me Test User",
      };

      await request(app.server).post("/api/v1/auth/register").send(testUser);

      const loginResponse = await request(app.server)
        .post("/api/v1/auth/login")
        .send({ email: testUser.email, password: testUser.password });

      authToken = loginResponse.body.data.token;
    });

    it("should return user info with valid token", async () => {
      const response = await request(app.server)
        .get("/api/v1/auth/me")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty("user");
      expect(response.body.data.user.email).toBe("me@example.com");
    });

    it("should reject request without token", async () => {
      const response = await request(app.server)
        .get("/api/v1/auth/me")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });

    it("should reject request with invalid token", async () => {
      const response = await request(app.server)
        .get("/api/v1/auth/me")
        .set("Authorization", "Bearer invalid_token")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });
  });

  describe("POST /api/v1/auth/logout", () => {
    let authToken: string;

    beforeAll(async () => {
      // Create and login a test user
      const testUser = {
        email: "logout@example.com",
        password: "testPassword123",
        name: "Logout Test User",
      };

      await request(app.server).post("/api/v1/auth/register").send(testUser);

      const loginResponse = await request(app.server)
        .post("/api/v1/auth/login")
        .send({ email: testUser.email, password: testUser.password });

      authToken = loginResponse.body.data.token;
    });

    it("should logout successfully with valid token", async () => {
      const response = await request(app.server)
        .post("/api/v1/auth/logout")
        .set("Authorization", `Bearer ${authToken}`)
        .expect("Content-Type", /json/)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.message).toContain("logout");
    });

    it("should reject logout without token", async () => {
      const response = await request(app.server)
        .post("/api/v1/auth/logout")
        .expect("Content-Type", /json/)
        .expect(401);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toBe("UNAUTHORIZED");
    });
  });
});
