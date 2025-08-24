import crypto from "crypto";
import { db, webhookLogs, webhookSubscriptions, eq, and, sql } from "@yuyu/db";

// Webhook event types
export enum WebhookEvent {
  ORDER_CREATED = "order.created",
  ORDER_UPDATED = "order.updated",
  ORDER_STATUS_CHANGED = "order.status_changed",
  ORDER_PAID = "order.paid",
  ORDER_SHIPPED = "order.shipped",
  ORDER_DELIVERED = "order.delivered",
  ORDER_CANCELLED = "order.cancelled",

  USER_CREATED = "user.created",
  USER_UPDATED = "user.updated",
  USER_BLOCKED = "user.blocked",
  USER_VERIFIED = "user.verified",

  SUBSCRIPTION_CREATED = "subscription.created",
  SUBSCRIPTION_RENEWED = "subscription.renewed",
  SUBSCRIPTION_EXPIRED = "subscription.expired",
  SUBSCRIPTION_CANCELLED = "subscription.cancelled",

  PAYMENT_RECEIVED = "payment.received",
  PAYMENT_FAILED = "payment.failed",
  PAYMENT_REFUNDED = "payment.refunded",

  INVENTORY_LOW = "inventory.low",
  INVENTORY_OUT_OF_STOCK = "inventory.out_of_stock",

  SYSTEM_MAINTENANCE = "system.maintenance",
  SYSTEM_ERROR = "system.error",
}

// Webhook payload interface
export interface WebhookPayload {
  id: string;
  event: WebhookEvent;
  timestamp: string;
  data: Record<string, any>;
  version: string;
}

// Webhook subscription interface
export interface WebhookSubscription {
  id: string;
  url: string;
  events: WebhookEvent[];
  secret: string;
  isActive: boolean;
  headers?: Record<string, string>;
  retryCount: number;
  maxRetries: number;
  timeoutMs: number;
}

// Webhook delivery result
export interface WebhookDeliveryResult {
  success: boolean;
  statusCode?: number;
  response?: string;
  error?: string;
  attempts: number;
  deliveredAt?: Date;
}

// Generate webhook signature
function generateSignature(payload: string, secret: string): string {
  return crypto
    .createHmac("sha256", secret)
    .update(payload, "utf8")
    .digest("hex");
}

// Verify webhook signature
export function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string,
): boolean {
  const expectedSignature = generateSignature(payload, secret);
  const providedSignature = signature.startsWith("sha256=")
    ? signature.slice(7)
    : signature;

  return crypto.timingSafeEqual(
    Buffer.from(expectedSignature, "hex"),
    Buffer.from(providedSignature, "hex"),
  );
}

// Create webhook payload
function createWebhookPayload(
  event: WebhookEvent,
  data: Record<string, any>,
): WebhookPayload {
  return {
    id: crypto.randomUUID(),
    event,
    timestamp: new Date().toISOString(),
    data,
    version: "1.0",
  };
}

