import { Elysia } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { db, users, eq } from "@yuyu/db";
import { UserRole } from "@yuyu/shared";

// User type for auth context
interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  emailVerified: boolean;
  avatar?: string;
  createdAt: Date;
}

export const authMiddleware = new Elysia({ name: "auth" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "your-jwt-secret-key",
    }),
  )
  .use(cookie())
  .state("user", null as AuthUser | null)
  .onBeforeHandle(async ({ jwt: jwtInstance, cookie: cookieInstance, headers, store }) => {
    // Try to get token from Authorization header or cookie
    const authHeader = headers.authorization;
    const token = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7)
      : cookieInstance.token;

    if (!token) {
      store.user = null;
      return;
    }

    try {
      const payload = await jwtInstance.verify(token);
      if (!payload || typeof payload !== "object" || !("userId" in payload)) {
        store.user = null;
        return;
      }

      // Get user from database
      const user = await db.query.users.findFirst({
        where: eq(users.id, payload.userId as string),
        columns: {
          id: true,
          email: true,
          name: true,
          role: true,
          status: true,
          emailVerified: true,
          avatar: true,
          createdAt: true,
        },
      });

      if (!user || user.status === "blocked") {
        store.user = null;
        return;
      }

      store.user = user as AuthUser;
    } catch (error) {
      console.error("Auth middleware error:", error);
      store.user = null;
    }
  });

// Require authentication
export const requireAuth = new Elysia({ name: "requireAuth" })
  .use(authMiddleware)
  .onBeforeHandle(({ store, set }) => {
    if (!store.user) {
      set.status = 401;
      return {
        success: false,
        error: "AUTHENTICATION_ERROR",
        message: "Authentication required",
      };
    }
  });

// Require admin role
export const requireAdmin = new Elysia({ name: "requireAdmin" })
  .use(requireAuth)
  .onBeforeHandle(({ store, set }) => {
    if (store.user?.role !== UserRole.ADMIN) {
      set.status = 403;
      return {
        success: false,
        error: "AUTHORIZATION_ERROR",
        message: "Admin access required",
      };
    }
  });

// Require email verification
export const requireEmailVerification = new Elysia({
  name: "requireEmailVerification",
})
  .use(requireAuth)
  .onBeforeHandle(({ store, set }) => {
    if (!store.user?.emailVerified) {
      set.status = 403;
      return {
        success: false,
        error: "EMAIL_NOT_VERIFIED",
        message: "Email verification required",
      };
    }
  });
