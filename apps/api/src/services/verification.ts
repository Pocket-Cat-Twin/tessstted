import { db, verificationTokens, users, smsLogs, emailLogs, verificationRateLimit, eq, and, gte } from '@yuyu/db';
import { generateRandomString } from '@yuyu/shared';
import { smsService, generateVerificationCode } from './sms';
import { sendEmail, EmailType } from './email';

export type VerificationType = 'email_registration' | 'phone_registration' | 'password_reset' | 'phone_change' | 'email_change' | 'login_2fa';

export interface VerificationRequest {
  userId?: string;
  type: VerificationType;
  email?: string;
  phone?: string;
  ipAddress?: string;
  userAgent?: string;
}

export interface VerificationResult {
  success: boolean;
  token?: string;
  expiresAt?: Date;
  error?: string;
  rateLimited?: boolean;
  retryAfter?: number; // seconds
}

export interface VerificationValidationResult {
  success: boolean;
  userId?: string;
  error?: string;
  attemptsRemaining?: number;
}

const VERIFICATION_EXPIRY_MINUTES = {
  email_registration: 60 * 24, // 24 hours
  phone_registration: 15, // 15 minutes
  password_reset: 60, // 1 hour
  phone_change: 15,
  email_change: 60,
  login_2fa: 10, // 10 minutes
};

const MAX_ATTEMPTS = {
  email_registration: 5,
  phone_registration: 3,
  password_reset: 5,
  phone_change: 3,
  email_change: 5,
  login_2fa: 3,
};

const RATE_LIMIT_WINDOW_MINUTES = 60; // 1 hour
const RATE_LIMIT_MAX_REQUESTS = {
  email_registration: 5,
  phone_registration: 3,
  password_reset: 3,
  phone_change: 2,
  email_change: 3,
  login_2fa: 5,
};

class VerificationService {
  
  /**
   * Create a new verification token
   */
  async createVerification(request: VerificationRequest): Promise<VerificationResult> {
    const { userId, type, email, phone, ipAddress, userAgent } = request;
    
    // Check rate limiting
    const rateLimitResult = await this.checkRateLimit(
      email || phone || `${ipAddress}:${type}`,
      type
    );
    
    if (!rateLimitResult.allowed) {
      return {
        success: false,
        error: 'Rate limit exceeded',
        rateLimited: true,
        retryAfter: rateLimitResult.retryAfter,
      };
    }
    
    // Generate token and code
    const token = generateRandomString(64);
    const code = type.includes('phone') ? generateVerificationCode() : generateRandomString(32);
    
    const expiresAt = new Date(Date.now() + VERIFICATION_EXPIRY_MINUTES[type] * 60 * 1000);
    const maxAttempts = MAX_ATTEMPTS[type];
    
    try {
      // Create verification token in database
      await db.insert(verificationTokens).values({
        userId,
        type,
        email,
        phone,
        token,
        code,
        maxAttempts,
        expiresAt,
        ipAddress,
        userAgent,
      });
      
      // Send verification based on type
      if (type.includes('email') && email) {
        await this.sendEmailVerification(email, code, type, userId);
      } else if (type.includes('phone') && phone) {
        await this.sendSmsVerification(phone, code, type);
      }
      
      // Update rate limiting
      await this.updateRateLimit(email || phone || `${ipAddress}:${type}`, type);
      
      return {
        success: true,
        token,
        expiresAt,
      };
      
    } catch (error) {
      console.error('Failed to create verification:', error);
      return {
        success: false,
        error: 'Failed to create verification',
      };
    }
  }
  
