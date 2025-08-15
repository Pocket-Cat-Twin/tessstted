import { Elysia, t } from "elysia";
import bcrypt from "bcryptjs";
import { db, users, userSessions, eq, and, desc, sql } from "@yuyu/db";
import { userProfileUpdateSchema, UserRole, UserStatus } from "@yuyu/shared";
import { requireAuth, requireAdmin } from "../middleware/auth";
import {
  NotFoundError,
  ValidationError,
  ForbiddenError,
} from "../middleware/error";

export const userRoutes = new Elysia({ prefix: "/users" })

  // User profile routes (authenticated users)
  .use(requireAuth)

  // Get current user profile
  .get(
    "/profile",
    ({ user }) => {
      return {
        success: true,
        data: { user },
      };
    },
    {
      detail: {
        summary: "Get current user profile",
        tags: ["Users"],
      },
    },
  )

  // Update current user profile
  .put(
    "/profile",
    async ({ body, user, set }) => {
      const validation = userProfileUpdateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid profile data");
      }

      const updateData = validation.data;

      // Update user
      const [updatedUser] = await db
        .update(users)
        .set({
          ...updateData,
          updatedAt: new Date(),
        })
        .where(eq(users.id, user.id))
        .returning({
          id: users.id,
          email: users.email,
          name: users.name,
          phone: users.phone,
          role: users.role,
          status: users.status,
          emailVerified: users.emailVerified,
          avatar: users.avatar,
          updatedAt: users.updatedAt,
        });

      return {
        success: true,
        message: "Profile updated successfully",
        data: { user: updatedUser },
      };
    },
    {
      body: t.Object({
        name: t.Optional(t.String({ minLength: 1 })),
        phone: t.Optional(t.String()),
        avatar: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update current user profile",
        tags: ["Users"],
      },
    },
  )

  // Change password
  .put(
    "/profile/password",
    async ({ body, user }) => {
      const { currentPassword, newPassword } = body as {
        currentPassword: string;
        newPassword: string;
      };

      // Get user with password
      const userWithPassword = await db.query.users.findFirst({
        where: eq(users.id, user.id),
      });

      if (!userWithPassword) {
        throw new NotFoundError("User not found");
      }

      // Verify current password
      const isCurrentPasswordValid = await bcrypt.compare(
        currentPassword,
        userWithPassword.password,
      );
      if (!isCurrentPasswordValid) {
        throw new ValidationError("Current password is incorrect");
      }

      // Hash new password
      const hashedNewPassword = await bcrypt.hash(newPassword, 12);

      // Update password
      await db
        .update(users)
        .set({
          password: hashedNewPassword,
          updatedAt: new Date(),
        })
        .where(eq(users.id, user.id));

      // Clear all sessions except current
      await db.delete(userSessions).where(eq(userSessions.userId, user.id));

      return {
        success: true,
        message: "Password changed successfully",
      };
    },
    {
      body: t.Object({
        currentPassword: t.String({ minLength: 1 }),
        newPassword: t.String({ minLength: 8 }),
      }),
      detail: {
        summary: "Change user password",
        tags: ["Users"],
      },
    },
  )

  // Get user's orders
  .get(
    "/profile/orders",
    async ({ user, query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 10;
      const offset = (page - 1) * limit;

      // Get user's orders
      const userOrders = await db.query.orders.findMany({
        where: eq(db.orders.userId, user.id),
        with: {
          goods: true,
        },
        orderBy: desc(db.orders.createdAt),
        limit,
        offset,
      });

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(db.orders)
        .where(eq(db.orders.userId, user.id));

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: userOrders,
        pagination: {
          page,
          limit,
          total: count,
          totalPages,
          hasNext: page < totalPages,
          hasPrev: page > 1,
        },
      };
    },
    {
      query: t.Object({
        page: t.Optional(t.String()),
        limit: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get current user orders",
        tags: ["Users"],
      },
    },
  )

  // Admin routes
  .use(requireAdmin)

  // Get all users with pagination and filtering
  .get(
    "/",
    async ({ query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 10;
      const role = query.role as UserRole;
      const status = query.status as UserStatus;
      const search = query.search;
      const offset = (page - 1) * limit;

      // Build where conditions
      const conditions = [];
      if (role) {
        conditions.push(eq(users.role, role));
      }
      if (status) {
        conditions.push(eq(users.status, status));
      }
      if (search) {
        conditions.push(
          sql`(${users.name} ILIKE ${`%${search}%`} OR ${users.email} ILIKE ${`%${search}%`})`,
        );
      }

      const whereClause =
        conditions.length > 0 ? and(...conditions) : undefined;

      // Get users
      const usersResult = await db.query.users.findMany({
        where: whereClause,
        columns: {
          password: false, // Exclude password
          passwordResetToken: false,
          emailVerificationToken: false,
        },
        orderBy: desc(users.createdAt),
        limit,
        offset,
      });

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(users)
        .where(whereClause);

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: usersResult,
        pagination: {
          page,
          limit,
          total: count,
          totalPages,
          hasNext: page < totalPages,
          hasPrev: page > 1,
        },
      };
    },
    {
      query: t.Object({
        page: t.Optional(t.String()),
        limit: t.Optional(t.String()),
        role: t.Optional(t.String()),
        status: t.Optional(t.String()),
        search: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get all users (Admin)",
        tags: ["Users"],
      },
    },
  )

  // Get user by ID
  .get(
    "/:id",
    async ({ params: { id } }) => {
      const user = await db.query.users.findFirst({
        where: eq(users.id, id),
        columns: {
          password: false, // Exclude password
          passwordResetToken: false,
          emailVerificationToken: false,
        },
        with: {
          orders: {
            columns: {
              id: true,
              nomerok: true,
              status: true,
              totalRuble: true,
              createdAt: true,
            },
            orderBy: desc(db.orders.createdAt),
            limit: 5, // Last 5 orders
          },
        },
      });

      if (!user) {
        throw new NotFoundError("User not found");
      }

      return {
        success: true,
        data: { user },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Get user by ID (Admin)",
        tags: ["Users"],
      },
    },
  )

  // Update user
  .put(
    "/:id",
    async ({ params: { id }, body, user: currentUser }) => {
      const { role, status, name, phone, avatar } = body as {
        role?: UserRole;
        status?: UserStatus;
        name?: string;
        phone?: string;
        avatar?: string;
      };

      // Find user
      const existingUser = await db.query.users.findFirst({
        where: eq(users.id, id),
      });

      if (!existingUser) {
        throw new NotFoundError("User not found");
      }

      // Prevent self-demotion from admin
      if (currentUser.id === id && role && role !== UserRole.ADMIN) {
        throw new ForbiddenError("Cannot change your own admin role");
      }

      // Update user
      const [updatedUser] = await db
        .update(users)
        .set({
          ...(role && { role }),
          ...(status && { status }),
          ...(name && { name }),
          ...(phone && { phone }),
          ...(avatar && { avatar }),
          updatedAt: new Date(),
        })
        .where(eq(users.id, id))
        .returning({
          id: users.id,
          email: users.email,
          name: users.name,
          phone: users.phone,
          role: users.role,
          status: users.status,
          emailVerified: users.emailVerified,
          avatar: users.avatar,
          updatedAt: users.updatedAt,
        });

      return {
        success: true,
        message: "User updated successfully",
        data: { user: updatedUser },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        role: t.Optional(t.String()),
        status: t.Optional(t.String()),
        name: t.Optional(t.String()),
        phone: t.Optional(t.String()),
        avatar: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update user (Admin)",
        tags: ["Users"],
      },
    },
  )

  // Block user
  .post(
    "/:id/block",
    async ({ params: { id }, body, user: currentUser }) => {
      const { reason } = body as { reason?: string };

      // Find user
      const existingUser = await db.query.users.findFirst({
        where: eq(users.id, id),
      });

      if (!existingUser) {
        throw new NotFoundError("User not found");
      }

      // Prevent self-blocking
      if (currentUser.id === id) {
        throw new ForbiddenError("Cannot block yourself");
      }

      // Update user status
      await db
        .update(users)
        .set({
          status: UserStatus.BLOCKED,
          updatedAt: new Date(),
        })
        .where(eq(users.id, id));

      // Clear user sessions
      await db.delete(userSessions).where(eq(userSessions.userId, id));

      return {
        success: true,
        message: "User blocked successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        reason: t.Optional(t.String()),
      }),
      detail: {
        summary: "Block user (Admin)",
        tags: ["Users"],
      },
    },
  )

  // Unblock user
  .post(
    "/:id/unblock",
    async ({ params: { id }, user: currentUser }) => {
      // Find user
      const existingUser = await db.query.users.findFirst({
        where: eq(users.id, id),
      });

      if (!existingUser) {
        throw new NotFoundError("User not found");
      }

      // Update user status
      await db
        .update(users)
        .set({
          status: UserStatus.ACTIVE,
          updatedAt: new Date(),
        })
        .where(eq(users.id, id));

      return {
        success: true,
        message: "User unblocked successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Unblock user (Admin)",
        tags: ["Users"],
      },
    },
  )

  // Delete user
  .delete(
    "/:id",
    async ({ params: { id }, user: currentUser }) => {
      // Find user
      const existingUser = await db.query.users.findFirst({
        where: eq(users.id, id),
      });

      if (!existingUser) {
        throw new NotFoundError("User not found");
      }

      // Prevent self-deletion
      if (currentUser.id === id) {
        throw new ForbiddenError("Cannot delete yourself");
      }

      // Delete user (this will cascade to sessions, but orders will have userId set to null)
      await db.delete(users).where(eq(users.id, id));

      return {
        success: true,
        message: "User deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete user (Admin)",
        tags: ["Users"],
      },
    },
  )

  // Get user statistics
  .get(
    "/stats/overview",
    async () => {
      // Get user counts by role
      const roleCounts = await db
        .select({
          role: users.role,
          count: sql<number>`count(*)`,
        })
        .from(users)
        .groupBy(users.role);

      // Get user counts by status
      const statusCounts = await db
        .select({
          status: users.status,
          count: sql<number>`count(*)`,
        })
        .from(users)
        .groupBy(users.status);

      // Get new users in last 30 days
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
      const [{ newUsersCount }] = await db
        .select({
          newUsersCount: sql<number>`count(*)`,
        })
        .from(users)
        .where(sql`${users.createdAt} >= ${thirtyDaysAgo}`);

      // Get email verification stats
      const [{ verifiedUsersCount }] = await db
        .select({
          verifiedUsersCount: sql<number>`count(*)`,
        })
        .from(users)
        .where(eq(users.emailVerified, true));

      const [{ totalUsersCount }] = await db
        .select({
          totalUsersCount: sql<number>`count(*)`,
        })
        .from(users);

      return {
        success: true,
        data: {
          roleCounts,
          statusCounts,
          newUsersCount: newUsersCount || 0,
          verifiedUsersCount: verifiedUsersCount || 0,
          totalUsersCount: totalUsersCount || 0,
        },
      };
    },
    {
      detail: {
        summary: "Get user statistics (Admin)",
        tags: ["Users"],
      },
    },
  );
