import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";
import { db, users, userSessions, eq, and } from "@lolita-fashion/db";
import {
  userRegistrationSchema,
  userLoginSchema,
  passwordResetRequestSchema,
  passwordResetSchema,
  UserStatus,
  UserRole,
  generateRandomString,
} from "@lolita-fashion/shared";
import {
  NotFoundError,
  UnauthorizedError,
  ValidationError,
  DuplicateError,
} from "../middleware/error";
import { requireAuth } from "../middleware/auth";
// Email service removed - no verification needed
// import { sendEmail, EmailType } from "../services/email";

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
    async ({ body, jwt, cookie, set }) => {
      const validation = userRegistrationSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid registration data");
      }

      const userData = validation.data;
      const { registrationMethod, password, name } = userData;

      // Get primary contact based on registration method
      const primaryEmail = registrationMethod === 'email' ? userData.email : undefined;
      const primaryPhone = registrationMethod === 'phone' ? userData.phone : undefined;
      const secondaryEmail = registrationMethod === 'phone' ? userData.email : undefined;
      const secondaryPhone = registrationMethod === 'email' ? userData.phone : undefined;

      // Check if user already exists (check primary contact method)
      let existingUser = null;
      if (registrationMethod === 'email' && primaryEmail) {
        existingUser = await db.query.users.findFirst({
          where: eq(users.email, primaryEmail),
        });
      } else if (registrationMethod === 'phone' && primaryPhone) {
        existingUser = await db.query.users.findFirst({
          where: eq(users.phone, primaryPhone),
        });
      }

      if (existingUser) {
        const contactType = registrationMethod === 'email' ? 'email' : 'phone number';
        throw new DuplicateError(`User with this ${contactType} already exists`);
      }

      // Hash password
      const hashedPassword = await bcrypt.hash(password, 12);

      // Create user with ACTIVE status (no verification required)
      const [newUser] = await db
        .insert(users)
        .values({
          email: primaryEmail,
          phone: primaryPhone,
          password: hashedPassword,
          name,
          registrationMethod: registrationMethod,
          role: UserRole.USER,
          status: UserStatus.ACTIVE,
          emailVerified: false,
          phoneVerified: false,
          // Set secondary contact info
          contactEmail: secondaryEmail,
          contactPhone: secondaryPhone,
        })
        .returning({
          id: users.id,
          email: users.email,
          phone: users.phone,
          name: users.name,
          registrationMethod: users.registrationMethod,
          role: users.role,
          status: users.status,
          emailVerified: users.emailVerified,
          phoneVerified: users.phoneVerified,
          createdAt: users.createdAt,
        });

      set.status = 201;
      return {
        success: true,
        message: "User registered successfully. You can now log in.",
        data: { user: newUser },
      };
    },
    {
      body: t.Union([
        // Email registration
        t.Object({
          registrationMethod: t.Literal('email'),
          email: t.String({ format: "email" }),
          password: t.String({ minLength: 8 }),
          name: t.String({ minLength: 1 }),
          phone: t.Optional(t.String()), // Optional secondary contact
        }),
        // Phone registration  
        t.Object({
          registrationMethod: t.Literal('phone'),
          phone: t.String({ minLength: 10 }),
          password: t.String({ minLength: 8 }),
          name: t.String({ minLength: 1 }),
          email: t.Optional(t.String({ format: "email" })), // Optional secondary contact
        }),
      ]),
      detail: {
        summary: "Register new user with email or phone",
        tags: ["Auth"],
      },
    },
  )

  // Login user
  .post(
    "/login",
    async ({ body, jwt: jwtService, cookie: cookieStore, set }) => {
      const validation = userLoginSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid login data");
      }

      const data = validation.data;
      const { loginMethod, password } = data;
      
      // Get login credential based on method
      const loginEmail = loginMethod === 'email' ? data.email : undefined;
      const loginPhone = loginMethod === 'phone' ? data.phone : undefined;

      // Find user based on login method
      let user = null;
      if (loginMethod === 'email' && loginEmail) {
        user = await db.query.users.findFirst({
          where: eq(users.email, loginEmail),
        });
      } else if (loginMethod === 'phone' && loginPhone) {
        user = await db.query.users.findFirst({
          where: eq(users.phone, loginPhone),
        });
      }

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
        email: user.email || user.phone || user.id,
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
        phone: user.phone,
        name: user.name,
        registrationMethod: user.registrationMethod,
        role: user.role,
        status: user.status,
        emailVerified: user.emailVerified,
        phoneVerified: user.phoneVerified,
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
      body: t.Union([
        // Email login
        t.Object({
          loginMethod: t.Literal('email'),
          email: t.String({ format: "email" }),
          password: t.String({ minLength: 1 }),
        }),
        // Phone login
        t.Object({
          loginMethod: t.Literal('phone'),
          phone: t.String({ minLength: 10 }),
          password: t.String({ minLength: 1 }),
        }),
      ]),
      detail: {
        summary: "Login user with email or phone",
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


  // Request password reset
  .post(
    "/forgot-password",
    async ({ body, set }) => {
      const validation = passwordResetRequestSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid email");
      }

      const data = validation.data;
      const email = 'email' in data ? data.email : undefined;
      
      if (!email) {
        throw new ValidationError("Email is required");
      }

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
    async ({ body, set }) => {
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

;