  /**
   * Validate a verification token and code
   */
  async validateVerification(token: string, code: string): Promise<VerificationValidationResult> {
    try {
      // Find verification token
      const verification = await db.query.verificationTokens.findFirst({
        where: eq(verificationTokens.token, token),
      });
      
      if (!verification) {
        return {
          success: false,
          error: 'Invalid verification token',
        };
      }
      
      // Check if expired
      if (new Date() > verification.expiresAt) {
        await this.cleanupExpiredToken(verification.id);
        return {
          success: false,
          error: 'Verification token expired',
        };
      }
      
      // Check if already verified
      if (verification.status === 'verified') {
        return {
          success: false,
          error: 'Verification already completed',
        };
      }
      
      // Check attempt count
      if (verification.attemptCount >= verification.maxAttempts) {
        await db.update(verificationTokens)
          .set({ status: 'failed' })
          .where(eq(verificationTokens.id, verification.id));
          
        return {
          success: false,
          error: 'Maximum verification attempts exceeded',
        };
      }
      
      // Increment attempt count
      await db.update(verificationTokens)
        .set({ 
          attemptCount: verification.attemptCount + 1,
          updatedAt: new Date(),
        })
        .where(eq(verificationTokens.id, verification.id));
      
      // Check if code matches
      if (verification.code !== code) {
        const attemptsRemaining = verification.maxAttempts - (verification.attemptCount + 1);
        
        return {
          success: false,
          error: 'Invalid verification code',
          attemptsRemaining: Math.max(0, attemptsRemaining),
        };
      }
      
      // Mark as verified
      await db.update(verificationTokens)
        .set({
          status: 'verified',
          verifiedAt: new Date(),
          updatedAt: new Date(),
        })
        .where(eq(verificationTokens.id, verification.id));
      
      return {
        success: true,
        userId: verification.userId,
      };
      
    } catch (error) {
      console.error('Failed to validate verification:', error);
      return {
        success: false,
        error: 'Verification validation failed',
      };
    }
  }
  
  /**
   * Check rate limiting for verification requests
   */
  private async checkRateLimit(identifier: string, type: VerificationType): Promise<{
    allowed: boolean;
    retryAfter?: number;
  }> {
    const windowStart = new Date(Date.now() - RATE_LIMIT_WINDOW_MINUTES * 60 * 1000);
    
    try {
      // Find existing rate limit record
      const rateLimit = await db.query.verificationRateLimit.findFirst({
        where: and(
          eq(verificationRateLimit.identifier, identifier),
          eq(verificationRateLimit.type, type),
          gte(verificationRateLimit.windowStart, windowStart)
        ),
      });
      
      const maxRequests = RATE_LIMIT_MAX_REQUESTS[type];
      
      if (!rateLimit) {
        // First request in this window
        return { allowed: true };
      }
      
      // Check if blocked
      if (rateLimit.blockedUntil && new Date() < rateLimit.blockedUntil) {
        const retryAfter = Math.ceil((rateLimit.blockedUntil.getTime() - Date.now()) / 1000);
        return { allowed: false, retryAfter };
      }
      
      // Check attempt count
      if (rateLimit.attemptCount >= maxRequests) {
        // Block for the remainder of the window
        const blockedUntil = new Date(rateLimit.windowStart.getTime() + RATE_LIMIT_WINDOW_MINUTES * 60 * 1000);
        
        await db.update(verificationRateLimit)
          .set({ blockedUntil })
          .where(eq(verificationRateLimit.id, rateLimit.id));
        
        const retryAfter = Math.ceil((blockedUntil.getTime() - Date.now()) / 1000);
        return { allowed: false, retryAfter };
      }
      
      return { allowed: true };
      
    } catch (error) {
      console.error('Rate limit check failed:', error);
      return { allowed: true }; // Fail open
    }
  }
  
  /**
   * Update rate limiting counters
   */
  private async updateRateLimit(identifier: string, type: VerificationType): Promise<void> {
    const windowStart = new Date(Date.now() - RATE_LIMIT_WINDOW_MINUTES * 60 * 1000);
    
    try {
      const existingRecord = await db.query.verificationRateLimit.findFirst({
        where: and(
          eq(verificationRateLimit.identifier, identifier),
          eq(verificationRateLimit.type, type),
          gte(verificationRateLimit.windowStart, windowStart)
        ),
      });
      
      if (existingRecord) {
        // Update existing record
        await db.update(verificationRateLimit)
          .set({
            attemptCount: existingRecord.attemptCount + 1,
            updatedAt: new Date(),
          })
          .where(eq(verificationRateLimit.id, existingRecord.id));
      } else {
        // Create new record
        await db.insert(verificationRateLimit).values({
          identifier,
          type,
          attemptCount: 1,
          windowStart: new Date(),
        });
      }
    } catch (error) {
      console.error('Failed to update rate limit:', error);
    }
  }
  