// Deliver webhook to a single endpoint
async function deliverWebhook(
  subscription: WebhookSubscription,
  payload: WebhookPayload,
): Promise<WebhookDeliveryResult> {
  const payloadString = JSON.stringify(payload);
  const signature = generateSignature(payloadString, subscription.secret);

  const headers = {
    "Content-Type": "application/json",
    "User-Agent": "YuYu-Lolita-Webhook/1.0",
    "X-Webhook-Signature": `sha256=${signature}`,
    "X-Webhook-Event": payload.event,
    "X-Webhook-ID": payload.id,
    "X-Webhook-Timestamp": payload.timestamp,
    ...subscription.headers,
  };

  let attempts = 0;
  let lastError = "";

  while (attempts < subscription.maxRetries) {
    attempts++;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        subscription.timeoutMs,
      );

      const response = await fetch(subscription.url, {
        method: "POST",
        headers,
        body: payloadString,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const responseText = await response.text();
        return {
          success: true,
          statusCode: response.status,
          response: responseText,
          attempts,
          deliveredAt: new Date(),
        };
      } else {
        lastError = `HTTP ${response.status}: ${response.statusText}`;

        // Don't retry for 4xx errors (client errors)
        if (response.status >= 400 && response.status < 500) {
          break;
        }
      }
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }

    // Exponential backoff for retries
    if (attempts < subscription.maxRetries) {
      const delay = Math.min(1000 * Math.pow(2, attempts - 1), 30000);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  return {
    success: false,
    error: lastError,
    attempts,
  };
}

// Log webhook delivery
async function logWebhookDelivery(
  subscriptionId: string,
  payload: WebhookPayload,
  result: WebhookDeliveryResult,
) {
  try {
    await db.insert(webhookLogs).values({
      subscriptionId,
      event: payload.event,
      payload: JSON.stringify(payload),
      url: "", // Will be set by the subscription
      httpStatus: result.statusCode,
      responseBody: result.response,
      errorMessage: result.error,
      attemptNumber: result.attempts,
      completedAt: result.deliveredAt,
      status: result.success ? "success" : "failed",
    });
  } catch (error) {
    console.error("Failed to log webhook delivery:", error);
  }
}

// Send webhook to all subscribers
export async function sendWebhook(
  event: WebhookEvent,
  data: Record<string, any>,
): Promise<void> {
  try {
    // Get active subscriptions for this event
    const subscriptions = await db.query.webhookSubscriptions.findMany({
      where: and(
        eq(webhookSubscriptions.isActive, true),
        sql`${webhookSubscriptions.events} ? ${event}`,
      ),
    });

    if (subscriptions.length === 0) {
      console.log(`No webhook subscriptions found for event: ${event}`);
      return;
    }

    // Create webhook payload
    const payload = createWebhookPayload(event, data);

    // Deliver webhooks concurrently
    const deliveryPromises = subscriptions.map(async (subscription) => {
      const subscriptionConfig: WebhookSubscription = {
        id: subscription.id,
        url: subscription.url,
        events: subscription.events as WebhookEvent[],
        secret: subscription.secret,
        isActive: subscription.isActive,
        headers: subscription.headers ? JSON.parse(subscription.headers) : {},
        retryCount: subscription.retryCount || 0,
        maxRetries: subscription.maxRetries || 3,
        timeoutMs: 30000, // Default timeout
      };

      const result = await deliverWebhook(subscriptionConfig, payload);

      // Log the delivery result
      await logWebhookDelivery(subscription.id, payload, result);

      // Update retry count if failed
      if (!result.success) {
        await db
          .update(webhookSubscriptions)
          .set({
            retryCount: sql`${webhookSubscriptions.retryCount} + 1`,
            updatedAt: new Date(),
          })
          .where(eq(webhookSubscriptions.id, subscription.id));
      } else {
        // Reset retry count on success
        await db
          .update(webhookSubscriptions)
          .set({
            retryCount: 0,
            lastTriggeredAt: new Date(),
            updatedAt: new Date(),
          })
          .where(eq(webhookSubscriptions.id, subscription.id));
      }

      return { subscriptionId: subscription.id, result };
    });

    const results = await Promise.allSettled(deliveryPromises);

    // Log summary
    const successful = results.filter((r) => r.status === "fulfilled").length;
    const failed = results.length - successful;

    console.log(
      `Webhook delivery summary for ${event}: ${successful} successful, ${failed} failed`,
    );
  } catch (error) {
    console.error("Failed to send webhook:", error);
  }
}

// Convenience functions for common webhook events

export async function sendOrderCreatedWebhook(orderData: any) {
  return sendWebhook(WebhookEvent.ORDER_CREATED, {
    order: orderData,
  });
}

export async function sendOrderStatusChangedWebhook(
  orderData: any,
  oldStatus: string,
  newStatus: string,
) {
  return sendWebhook(WebhookEvent.ORDER_STATUS_CHANGED, {
    order: orderData,
    oldStatus,
    newStatus,
    changedAt: new Date().toISOString(),
  });
}

export async function sendUserCreatedWebhook(userData: any) {
  return sendWebhook(WebhookEvent.USER_CREATED, {
    user: userData,
  });
}

export async function sendSubscriptionExpiredWebhook(subscriptionData: any) {
  return sendWebhook(WebhookEvent.SUBSCRIPTION_EXPIRED, {
    subscription: subscriptionData,
  });
}

export async function sendPaymentReceivedWebhook(paymentData: any) {
  return sendWebhook(WebhookEvent.PAYMENT_RECEIVED, {
    payment: paymentData,
  });
}

export async function sendInventoryLowWebhook(inventoryData: any) {
  return sendWebhook(WebhookEvent.INVENTORY_LOW, {
    inventory: inventoryData,
  });
}

export async function sendSystemErrorWebhook(errorData: any) {
  return sendWebhook(WebhookEvent.SYSTEM_ERROR, {
    error: errorData,
    timestamp: new Date().toISOString(),
  });
}

// Webhook management functions

export async function createWebhookSubscription(
  url: string,
  events: WebhookEvent[],
  secret?: string,
  headers?: Record<string, string>,
  maxRetries = 3,
  timeoutMs = 30000,
): Promise<string> {
  const subscriptionSecret = secret || crypto.randomBytes(32).toString("hex");

  const [subscription] = await db
    .insert(webhookSubscriptions)
    .values({
      url,
      events: JSON.stringify(events),
      secret: subscriptionSecret,
      headers: headers ? JSON.stringify(headers) : null,
      maxRetries,
      isActive: true,
    })
    .returning();

  return subscription.id;
}

export async function updateWebhookSubscription(
  subscriptionId: string,
  updates: Partial<{
    url: string;
    events: WebhookEvent[];
    secret: string;
    headers: Record<string, string>;
    maxRetries: number;
    timeoutMs: number;
    isActive: boolean;
  }>,
): Promise<void> {
  const updateData: any = {};

  if (updates.url) updateData.url = updates.url;
  if (updates.events) updateData.events = JSON.stringify(updates.events);
  if (updates.secret) updateData.secret = updates.secret;
  if (updates.headers) updateData.headers = JSON.stringify(updates.headers);
  if (updates.maxRetries !== undefined)
    updateData.maxRetries = updates.maxRetries;
  if (updates.timeoutMs !== undefined) updateData.timeoutMs = updates.timeoutMs;
  if (updates.isActive !== undefined) updateData.isActive = updates.isActive;

  updateData.updatedAt = new Date();

  await db
    .update(webhookSubscriptions)
    .set(updateData)
    .where(eq(webhookSubscriptions.id, subscriptionId));
}

export async function deleteWebhookSubscription(
  subscriptionId: string,
): Promise<void> {
  await db
    .delete(webhookSubscriptions)
    .where(eq(webhookSubscriptions.id, subscriptionId));
}

export async function getWebhookSubscriptions(isActive?: boolean) {
  const conditions = [];
  if (isActive !== undefined) {
    conditions.push(eq(webhookSubscriptions.isActive, isActive));
  }

  return db.query.webhookSubscriptions.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [webhookSubscriptions.createdAt],
  });
}

