import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";
import { getPool, QueryBuilder } from "@lolita-fashion/db";
import type { User } from "@lolita-fashion/db";

export const authRoutes = new Elysia({ prefix: "/auth" })
  .use(
    jwt({
      name: "jwt", 
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())

  // User Registration
  .post(
    "/register",
    async ({ body, jwt, cookie: { auth } }) => {
      try {
        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);

        // Check if user already exists
        const existingUser = await queryBuilder.getUserByEmail(body.email);
        if (existingUser) {
          return {
            success: false,
            error: "User already exists",
          };
        }

        // Hash password
        const passwordHash = await bcrypt.hash(body.password, 10);

        // Create user
        const userId = await queryBuilder.createUser({
          email: body.email,
          phone: body.phone,
          password_hash: passwordHash,
          name: body.name,
          full_name: body.fullName,
          registration_method: "email",
          role: "user",
          status: "active", // No verification for now
          email_verified: true, // Auto-verify for simplicity
          phone_verified: false,
        });

        // Generate JWT token
        const token = await jwt.sign({ userId, email: body.email });
        auth.set({
          value: token,
          httpOnly: true,
          maxAge: 7 * 24 * 60 * 60, // 7 days
        });

        return {
          success: true,
          message: "User registered successfully",
          user: {
            id: userId,
            email: body.email,
            name: body.name,
          },
        };
      } catch (error) {
        console.error("Registration error:", error);
        return {
          success: false,
          error: "Registration failed",
        };
      }
    },
    {
      body: t.Object({
        email: t.String({ format: "email" }),
        password: t.String({ minLength: 6 }),
        name: t.String({ minLength: 1 }),
        fullName: t.Optional(t.String()),
        phone: t.Optional(t.String()),
      }),
      detail: {
        tags: ["Auth"],
        summary: "Register new user",
        description: "Register a new user with email and password",
      },
    },
  )

  // User Login
  .post(
    "/login",
    async ({ body, jwt, cookie: { auth } }) => {
      try {
        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);

        // Find user by email
        const user = await queryBuilder.getUserByEmail(body.email);
        if (!user) {
          return {
            success: false,
            error: "Invalid credentials",
          };
        }

        // Check password
        const isValid = await bcrypt.compare(body.password, user.password_hash);
        if (!isValid) {
          return {
            success: false,
            error: "Invalid credentials",
          };
        }

        // Check if user is active
        if (user.status !== "active") {
          return {
            success: false,
            error: "Account is not active",
          };
        }

        // Generate JWT token
        const token = await jwt.sign({ userId: user.id, email: user.email });
        auth.set({
          value: token,
          httpOnly: true,
          maxAge: 7 * 24 * 60 * 60, // 7 days
        });

        return {
          success: true,
          message: "Login successful",
          user: {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role,
          },
        };
      } catch (error) {
        console.error("Login error:", error);
        return {
          success: false,
          error: "Login failed",
        };
      }
    },
    {
      body: t.Object({
        email: t.String({ format: "email" }),
        password: t.String({ minLength: 1 }),
      }),
      detail: {
        tags: ["Auth"],
        summary: "User login",
        description: "Authenticate user with email and password",
      },
    },
  )

  // User Logout
  .post(
    "/logout",
    async ({ cookie: { auth } }) => {
      auth.remove();
      return {
        success: true,
        message: "Logged out successfully",
      };
    },
    {
      detail: {
        tags: ["Auth"],
        summary: "User logout",
        description: "Logout user and clear authentication cookie",
      },
    },
  )

  // Get Current User
  .get(
    "/me",
    async ({ jwt, cookie: { auth } }) => {
      try {
        if (!auth.value) {
          return {
            success: false,
            error: "Not authenticated",
          };
        }

        const payload = await jwt.verify(auth.value);
        if (!payload) {
          return {
            success: false,
            error: "Invalid token",
          };
        }

        const pool = await getPool();
        const queryBuilder = new QueryBuilder(pool);
        const user = await queryBuilder.getUserById(payload.userId as string);

        if (!user) {
          return {
            success: false,
            error: "User not found",
          };
        }

        return {
          success: true,
          user: {
            id: user.id,
            email: user.email,
            name: user.name,
            role: user.role,
            status: user.status,
          },
        };
      } catch (error) {
        console.error("Get current user error:", error);
        return {
          success: false,
          error: "Failed to get user info",
        };
      }
    },
    {
      detail: {
        tags: ["Auth"],
        summary: "Get current user",
        description: "Get information about the currently authenticated user",
      },
    },
  );
