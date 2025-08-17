/**
 * Enhanced Authentication Routes with Multi-Auth Support
 * Supports both email and phone registration/login
 * Enterprise-level security with rate limiting and comprehensive logging
 * Version: 2.0
 */

import { Elysia, t } from "elysia";
import { jwt } from "@elysiajs/jwt";
import { cookie } from "@elysiajs/cookie";
import bcrypt from "bcryptjs";
import { 
  db, 
  users, 
  userSessions, 
  verificationTokens,
  smsLogs,
  emailLogs,
  verificationRateLimit,
  eq, 
  and, 
  or,
  gt,
  sql
} from "@yuyu/db";
import {
  userRegistrationSchema,
  userRegistrationEmailSchema,
  userRegistrationPhoneSchema,
  userLoginSchema,
  userLoginEmailSchema,
  userLoginPhoneSchema,
  userLoginLegacySchema,
  passwordResetRequestSchema,
  passwordResetRequestEmailSchema,
  passwordResetRequestPhoneSchema,
  passwordResetRequestLegacySchema,
  passwordResetSchema,
  emailVerificationSchema,
  phoneVerificationSchema,
  UserStatus,
  UserRole,
  RegistrationMethod,
  isEmailRegistration,
  isPhoneRegistration,
  isEmailLogin,
  isPhoneLogin,
  normalizePhoneNumber,
  formatPhoneForDisplay,
  authResponseSchema,
} from "@yuyu/shared";
import {
  NotFoundError,
  UnauthorizedError,
  ValidationError,
  DuplicateError,
} from "../middleware/error";
import { requireAuth } from "../middleware/auth";
import { sendEmail, EmailType } from "../services/email";
import { generateRandomString } from "@yuyu/shared";

// Rate limiting service
class RateLimitService {
  static async checkLimit(
    identifier: string,
    type: string,
    maxAttempts: number = 5,
    windowMinutes: number = 15
  ): Promise<boolean> {
    const windowStart = new Date(Date.now() - windowMinutes * 60 * 1000);
    
    const existing = await db.query.verificationRateLimit.findFirst({
      where: and(
        eq(verificationRateLimit.identifier, identifier),
        eq(verificationRateLimit.type, type as any),
        gt(verificationRateLimit.windowStart, windowStart)
      ),
    });

    if (existing) {
      if (existing.attemptCount >= maxAttempts) {
        // Check if still blocked
        if (existing.blockedUntil && existing.blockedUntil > new Date()) {
          return true; // Still rate limited
        }
      }
      
      // Increment attempt count
      await db
        .update(verificationRateLimit)
        .set({
          attemptCount: existing.attemptCount + 1,
          blockedUntil: existing.attemptCount + 1 >= maxAttempts 
            ? new Date(Date.now() + windowMinutes * 60 * 1000)
            : null,
          updatedAt: new Date(),
        })
        .where(eq(verificationRateLimit.id, existing.id));
        
      return existing.attemptCount + 1 >= maxAttempts;
    } else {
      // Create new rate limit record
      await db.insert(verificationRateLimit).values({
        identifier,
        type: type as any,
        attemptCount: 1,
        windowStart: new Date(),
      });
      return false;
    }
  }

  static async logAttempt(
    identifier: string,
    type: string,
    status: string,
    ipAddress: string,
    message?: string
  ): Promise<void> {
    // This could be expanded to log to a dedicated audit table
    console.log(`[${new Date().toISOString()}] Auth attempt: ${type} for ${identifier} from ${ipAddress}: ${status}${message ? ` - ${message}` : ''}`);
  }
}

