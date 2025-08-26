import { Elysia } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import { getPool, QueryBuilder } from "@lolita-fashion/db";

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
      secret: process.env.JWT_SECRET || "mysql-jwt-secret-change-in-production",
      exp: "7d",
    }),
  )
  .use(cookie())
  .derive(async ({ jwt, cookie: { auth } }) => {
    if (!auth.value) return { user: null };

    try {
      const payload = await jwt.verify(auth.value);
      if (!payload) return { user: null };

      const pool = await getPool();
      const queryBuilder = new QueryBuilder(pool);
      const user = await queryBuilder.getUserById(payload.userId as string);

      if (!user) return { user: null };

      return {
        user: {
          id: user.id,
          email: user.email || "",
          name: user.name,
          role: user.role,
          status: user.status,
          emailVerified: user.email_verified,
          avatar: user.avatar,
          createdAt: user.created_at,
        } as AuthUser,
      };
    } catch (error) {
      console.error("Auth middleware error:", error);
      return { user: null };
    }
  });

// Require authentication  
export const requireAuth = new Elysia({ name: "require-auth" })
  .use(authMiddleware)
  .onBeforeHandle(({ ...context }) => {
    const user = (context as any).user;
    if (!user) {
      throw new Error("Authentication required");
    }
  });

// Require admin role
export const requireAdmin = new Elysia({ name: "require-admin" })
  .use(authMiddleware)
  .onBeforeHandle(({ ...context }) => {
    const user = (context as any).user;
    if (!user || user.role !== "admin") {
      throw new Error("Admin access required");
    }
  });
