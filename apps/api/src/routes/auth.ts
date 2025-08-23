import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";
import { db, users, userSessions, eq, and } from "@yuyu/db";
import {
  userRegistrationSchema,
  userLoginSchema,
  passwordResetRequestSchema,
  passwordResetSchema,
  emailVerificationSchema,
  UserStatus,
  UserRole,
  generateRandomString,
} from "@yuyu/shared";
import {
  NotFoundError,
  UnauthorizedError,
  ValidationError,
  DuplicateError,
} from "../middleware/error";
import { requireAuth } from "../middleware/auth";
import { sendEmail, EmailType } from "../services/email";

export const authRoutes = new Elysia({ prefix: "/auth" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "your-jwt-secret-key",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Register new user
  .post(
    "/register",
    async ({ body, _jwt, _cookie, set }) => {
      const validation = userRegistrationSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid registration data");
      }

      const { email, password, name, phone } = validation.data;

      // Check if user already exists
      const existingUser = await db.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (existingUser) {
        throw new DuplicateError("User with this email already exists");
      }

      // Hash password
      const hashedPassword = await bcrypt.hash(password, 12);

      // Generate email verification token
      const emailVerificationToken = generateRandomString(32);

      // Create user
      const [newUser] = await db
        .insert(users)
        .values({
          email,
          password: hashedPassword,
          name,
          phone,
          role: UserRole.USER,
          status: UserStatus.PENDING,
          emailVerified: false,
          emailVerificationToken,
        })
        .returning({
          id: users.id,
          email: users.email,
          name: users.name,
          role: users.role,
          status: users.status,
          emailVerified: users.emailVerified,
          createdAt: users.createdAt,
        });

      // Send verification email
      try {
        await sendEmail(EmailType.EMAIL_VERIFICATION, email, {
          name,
          verificationToken: emailVerificationToken,
        });
      } catch (error) {
        console.error("Failed to send verification email:", error);
        // Don't fail registration if email fails
      }

      set.status = 201;
      return {
        success: true,
        message:
          "User registered successfully. Please check your email for verification.",
        data: { user: newUser },
      };
    },
    {
      body: t.Object({
        email: t.String({ format: "email" }),
        password: t.String({ minLength: 8 }),
        name: t.String({ minLength: 1 }),
        phone: t.Optional(t.String()),
      }),
      detail: {
        summary: "Register new user",
        tags: ["Auth"],
      },
    },
  )

  // Login user
  .post(
    "/login",
    async ({ body, jwt: jwtService, cookie: cookieStore, _set }) => {
      const validation = userLoginSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid login data");
      }

      const { email, password } = validation.data;

      // Find user
      const user = await db.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (!user) {
        throw new UnauthorizedError("Invalid credentials");
      }

      // Check password
      const isPasswordValid = await bcrypt.compare(password, user.password);
      if (!isPasswordValid) {
        throw new UnauthorizedError("Invalid credentials");
      }

      // Check if user is blocked
      if (user.status === UserStatus.BLOCKED) {
        throw new UnauthorizedError("Account is blocked");
      }

      // Generate JWT token
      const token = await jwtService.sign({
        userId: user.id,
        email: user.email,
        role: user.role,
      });

      // Create session
      const sessionId = generateRandomString(32);
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days

      await db.insert(userSessions).values({
        id: sessionId,
        userId: user.id,
        expiresAt,
      });

      // Update last login
      await db
        .update(users)
        .set({ lastLoginAt: new Date() })
        .where(eq(users.id, user.id));

      // Set cookie
      cookieStore.token.set({
        value: token,
        maxAge: 7 * 24 * 60 * 60, // 7 days
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
      });

      const userResponse = {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
        status: user.status,
        emailVerified: user.emailVerified,
        avatar: user.avatar,
        createdAt: user.createdAt,
      };

      return {
        success: true,
        message: "Login successful",
        data: {
          token,
          user: userResponse,
        },
      };
    },
    {
      body: t.Object({
        email: t.String({ format: "email" }),
        password: t.String({ minLength: 1 }),
      }),
      detail: {
        summary: "Login user",
        tags: ["Auth"],
      },
    },
  )

  // Logout user
  .use(requireAuth)
  .post(
    "/logout",
    async ({ cookie: cookieStore, store }) => {
      // Clear cookie
      cookieStore.token.remove();

      // If user is authenticated, clear their sessions
      if (store.user) {
        await db
          .delete(userSessions)
          .where(eq(userSessions.userId, store.user.id));
      }

      return {
        success: true,
        message: "Logout successful",
      };
    },
    {
      detail: {
        summary: "Logout user",
        tags: ["Auth"],
      },
    },
  )

  // Get current user
  .get(
    "/me",
    ({ store }) => {
      return {
        success: true,
        data: { user: store.user },
      };
    },
    {
      detail: {
        summary: "Get current user",
        tags: ["Auth"],
      },
    },
  )

  // Verify email
  .post(
    "/verify-email",
    async ({ body, _set }) => {
      const validation = emailVerificationSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid verification token");
      }

      const { token } = validation.data;

      // Find user with this token
      const user = await db.query.users.findFirst({
        where: eq(users.emailVerificationToken, token),
      });

      if (!user) {
        throw new NotFoundError("Invalid verification token");
      }

      // Update user
      await db
        .update(users)
        .set({
          emailVerified: true,
          emailVerificationToken: null,
          status: UserStatus.ACTIVE,
          updatedAt: new Date(),
        })
        .where(eq(users.id, user.id));

      return {
        success: true,
        message: "Email verified successfully",
      };
    },
    {
      body: t.Object({
        token: t.String(),
      }),
      detail: {
        summary: "Verify email address",
        tags: ["Auth"],
      },
    },
  )

  // Request password reset
  .post(
    "/forgot-password",
    async ({ body, _set }) => {
      const validation = passwordResetRequestSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid email");
      }

      const { email } = validation.data;

      // Find user
      const user = await db.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (!user) {
        // Don't reveal if email exists or not
        return {
          success: true,
          message:
            "If an account with this email exists, a password reset link has been sent.",
        };
      }

      // Generate reset token
      const resetToken = generateRandomString(32);
      const resetExpires = new Date(Date.now() + 60 * 60 * 1000); // 1 hour

      // Update user with reset token
      await db
        .update(users)
        .set({
          passwordResetToken: resetToken,
          passwordResetExpires: resetExpires,
          updatedAt: new Date(),
        })
        .where(eq(users.id, user.id));

      // Send reset email
      try {
        await sendEmail(EmailType.PASSWORD_RESET, email, {
          name: user.name,
          resetToken,
        });
      } catch (error) {
        console.error("Failed to send password reset email:", error);
        throw new Error("Failed to send password reset email");
      }

      return {
        success: true,
        message:
          "If an account with this email exists, a password reset link has been sent.",
      };
    },
    {
      body: t.Object({
        email: t.String({ format: "email" }),
      }),
      detail: {
        summary: "Request password reset",
        tags: ["Auth"],
      },
    },
  )

  // Reset password
  .post(
    "/reset-password",
    async ({ body, _set }) => {
      const validation = passwordResetSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid reset data");
      }

      const { token, password } = validation.data;

      // Find user with valid reset token
      const user = await db.query.users.findFirst({
        where: and(
          eq(users.passwordResetToken, token),
          // Token should not be expired
        ),
      });

      if (
        !user ||
        !user.passwordResetExpires ||
        user.passwordResetExpires < new Date()
      ) {
        throw new UnauthorizedError("Invalid or expired reset token");
      }

      // Hash new password
      const hashedPassword = await bcrypt.hash(password, 12);

      // Update user
      await db
        .update(users)
        .set({
          password: hashedPassword,
          passwordResetToken: null,
          passwordResetExpires: null,
          updatedAt: new Date(),
        })
        .where(eq(users.id, user.id));

      // Clear all sessions
      await db.delete(userSessions).where(eq(userSessions.userId, user.id));

      return {
        success: true,
        message: "Password reset successful",
      };
    },
    {
      body: t.Object({
        token: t.String(),
        password: t.String({ minLength: 8 }),
      }),
      detail: {
        summary: "Reset password",
        tags: ["Auth"],
      },
    },
  )

  // Resend verification email
  .post(
    "/resend-verification",
    async ({ body, _set }) => {
      const { email } = body as { email: string };

      // Find user
      const user = await db.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (!user || user.emailVerified) {
        return {
          success: true,
          message:
            "If an unverified account with this email exists, a verification email has been sent.",
        };
      }

      // Generate new verification token
      const emailVerificationToken = generateRandomString(32);

      // Update user
      await db
        .update(users)
        .set({
          emailVerificationToken,
          updatedAt: new Date(),
        })
        .where(eq(users.id, user.id));

      // Send verification email
      try {
        await sendEmail(EmailType.EMAIL_VERIFICATION, email, {
          name: user.name,
          verificationToken: emailVerificationToken,
        });
      } catch (error) {
        console.error("Failed to send verification email:", error);
        throw new Error("Failed to send verification email");
      }

      return {
        success: true,
        message:
          "If an unverified account with this email exists, a verification email has been sent.",
      };
    },
    {
      body: t.Object({
        email: t.String({ format: "email" }),
      }),
      detail: {
        summary: "Resend verification email",
        tags: ["Auth"],
      },
    },
  );
