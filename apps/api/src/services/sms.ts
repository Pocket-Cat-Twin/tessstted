import { z } from "zod";

export interface SmsProvider {
  name: string;
  sendSms(phone: string, message: string): Promise<SmsResult>;
  getDeliveryStatus?(messageId: string): Promise<SmsDeliveryStatus>;
}

export interface SmsResult {
  success: boolean;
  messageId?: string;
  error?: string;
  cost?: string;
}

export interface SmsDeliveryStatus {
  messageId: string;
  status: "sent" | "delivered" | "failed" | "pending";
  timestamp?: Date;
  error?: string;
}

// Mock SMS provider for development/testing
class MockSmsProvider implements SmsProvider {
  name = "mock";

  async sendSms(phone: string, message: string): Promise<SmsResult> {
    console.log(`[MOCK SMS] Sending to ${phone}: ${message}`);

    // Simulate different scenarios based on phone number
    if (phone.includes("error")) {
      return {
        success: false,
        error: "Mock SMS delivery failed",
      };
    }

    // Simulate successful delivery
    return {
      success: true,
      messageId: `mock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      cost: "0.05",
    };
  }

  async getDeliveryStatus(messageId: string): Promise<SmsDeliveryStatus> {
    return {
      messageId,
      status: "delivered",
      timestamp: new Date(),
    };
  }
}

// SMS.ru provider implementation (popular in Russia)
class SmsRuProvider implements SmsProvider {
  name = "sms.ru";
  private apiId: string;
  private apiKey?: string;
  private from?: string;

  constructor(config: { apiId: string; apiKey?: string; from?: string }) {
    this.apiId = config.apiId;
    this.apiKey = config.apiKey;
    this.from = config.from;
  }

  async sendSms(phone: string, message: string): Promise<SmsResult> {
    try {
      const params = new URLSearchParams({
        api_id: this.apiId,
        to: this.normalizePhone(phone),
        msg: message,
        json: "1",
      });

      if (this.from) {
        params.append("from", this.from);
      }

      const response = await fetch("https://sms.ru/sms/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params.toString(),
      });

      const data = await response.json() as {
        status: string;
        status_text?: string;
        sms?: Record<string, {
          status: string;
          status_text?: string;
          sms_id?: string;
          cost?: string;
        }>;
      };

      if (data.status === "OK") {
        // Get the first phone number's result
        const phoneResult = data.sms ? Object.values(data.sms)[0] : null;

        if (phoneResult && phoneResult.status === "OK") {
          return {
            success: true,
            messageId: phoneResult.sms_id,
            cost: phoneResult.cost,
          };
        } else {
          return {
            success: false,
            error: `SMS.ru error: ${phoneResult?.status_text || 'Unknown error'}`,
          };
        }
      } else {
        return {
          success: false,
          error: `SMS.ru API error: ${data.status_text}`,
        };
      }
    } catch (error) {
      return {
        success: false,
        error: `SMS.ru request failed: ${(error as Error).message}`,
      };
    }
  }

  private normalizePhone(phone: string): string {
    // Remove all non-digits
    const digits = phone.replace(/\D/g, "");

    // Handle Russian phone numbers
    if (digits.startsWith("8") && digits.length === 11) {
      return "7" + digits.slice(1);
    }
    if (digits.startsWith("7") && digits.length === 11) {
      return digits;
    }

    // Return as-is if format is unknown
    return digits;
  }
}

// SMS service singleton
class SmsService {
  private provider: SmsProvider;

  constructor() {
    this.provider = this.createProvider();
  }

  private createProvider(): SmsProvider {
    const provider = process.env.SMS_PROVIDER || "mock";

    switch (provider) {
      case "sms.ru": {
        const apiId = process.env.SMS_RU_API_ID;
        if (!apiId) {
          console.warn(
            "SMS_RU_API_ID not found, falling back to mock provider",
          );
          return new MockSmsProvider();
        }

        return new SmsRuProvider({
          apiId,
          apiKey: process.env.SMS_RU_API_KEY,
          from: process.env.SMS_RU_FROM,
        });
      }

      case "mock":
      default:
        return new MockSmsProvider();
    }
  }

  async sendVerificationSms(phone: string, code: string): Promise<SmsResult> {
    const message = `Ваш код подтверждения для YuYu Lolita: ${code}. Никому не сообщайте этот код.`;

    console.log(`Sending verification SMS to ${phone}: ${code}`);

    const result = await this.provider.sendSms(phone, message);

    if (result.success) {
      console.log(
        `SMS sent successfully to ${phone}, message ID: ${result.messageId}`,
      );
    } else {
      console.error(`Failed to send SMS to ${phone}: ${result.error}`);
    }

    return result;
  }

  async sendPasswordResetSms(phone: string, code: string): Promise<SmsResult> {
    const message = `Код для сброса пароля YuYu Lolita: ${code}. Если вы не запрашивали сброс пароля, игнорируйте это сообщение.`;

    console.log(`Sending password reset SMS to ${phone}: ${code}`);

    return await this.provider.sendSms(phone, message);
  }

  async sendNotificationSms(
    phone: string,
    message: string,
  ): Promise<SmsResult> {
    console.log(
      `Sending notification SMS to ${phone}: ${message.substring(0, 50)}...`,
    );

    return await this.provider.sendSms(phone, message);
  }

  async getDeliveryStatus(
    messageId: string,
  ): Promise<SmsDeliveryStatus | null> {
    if (this.provider.getDeliveryStatus) {
      return await this.provider.getDeliveryStatus(messageId);
    }
    return null;
  }

  getProviderName(): string {
    return this.provider.name;
  }
}

// Export singleton instance
export const smsService = new SmsService();

// Export types and validation schemas
export const smsResultSchema = z.object({
  success: z.boolean(),
  messageId: z.string().optional(),
  error: z.string().optional(),
  cost: z.string().optional(),
});

export const phoneNumberSchema = z
  .string()
  .regex(/^\+?[\d\s\-()]{10,15}$/, "Invalid phone number format");

// Utility function to generate verification codes
export function generateVerificationCode(): string {
  return Math.floor(1000 + Math.random() * 9000).toString();
}
