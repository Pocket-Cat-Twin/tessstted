import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";
import { db, users, userSessions, eq } from "@lolita-fashion/db";
import {
  UserStatus,
  UserRole,
  generateRandomString,
} from "@lolita-fashion/shared";
import {
  UnauthorizedError,
  ValidationError,
  DuplicateError,
} from "../middleware/error";
import { requireAuth } from "../middleware/auth";
import { verificationService } from "../services/verification";
import { phoneNumberSchema } from "../services/sms";

// Extended registration schema for email OR phone
const extendedRegistrationSchema = t.Object({
  registrationMethod: t.Union([t.Literal("email"), t.Literal("phone")]),
  email: t.Optional(t.String({ format: "email" })),
  phone: t.Optional(t.String()),
  password: t.String({ minLength: 6 }),
  name: t.Optional(t.String({ minLength: 1 })),
  fullName: t.Optional(t.String({ minLength: 1 })),
});

// Extended login schema for email OR phone
const extendedLoginSchema = t.Object({
  loginMethod: t.Union([t.Literal("email"), t.Literal("phone")]),
  email: t.Optional(t.String()),
  phone: t.Optional(t.String()),
  password: t.String({ minLength: 1 }),
});

export const authV2Routes = new Elysia({ prefix: "/auth/v2" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "your-jwt-secret-key",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Register new user with email OR phone
  .post(
    "/register",
    async ({ body, jwt, cookie, set }) => {
      const { registrationMethod, email, phone, password, name, fullName } =
        body;

      // Validate registration method and required fields
      if (registrationMethod === "email" && !email) {
        throw new ValidationError("Email is required for email registration");
      }
      if (registrationMethod === "phone" && !phone) {
        throw new ValidationError("Phone is required for phone registration");
      }
      if (registrationMethod === "phone") {
        const phoneValidation = phoneNumberSchema.safeParse(phone);
        if (!phoneValidation.success) {
          throw new ValidationError("Invalid phone number format");
        }
      }

      // Check if user already exists
      let existingUser;
      if (registrationMethod === "email" && email) {
        existingUser = await db.query.users.findFirst({
          where: eq(users.email, email),
        });
        if (existingUser) {
          throw new DuplicateError("User with this email already exists");
        }
      } else if (registrationMethod === "phone" && phone) {
        existingUser = await db.query.users.findFirst({
          where: eq(users.phone, phone),
        });
        if (existingUser) {
          throw new DuplicateError(
            "User with this phone number already exists",
          );
        }
      }

      // Hash password
      const hashedPassword = await bcrypt.hash(password, 12);

      // Create user
      const userData: any = {
        registrationMethod,
        password: hashedPassword,
        name,
        fullName,
        role: UserRole.USER,
        status: UserStatus.ACTIVE,
        emailVerified: false,
        phoneVerified: false,
      };

      if (registrationMethod === "email") {
        userData.email = email;
      } else {
        userData.phone = phone;
      }

      const [newUser] = await db.insert(users).values(userData).returning({
        id: users.id,
        email: users.email,
        phone: users.phone,
        name: users.name,
        fullName: users.fullName,
        registrationMethod: users.registrationMethod,
        role: users.role,
        status: users.status,
        emailVerified: users.emailVerified,
        phoneVerified: users.phoneVerified,
        createdAt: users.createdAt,
      });

      // Send verification
      try {
        if (registrationMethod === "email" && email) {
          const verificationResult =
            await verificationService.createVerification({
              userId: newUser.id,
              type: "email_registration",
              email,
            });

          if (!verificationResult.success) {
            console.error(
              "Failed to create email verification:",
              verificationResult.error,
            );
          }
        } else if (registrationMethod === "phone" && phone) {
          const verificationResult =
            await verificationService.createVerification({
              userId: newUser.id,
              type: "phone_registration",
              phone,
            });

          if (!verificationResult.success) {
            console.error(
              "Failed to create phone verification:",
              verificationResult.error,
            );
          }
        }
      } catch (error) {
        console.error("Failed to send verification:", error);
        // Don't fail registration if verification fails
      }

      set.status = 201;
      return {
        success: true,
        message:
          registrationMethod === "email"
            ? "User registered successfully. Please check your email for verification."
            : "User registered successfully. Please check your phone for verification code.",
        data: { user: newUser },
      };
    },
    {
      body: extendedRegistrationSchema,
      detail: {
        summary: "Register new user with email or phone",
        tags: ["Auth V2"],
      },
    },
  )

  // Login user with email OR phone
  .post(
    "/login",
    async ({ body, jwt: jwtService, cookie: cookieStore, set }) => {
      const { loginMethod, email, phone, password } = body;

      // Validate login method and required fields
      if (loginMethod === "email" && !email) {
        throw new ValidationError("Email is required for email login");
      }
      if (loginMethod === "phone" && !phone) {
        throw new ValidationError("Phone is required for phone login");
      }

      // Find user
      let user;
      if (loginMethod === "email" && email) {
        user = await db.query.users.findFirst({
          where: eq(users.email, email),
        });
      } else if (loginMethod === "phone" && phone) {
        user = await db.query.users.findFirst({
          where: eq(users.phone, phone),
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

      // No verification needed - users are auto-activated
      // Verification logic removed for consistency with main auth routes

      // Generate JWT token
      const token = await jwtService.sign({
        userId: user.id,
        email: user.email || "",
        phone: user.phone || "",
        registrationMethod: user.registrationMethod,
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
        fullName: user.fullName,
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
      body: extendedLoginSchema,
      detail: {
        summary: "Login user with email or phone",
        tags: ["Auth V2"],
      },
    },
  )

  // Verify email or phone
  .post(
    "/verify",
    async ({ body, set }) => {
      const { token, code } = body;

      if (!token || !code) {
        throw new ValidationError("Token and code are required");
      }

      const result = await verificationService.validateVerification(
        token,
        code,
      );

      if (!result.success) {
        return {
          success: false,
          message: result.error,
          attemptsRemaining: result.attemptsRemaining,
        };
      }

      // Update user verification status
      if (result.userId) {
        const verificationToken = await db.query.verificationTokens.findFirst({
          where: eq(users.id, result.userId), // This should be verificationTokens table
        });

        if (verificationToken?.type === "email_registration") {
          await db
            .update(users)
            .set({
              emailVerified: true,
              status: UserStatus.ACTIVE,
              updatedAt: new Date(),
            })
            .where(eq(users.id, result.userId));
        } else if (verificationToken?.type === "phone_registration") {
          await db
            .update(users)
            .set({
              phoneVerified: true,
              status: UserStatus.ACTIVE,
              updatedAt: new Date(),
            })
            .where(eq(users.id, result.userId));
        }
      }

      return {
        success: true,
        message: "Verification successful",
      };
    },
    {
      body: t.Object({
        token: t.String(),
        code: t.String(),
      }),
      detail: {
        summary: "Verify email or phone",
        tags: ["Auth V2"],
      },
    },
  )

  // Resend verification code
  .post(
    "/resend-verification",
    async ({ body, set }) => {
      const { type, email, phone } = body;

      if (type === "email" && !email) {
        throw new ValidationError("Email is required for email verification");
      }
      if (type === "phone" && !phone) {
        throw new ValidationError("Phone is required for phone verification");
      }

      // Find user
      let user;
      if (type === "email" && email) {
        user = await db.query.users.findFirst({
          where: eq(users.email, email),
        });
      } else if (type === "phone" && phone) {
        user = await db.query.users.findFirst({
          where: eq(users.phone, phone),
        });
      }

      if (!user) {
        // Don't reveal if account exists
        return {
          success: true,
          message: "If an account exists, a verification code has been sent.",
        };
      }

      // Check if already verified
      const isAlreadyVerified =
        type === "email" ? user.emailVerified : user.phoneVerified;
      if (isAlreadyVerified) {
        return {
          success: true,
          message: "Account is already verified.",
        };
      }

      // Create new verification
      try {
        const verificationResult = await verificationService.createVerification(
          {
            userId: user.id,
            type:
              type === "email" ? "email_registration" : "phone_registration",
            email: type === "email" ? email : undefined,
            phone: type === "phone" ? phone : undefined,
          },
        );

        if (!verificationResult.success) {
          if (verificationResult.rateLimited) {
            return {
              success: false,
              message: "Rate limit exceeded. Please try again later.",
              retryAfter: verificationResult.retryAfter,
            };
          }

          throw new Error(
            verificationResult.error || "Failed to send verification",
          );
        }

        return {
          success: true,
          message: "Verification code sent.",
          data: { token: verificationResult.token },
        };
      } catch (error) {
        console.error("Failed to resend verification:", error);
        return {
          success: false,
          message: "Failed to send verification code. Please try again.",
        };
      }
    },
    {
      body: t.Object({
        type: t.Union([t.Literal("email"), t.Literal("phone")]),
        email: t.Optional(t.String()),
        phone: t.Optional(t.String()),
      }),
      detail: {
        summary: "Resend verification code",
        tags: ["Auth V2"],
      },
    },
  )

  // Request password reset (email or phone)
  .post(
    "/forgot-password",
    async ({ body, set }) => {
      const { type, email, phone } = body;

      if (type === "email" && !email) {
        throw new ValidationError("Email is required");
      }
      if (type === "phone" && !phone) {
        throw new ValidationError("Phone is required");
      }

      // Find user
      let user;
      if (type === "email" && email) {
        user = await db.query.users.findFirst({
          where: eq(users.email, email),
        });
      } else if (type === "phone" && phone) {
        user = await db.query.users.findFirst({
          where: eq(users.phone, phone),
        });
      }

      if (!user) {
        // Don't reveal if account exists
        return {
          success: true,
          message: "If an account exists, a password reset code has been sent.",
        };
      }

      try {
        const verificationResult = await verificationService.createVerification(
          {
            userId: user.id,
            type: "password_reset",
            email: type === "email" ? email : undefined,
            phone: type === "phone" ? phone : undefined,
          },
        );

        if (!verificationResult.success) {
          if (verificationResult.rateLimited) {
            return {
              success: false,
              message: "Rate limit exceeded. Please try again later.",
              retryAfter: verificationResult.retryAfter,
            };
          }
          throw new Error(
            verificationResult.error || "Failed to send reset code",
          );
        }

        return {
          success: true,
          message: "If an account exists, a password reset code has been sent.",
          data: { token: verificationResult.token },
        };
      } catch (error) {
        console.error("Failed to send password reset:", error);
        return {
          success: false,
          message: "Failed to send password reset code. Please try again.",
        };
      }
    },
    {
      body: t.Object({
        type: t.Union([t.Literal("email"), t.Literal("phone")]),
        email: t.Optional(t.String()),
        phone: t.Optional(t.String()),
      }),
      detail: {
        summary: "Request password reset",
        tags: ["Auth V2"],
      },
    },
  )

  // Reset password with verification code
  .post(
    "/reset-password",
    async ({ body, set }) => {
      const { token, code, newPassword } = body;

      if (!token || !code || !newPassword) {
        throw new ValidationError("Token, code, and new password are required");
      }

      if (newPassword.length < 6) {
        throw new ValidationError(
          "Password must be at least 6 characters long",
        );
      }

      // Validate verification
      const result = await verificationService.validateVerification(
        token,
        code,
      );

      if (!result.success) {
        return {
          success: false,
          message: result.error,
          attemptsRemaining: result.attemptsRemaining,
        };
      }

      if (!result.userId) {
        throw new Error("Verification successful but no user ID found");
      }

      // Hash new password
      const hashedPassword = await bcrypt.hash(newPassword, 12);

      // Update user password
      await db
        .update(users)
        .set({
          password: hashedPassword,
          updatedAt: new Date(),
        })
        .where(eq(users.id, result.userId));

      // Clear all sessions for this user
      await db
        .delete(userSessions)
        .where(eq(userSessions.userId, result.userId));

      return {
        success: true,
        message:
          "Password reset successful. Please log in with your new password.",
      };
    },
    {
      body: t.Object({
        token: t.String(),
        code: t.String(),
        newPassword: t.String({ minLength: 6 }),
      }),
      detail: {
        summary: "Reset password with verification code",
        tags: ["Auth V2"],
      },
    },
  )

  // All other existing auth routes...
  .use(requireAuth)
  .post(
    "/logout",
    async ({ cookie: cookieStore, store }) => {
      cookieStore.token.remove();

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
        tags: ["Auth V2"],
      },
    },
  )

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
        tags: ["Auth V2"],
      },
    },
  );