  /**
   * Send email verification
   */
  private async sendEmailVerification(email: string, code: string, type: VerificationType, userId?: string): Promise<void> {
    try {
      let emailType: EmailType;
      let templateData: any = { code };
      
      if (userId) {
        const user = await db.query.users.findFirst({
          where: eq(users.id, userId),
        });
        if (user) {
          templateData.name = user.name || user.fullName;
        }
      }
      
      switch (type) {
        case 'email_registration':
          emailType = EmailType.EMAIL_VERIFICATION;
          templateData.verificationToken = code;
          break;
        case 'password_reset':
          emailType = EmailType.PASSWORD_RESET;
          templateData.resetToken = code;
          break;
        default:
          emailType = EmailType.EMAIL_VERIFICATION;
      }
      
      await sendEmail(emailType, email, templateData);
      
      // Log email
      await db.insert(emailLogs).values({
        email,
        subject: `Verification code for ${type}`,
        templateName: emailType,
        status: 'sent',
      });
      
    } catch (error) {
      console.error(`Failed to send ${type} email to ${email}:`, error);
      
      // Log failed email
      await db.insert(emailLogs).values({
        email,
        subject: `Verification code for ${type}`,
        status: 'failed',
        statusMessage: error.message,
        failedAt: new Date(),
      });
      
      throw error;
    }
  }
  
  /**
   * Send SMS verification
   */
  private async sendSmsVerification(phone: string, code: string, type: VerificationType): Promise<void> {
    try {
      let result;
      
      switch (type) {
        case 'phone_registration':
          result = await smsService.sendVerificationSms(phone, code);
          break;
        case 'password_reset':
          result = await smsService.sendPasswordResetSms(phone, code);
          break;
        default:
          result = await smsService.sendVerificationSms(phone, code);
      }
      
      // Log SMS
      await db.insert(smsLogs).values({
        phone,
        message: `Verification code: ${code}`,
        provider: smsService.getProviderName(),
        providerId: result.messageId,
        status: result.success ? 'sent' : 'failed',
        statusMessage: result.error,
        cost: result.cost,
        failedAt: result.success ? undefined : new Date(),
      });
      
      if (!result.success) {
        throw new Error(result.error || 'SMS sending failed');
      }
      
    } catch (error) {
      console.error(`Failed to send ${type} SMS to ${phone}:`, error);
      throw error;
    }
  }
  
  /**
   * Clean up expired token
   */
  private async cleanupExpiredToken(tokenId: string): Promise<void> {
    try {
      await db.update(verificationTokens)
        .set({ status: 'expired' })
        .where(eq(verificationTokens.id, tokenId));
    } catch (error) {
      console.error('Failed to cleanup expired token:', error);
    }
  }
  
  /**
   * Clean up old verification tokens and rate limit records
   */
  async cleanupExpiredRecords(): Promise<void> {
    try {
      const cutoffDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
      
      // Delete old verification tokens
      await db.delete(verificationTokens)
        .where(
          and(
            eq(verificationTokens.status, 'expired'),
            gte(cutoffDate, verificationTokens.expiresAt)
          )
        );
      
      // Delete old rate limit records
      const rateLimitCutoff = new Date(Date.now() - RATE_LIMIT_WINDOW_MINUTES * 60 * 1000);
      await db.delete(verificationRateLimit)
        .where(gte(rateLimitCutoff, verificationRateLimit.windowStart));
      
      console.log('Cleaned up expired verification records');
      
    } catch (error) {
      console.error('Failed to cleanup expired records:', error);
    }
  }
}

// Export singleton instance
export const verificationService = new VerificationService();