// SMS Service placeholder (implement with your preferred provider)
async function sendSMSMessage(data: { phone: string; message: string; type: string }): Promise<void> {
  try {
    // TODO: Implement with actual SMS provider (Twilio, AWS SNS, etc.)
    console.log(`SMS to ${data.phone}: ${data.message}`);
    
    // Log SMS attempt
    await db.insert(smsLogs).values({
      phone: data.phone,
      message: data.message,
      provider: "development",
      status: "sent",
      sentAt: new Date(),
    });
  } catch (error) {
    console.error("SMS sending failed:", error);
    
    // Log failed SMS
    await db.insert(smsLogs).values({
      phone: data.phone,
      message: data.message,
      provider: "development",
      status: "failed",
      statusMessage: error instanceof Error ? error.message : "Unknown error",
      failedAt: new Date(),
      sentAt: new Date(),
    });
    
    throw error;
  }
}

// Verification code generator
function generateVerificationCode(): string {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

export const authEnhancedRoutes = new Elysia({ prefix: "/auth" })
  .use(
    jwt({
      name: "jwt",
      secret: process.env.JWT_SECRET || "your-jwt-secret-key",
      exp: "7d",
    }),
  )
  .use(cookie())

  // Enhanced Multi-Auth Registration
  .post(
    "/register",
    async ({ body, jwt, cookie, set, request }) => {
      try {
        // Validate registration data
        const validation = userRegistrationSchema.safeParse(body);
        if (!validation.success) {
          console.error("Registration validation failed:", validation.error.flatten());
          throw new ValidationError(
            validation.error.issues.map(issue => issue.message).join(", ") ||
            "Некорректные данные регистрации"
          );
        }

        const registrationData = validation.data;
        const clientIP = request.headers.get("x-forwarded-for") || 
                        request.headers.get("x-real-ip") || 
                        "unknown";
        const userAgent = request.headers.get("user-agent") || "unknown";

        // Rate limiting
        const rateLimitKey = isEmailRegistration(registrationData) 
          ? registrationData.email 
          : normalizePhoneNumber(registrationData.phone);
        
        const isRateLimited = await RateLimitService.checkLimit(
          rateLimitKey,
          isEmailRegistration(registrationData) ? "email_registration" : "phone_registration",
          3, // max 3 attempts
          60  // per hour
        );
        
        if (isRateLimited) {
          set.status = 429;
          return {
            success: false,
            error: "RATE_LIMITED",
            message: "Слишком много попыток регистрации. Попробуйте через час.",
          };
        }

        // Check for existing users
        let existingUser;
        
        if (isEmailRegistration(registrationData)) {
          const { email, phone } = registrationData;
          
          // Check email uniqueness
          existingUser = await db.query.users.findFirst({
            where: eq(users.email, email),
          });
          
          if (existingUser) {
            await RateLimitService.logAttempt(email, "email_registration", "duplicate", clientIP, "Email already exists");
            throw new DuplicateError("Пользователь с таким email уже существует");
          }
          
          // Check phone uniqueness if provided
          if (phone) {
            const normalizedPhone = normalizePhoneNumber(phone);
            const existingPhoneUser = await db.query.users.findFirst({
              where: eq(users.phone, normalizedPhone),
            });
            
            if (existingPhoneUser) {
              await RateLimitService.logAttempt(email, "email_registration", "duplicate", clientIP, "Phone already exists");
              throw new DuplicateError("Пользователь с таким телефоном уже существует");
            }
          }
        } else {
          const { phone, email } = registrationData;
          const normalizedPhone = normalizePhoneNumber(phone);
          
          // Check phone uniqueness
          existingUser = await db.query.users.findFirst({
            where: eq(users.phone, normalizedPhone),
          });
          
          if (existingUser) {
            await RateLimitService.logAttempt(normalizedPhone, "phone_registration", "duplicate", clientIP, "Phone already exists");
            throw new DuplicateError("Пользователь с таким телефоном уже существует");
          }
          
          // Check email uniqueness if provided
          if (email) {
            const existingEmailUser = await db.query.users.findFirst({
              where: eq(users.email, email),
            });
            
            if (existingEmailUser) {
              await RateLimitService.logAttempt(normalizedPhone, "phone_registration", "duplicate", clientIP, "Email already exists");
              throw new DuplicateError("Пользователь с таким email уже существует");
            }
          }
        }

        const { password, name } = registrationData;

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 12);

        // Prepare user data based on registration method
        let newUserData;
        
        if (isEmailRegistration(registrationData)) {
          const { email, phone } = registrationData;
          newUserData = {
            email,
            password: hashedPassword,
            name,
            phone: phone ? normalizePhoneNumber(phone) : null,
            contactPhone: phone ? normalizePhoneNumber(phone) : null,
            registrationMethod: RegistrationMethod.EMAIL,
            status: UserStatus.PENDING,
            role: UserRole.USER,
            emailVerified: false,
            phoneVerified: false,
          };
        } else {
          const { phone, email } = registrationData;
          const normalizedPhone = normalizePhoneNumber(phone);
          newUserData = {
            phone: normalizedPhone,
            contactPhone: normalizedPhone,
            email: email || null,
            contactEmail: email || null,
            password: hashedPassword,
            name,
            registrationMethod: RegistrationMethod.PHONE,
            status: UserStatus.PENDING,
            role: UserRole.USER,
            emailVerified: false,
            phoneVerified: false,
          };
        }

        // Create user
        const [newUser] = await db
          .insert(users)
          .values(newUserData)
          .returning();

        // Generate verification token and code
        const verificationToken = generateRandomString(32);
        const verificationCode = generateVerificationCode();
        
        // Create verification record
        const verificationType = isEmailRegistration(registrationData) 
          ? "email_registration" 
          : "phone_registration";
          
        await db.insert(verificationTokens).values({
          userId: newUser.id,
          type: verificationType as any,
          email: isEmailRegistration(registrationData) ? registrationData.email : null,
          phone: isPhoneRegistration(registrationData) ? normalizePhoneNumber(registrationData.phone) : null,
          token: verificationToken,
          code: verificationCode,
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
          ipAddress: clientIP,
          userAgent,
        });

        // Send verification
        try {
          if (isEmailRegistration(registrationData)) {
            await sendEmail({
              to: registrationData.email,
              type: EmailType.EMAIL_VERIFICATION,
              data: {
                name,
                verificationUrl: `${process.env.FRONTEND_URL}/verify-email?token=${verificationToken}`,
              },
            });
            
            await RateLimitService.logAttempt(registrationData.email, "email_registration", "verification_sent", clientIP);
          } else {
            const message = `YuYu Lolita: Код подтверждения: ${verificationCode}. Никому не сообщайте этот код.`;
            
            await sendSMSMessage({
              phone: normalizePhoneNumber(registrationData.phone),
              message,
              type: "registration",
            });
            
            await RateLimitService.logAttempt(normalizePhoneNumber(registrationData.phone), "phone_registration", "verification_sent", clientIP);
          }
        } catch (verificationError) {
          console.error("Failed to send verification:", verificationError);
          // Don't fail registration if verification sending fails
        }

        set.status = 201;
        return {
          success: true,
          message: isEmailRegistration(registrationData) 
            ? "Регистрация успешна! Проверьте почту для подтверждения."
            : "Регистрация успешна! SMS с кодом отправлен на ваш телефон.",
          data: {
            user: {
              id: newUser.id,
              email: newUser.email,
              phone: newUser.phone ? formatPhoneForDisplay(newUser.phone) : null,
              name: newUser.name,
              registrationMethod: newUser.registrationMethod,
              role: newUser.role,
              status: newUser.status,
              emailVerified: newUser.emailVerified,
              phoneVerified: newUser.phoneVerified,
            },
            requiresVerification: true,
            verificationMethod: isEmailRegistration(registrationData) 
              ? RegistrationMethod.EMAIL 
              : RegistrationMethod.PHONE,
          },
        };
      } catch (error) {
        console.error("Registration error:", error);
        throw error;
      }
    },
    {
      body: t.Object({
        registrationMethod: t.Union([t.Literal("email"), t.Literal("phone")]),
        password: t.String({ minLength: 8 }),
        name: t.String({ minLength: 1 }),
        email: t.Optional(t.String({ format: "email" })),
        phone: t.Optional(t.String()),
      }),
      detail: {
        summary: "Register new user with email or phone",
        tags: ["Auth V2"],
      },
    },
  )

  // Enhanced Multi-Auth Login
  .post(
    "/login",
    async ({ body, jwt, cookie, set, request }) => {
      try {
        // Try new multi-auth schema first, fall back to legacy
        let validation = userLoginSchema.safeParse(body);
        let isLegacyLogin = false;
        
        if (!validation.success) {
          // Try legacy email-only login for backward compatibility
          const legacyValidation = userLoginLegacySchema.safeParse(body);
          if (legacyValidation.success) {
            validation = { 
              success: true, 
              data: {
                ...legacyValidation.data,
                loginMethod: RegistrationMethod.EMAIL
              }
            };
            isLegacyLogin = true;
          } else {
            throw new ValidationError("Некорректные данные для входа");
          }
        }

        const loginData = validation.data;
        const clientIP = request.headers.get("x-forwarded-for") || 
                        request.headers.get("x-real-ip") || 
                        "unknown";

        // Rate limiting
        const rateLimitKey = isEmailLogin(loginData) ? loginData.email : normalizePhoneNumber(loginData.phone);
        const isRateLimited = await RateLimitService.checkLimit(rateLimitKey, "login_2fa", 5, 15);
        
        if (isRateLimited) {
          set.status = 429;
          return {
            success: false,
            error: "RATE_LIMITED",
            message: "Слишком много попыток входа. Попробуйте через 15 минут.",
          };
        }

        // Find user by email or phone
        let user;
        
        if (isEmailLogin(loginData) || isLegacyLogin) {
          user = await db.query.users.findFirst({
            where: eq(users.email, loginData.email),
          });
        } else {
          const normalizedPhone = normalizePhoneNumber(loginData.phone);
          user = await db.query.users.findFirst({
            where: eq(users.phone, normalizedPhone),
          });
        }

        if (!user || !(await bcrypt.compare(loginData.password, user.password))) {
          await RateLimitService.logAttempt(rateLimitKey, "login_2fa", "failed", clientIP, "Invalid credentials");
          throw new UnauthorizedError("Неверные данные для входа");
        }

        // Check if user is blocked
        if (user.status === UserStatus.BLOCKED) {
          await RateLimitService.logAttempt(rateLimitKey, "login_2fa", "blocked", clientIP, "Account blocked");
          throw new UnauthorizedError("Аккаунт заблокирован");
        }

        // Update last login
        await db
          .update(users)
          .set({ lastLoginAt: new Date() })
          .where(eq(users.id, user.id));

        // Generate JWT token
        const token = await jwt.sign({
          id: user.id,
          email: user.email,
          phone: user.phone,
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

        // Set authentication cookie
        cookie.token.set({
          value: token,
          httpOnly: true,
          secure: process.env.NODE_ENV === "production",
          sameSite: "strict",
          maxAge: 7 * 24 * 60 * 60, // 7 days
        });

        await RateLimitService.logAttempt(rateLimitKey, "login_2fa", "success", clientIP);

        return {
          success: true,
          message: "Успешный вход в систему",
          data: {
            user: {
              id: user.id,
              email: user.email,
              phone: user.phone ? formatPhoneForDisplay(user.phone) : null,
              name: user.name,
              registrationMethod: user.registrationMethod,
              role: user.role,
              status: user.status,
              emailVerified: user.emailVerified,
              phoneVerified: user.phoneVerified,
            },
            token,
          },
        };
      } catch (error) {
        console.error("Login error:", error);
        throw error;
      }
    },
    {
      body: t.Object({
        loginMethod: t.Optional(t.Union([t.Literal("email"), t.Literal("phone")])),
        email: t.Optional(t.String({ format: "email" })),
        phone: t.Optional(t.String()),
        password: t.String({ minLength: 1 }),
      }),
      detail: {
        summary: "Login with email or phone",
        tags: ["Auth V2"],
      },
    },
  )

  // Verify Email
  .post(
    "/verify-email",
    async ({ body, set }) => {
      const validation = emailVerificationSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Некорректный токен верификации");
      }

      const { token } = validation.data;

      // Find verification record
      const verificationRecord = await db.query.verificationTokens.findFirst({
        where: and(
          eq(verificationTokens.token, token),
          eq(verificationTokens.type, "email_registration"),
          eq(verificationTokens.status, "pending")
        ),
      });

      if (!verificationRecord || verificationRecord.expiresAt < new Date()) {
        throw new NotFoundError("Недействительный или истекший токен верификации");
      }

      // Update verification record
      await db
        .update(verificationTokens)
        .set({
          status: "verified",
          verifiedAt: new Date(),
        })
        .where(eq(verificationTokens.id, verificationRecord.id));

      // Update user
      await db
        .update(users)
        .set({
          emailVerified: true,
          status: UserStatus.ACTIVE,
          updatedAt: new Date(),
        })
        .where(eq(users.id, verificationRecord.userId!));

      return {
        success: true,
        message: "Email успешно подтвержден",
      };
    },
    {
      body: t.Object({
        token: t.String(),
      }),
      detail: {
        summary: "Verify email address",
        tags: ["Auth V2"],
      },
    },
  )

  // Verify Phone
  .post(
    "/verify-phone",
    async ({ body, set }) => {
      const validation = phoneVerificationSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Некорректный код верификации");
      }

      const { token, code } = validation.data;

      // Find verification record
      const verificationRecord = await db.query.verificationTokens.findFirst({
        where: and(
          eq(verificationTokens.token, token),
          eq(verificationTokens.type, "phone_registration"),
          eq(verificationTokens.status, "pending")
        ),
      });

      if (!verificationRecord || verificationRecord.expiresAt < new Date()) {
        throw new NotFoundError("Недействительный или истекший токен верификации");
      }

      // Check attempt count
      if (verificationRecord.attemptCount >= verificationRecord.maxAttempts) {
        throw new UnauthorizedError("Превышено максимальное количество попыток");
      }

      // Verify code
      if (verificationRecord.code !== code) {
        // Increment attempt count
        await db
          .update(verificationTokens)
          .set({
            attemptCount: verificationRecord.attemptCount + 1,
            status: verificationRecord.attemptCount + 1 >= verificationRecord.maxAttempts ? "failed" : "pending",
          })
          .where(eq(verificationTokens.id, verificationRecord.id));
          
        throw new UnauthorizedError("Неверный код подтверждения");
      }

      // Update verification record
      await db
        .update(verificationTokens)
        .set({
          status: "verified",
          verifiedAt: new Date(),
        })
        .where(eq(verificationTokens.id, verificationRecord.id));

      // Update user
      await db
        .update(users)
        .set({
          phoneVerified: true,
          status: UserStatus.ACTIVE,
          updatedAt: new Date(),
        })
        .where(eq(users.id, verificationRecord.userId!));

      return {
        success: true,
        message: "Телефон успешно подтвержден",
      };
    },
    {
      body: t.Object({
        token: t.String(),
        code: t.String({ minLength: 6, maxLength: 6 }),
      }),
      detail: {
        summary: "Verify phone number with SMS code",
        tags: ["Auth V2"],
      },
    },
  )

  // Logout
  .use(requireAuth)
  .post(
    "/logout",
    async ({ cookie, store }) => {
      // Clear cookie
      cookie.token.remove();

      // Clear user sessions
      if (store.user) {
        await db
          .delete(userSessions)
          .where(eq(userSessions.userId, store.user.id));
      }

      return {
        success: true,
        message: "Выход выполнен успешно",
      };
    },
    {
      detail: {
        summary: "Logout user",
        tags: ["Auth V2"],
      },
    },
  )

  // Get current user
  .get(
    "/me",
    ({ store }) => {
      const user = store.user;
      return {
        success: true,
        data: {
          user: user ? {
            ...user,
            phone: user.phone ? formatPhoneForDisplay(user.phone) : null,
          } : null,
        },
      };
    },
    {
      detail: {
        summary: "Get current user",
        tags: ["Auth V2"],
      },
    },
  );