export async function getWebhookLogs(subscriptionId?: string, limit = 100) {
  const conditions = [];
  if (subscriptionId) {
    conditions.push(eq(webhookLogs.subscriptionId, subscriptionId));
  }

  return db.query.webhookLogs.findMany({
    where: conditions.length > 0 ? and(...conditions) : undefined,
    orderBy: [webhookLogs.createdAt],
    limit,
  });
}

// Test webhook endpoint
export async function testWebhookEndpoint(
  url: string,
  secret: string,
  timeoutMs = 10000,
): Promise<{ success: boolean; error?: string; responseTime: number }> {
  const startTime = Date.now();

  try {
    const testPayload = createWebhookPayload(WebhookEvent.SYSTEM_MAINTENANCE, {
      test: true,
      message: "Webhook endpoint test",
    });

    const payloadString = JSON.stringify(testPayload);
    const signature = generateSignature(payloadString, secret);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Webhook-Signature": `sha256=${signature}`,
        "X-Webhook-Event": testPayload.event,
        "X-Webhook-ID": testPayload.id,
        "X-Webhook-Test": "true",
      },
      body: payloadString,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const responseTime = Date.now() - startTime;

    if (response.ok) {
      return { success: true, responseTime };
    } else {
      return {
        success: false,
        error: `HTTP ${response.status}: ${response.statusText}`,
        responseTime,
      };
    }
  } catch (error) {
    const responseTime = Date.now() - startTime;
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
      responseTime,
    };
  }
}
