import { Elysia, t } from 'elysia';
import { requireAdmin } from '../middleware/auth';
import { ValidationError, NotFoundError } from '../middleware/error';
import {
  WebhookEvent,
  createWebhookSubscription,
  updateWebhookSubscription,
  deleteWebhookSubscription,
  getWebhookSubscriptions,
  getWebhookLogs,
  testWebhookEndpoint,
  verifyWebhookSignature,
  sendWebhook,
} from '../services/webhook';
import { db, webhookSubscriptions, eq } from '@yuyu/db';

export const webhookRoutes = new Elysia({ prefix: '/webhooks' })

  // Public webhook receiver endpoint (for external services to send webhooks to us)
  .post('/receive/:provider', async ({ params: { provider }, body, headers, set }) => {
    // This endpoint receives webhooks from external services (payment processors, shipping providers, etc.)
    
    const signature = headers['x-webhook-signature'] || headers['x-signature'];
    const event = headers['x-webhook-event'] || headers['x-event-type'];
    
    // Verify signature based on provider
    let isValid = false;
    const webhookSecret = process.env.WEBHOOK_SECRET || 'default-secret';
    
    if (signature && typeof body === 'string') {
      isValid = verifyWebhookSignature(body, signature, webhookSecret);
    }
    
    if (!isValid) {
      set.status = 401;
      return {
        success: false,
        error: 'Invalid webhook signature',
      };
    }
    
    // Log received webhook
    console.log(`Received webhook from ${provider}:`, { event, body });
    
    // Process webhook based on provider
    try {
      await processExternalWebhook(provider, event, body);
      
      return {
        success: true,
        message: 'Webhook processed successfully',
      };
    } catch (error) {
      set.status = 500;
      return {
        success: false,
        error: 'Failed to process webhook',
        message: error instanceof Error ? error.message : String(error),
      };
    }
  }, {
    params: t.Object({
      provider: t.String(),
    }),
    detail: {
      summary: 'Receive external webhook',
      description: 'Endpoint for receiving webhooks from external services',
      tags: ['Webhooks'],
    },
  })

  // Admin routes for managing webhook subscriptions
  .use(requireAdmin)

  // Get all webhook subscriptions
  .get('/subscriptions', async ({ query }) => {
    const isActive = query.active !== undefined ? query.active === 'true' : undefined;
    
    const subscriptions = await getWebhookSubscriptions(isActive);
    
    return {
      success: true,
      data: subscriptions,
    };
  }, {
    query: t.Object({
      active: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get webhook subscriptions (Admin)',
      description: 'Get all webhook subscriptions with optional filtering',
      tags: ['Webhooks'],
    },
  })

  // Create webhook subscription
  .post('/subscriptions', async ({ body, set }) => {
    const { url, events, secret, headers, maxRetries, timeoutMs } = body;
    
    // Validate URL
    try {
      new URL(url);
    } catch {
      throw new ValidationError('Invalid webhook URL');
    }
    
    // Validate events
    const validEvents = Object.values(WebhookEvent);
    const invalidEvents = events.filter(event => !validEvents.includes(event as WebhookEvent));
    
    if (invalidEvents.length > 0) {
      throw new ValidationError(`Invalid webhook events: ${invalidEvents.join(', ')}`);
    }
    
    // Create subscription
    const subscriptionId = await createWebhookSubscription(
      url,
      events as WebhookEvent[],
      secret,
      headers,
      maxRetries,
      timeoutMs
    );
    
    // Get the created subscription
    const subscription = await db.query.webhookSubscriptions.findFirst({
      where: eq(webhookSubscriptions.id, subscriptionId),
    });
    
    set.status = 201;
    return {
      success: true,
      message: 'Webhook subscription created successfully',
      data: { subscription },
    };
  }, {
    body: t.Object({
      url: t.String({ format: 'uri' }),
      events: t.Array(t.String(), { minItems: 1 }),
      secret: t.Optional(t.String()),
      headers: t.Optional(t.Record(t.String(), t.String())),
      maxRetries: t.Optional(t.Number({ minimum: 0, maximum: 10 })),
      timeoutMs: t.Optional(t.Number({ minimum: 1000, maximum: 120000 })),
    }),
    detail: {
      summary: 'Create webhook subscription (Admin)',
      description: 'Create a new webhook subscription',
      tags: ['Webhooks'],
    },
  })

  // Get webhook subscription by ID
  .get('/subscriptions/:id', async ({ params: { id } }) => {
    const subscription = await db.query.webhookSubscriptions.findFirst({
      where: eq(webhookSubscriptions.id, id),
    });
    
    if (!subscription) {
      throw new NotFoundError('Webhook subscription not found');
    }
    
    return {
      success: true,
      data: { subscription },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Get webhook subscription by ID (Admin)',
      tags: ['Webhooks'],
    },
  })

  // Update webhook subscription
  .put('/subscriptions/:id', async ({ params: { id }, body }) => {
    // Check if subscription exists
    const existingSubscription = await db.query.webhookSubscriptions.findFirst({
      where: eq(webhookSubscriptions.id, id),
    });
    
    if (!existingSubscription) {
      throw new NotFoundError('Webhook subscription not found');
    }
    
    // Validate URL if provided
    if (body.url) {
      try {
        new URL(body.url);
      } catch {
        throw new ValidationError('Invalid webhook URL');
      }
    }
    
    // Validate events if provided
    if (body.events) {
      const validEvents = Object.values(WebhookEvent);
      const invalidEvents = body.events.filter(event => !validEvents.includes(event as WebhookEvent));
      
      if (invalidEvents.length > 0) {
        throw new ValidationError(`Invalid webhook events: ${invalidEvents.join(', ')}`);
      }
    }
    
    // Update subscription
    await updateWebhookSubscription(id, body);
    
    // Get updated subscription
    const updatedSubscription = await db.query.webhookSubscriptions.findFirst({
      where: eq(webhookSubscriptions.id, id),
    });
    
    return {
      success: true,
      message: 'Webhook subscription updated successfully',
      data: { subscription: updatedSubscription },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    body: t.Object({
      url: t.Optional(t.String({ format: 'uri' })),
      events: t.Optional(t.Array(t.String())),
      secret: t.Optional(t.String()),
      headers: t.Optional(t.Record(t.String(), t.String())),
      maxRetries: t.Optional(t.Number({ minimum: 0, maximum: 10 })),
      timeoutMs: t.Optional(t.Number({ minimum: 1000, maximum: 120000 })),
      isActive: t.Optional(t.Boolean()),
    }),
    detail: {
      summary: 'Update webhook subscription (Admin)',
      tags: ['Webhooks'],
    },
  })

  // Delete webhook subscription
  .delete('/subscriptions/:id', async ({ params: { id } }) => {
    // Check if subscription exists
    const subscription = await db.query.webhookSubscriptions.findFirst({
      where: eq(webhookSubscriptions.id, id),
    });
    
    if (!subscription) {
      throw new NotFoundError('Webhook subscription not found');
    }
    
    // Delete subscription
    await deleteWebhookSubscription(id);
    
    return {
      success: true,
      message: 'Webhook subscription deleted successfully',
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Delete webhook subscription (Admin)',
      tags: ['Webhooks'],
    },
  })

  // Test webhook subscription
  .post('/subscriptions/:id/test', async ({ params: { id } }) => {
    // Get subscription
    const subscription = await db.query.webhookSubscriptions.findFirst({
      where: eq(webhookSubscriptions.id, id),
    });
    
    if (!subscription) {
      throw new NotFoundError('Webhook subscription not found');
    }
    
    // Test the endpoint
    const testResult = await testWebhookEndpoint(
      subscription.url,
      subscription.secret,
      subscription.timeoutMs || 10000
    );
    
    return {
      success: true,
      data: { testResult },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Test webhook subscription (Admin)',
      description: 'Send a test webhook to verify the endpoint is working',
      tags: ['Webhooks'],
    },
  })

  // Get webhook logs
  .get('/logs', async ({ query }) => {
    const subscriptionId = query.subscriptionId;
    const limit = parseInt(query.limit) || 100;
    
    const logs = await getWebhookLogs(subscriptionId, limit);
    
    return {
      success: true,
      data: logs,
    };
  }, {
    query: t.Object({
      subscriptionId: t.Optional(t.String()),
      limit: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get webhook logs (Admin)',
      description: 'Get webhook delivery logs with optional filtering',
      tags: ['Webhooks'],
    },
  })

  // Send test webhook
  .post('/test', async ({ body }) => {
    const { event, data } = body;
    
    // Validate event
    if (!Object.values(WebhookEvent).includes(event as WebhookEvent)) {
      throw new ValidationError(`Invalid webhook event: ${event}`);
    }
    
    // Send webhook
    await sendWebhook(event as WebhookEvent, data);
    
    return {
      success: true,
      message: `Test webhook sent for event: ${event}`,
    };
  }, {
    body: t.Object({
      event: t.String(),
      data: t.Record(t.String(), t.Any()),
    }),
    detail: {
      summary: 'Send test webhook (Admin)',
      description: 'Send a test webhook with custom event and data',
      tags: ['Webhooks'],
    },
  })

  // Get available webhook events
  .get('/events', async () => {
    const events = Object.values(WebhookEvent).map(event => ({
      name: event,
      description: getEventDescription(event),
    }));
    
    return {
      success: true,
      data: { events },
    };
  }, {
    detail: {
      summary: 'Get available webhook events (Admin)',
      description: 'Get list of all available webhook events',
      tags: ['Webhooks'],
    },
  })

  // Webhook statistics
  .get('/stats', async ({ query }) => {
    const days = parseInt(query.days) || 7;
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    
    // Get delivery statistics
    const stats = await db.execute(`
      SELECT 
        COUNT(*) as total_deliveries,
        COUNT(CASE WHEN success = true THEN 1 END) as successful_deliveries,
        COUNT(CASE WHEN success = false THEN 1 END) as failed_deliveries,
        AVG(attempts) as avg_attempts,
        COUNT(DISTINCT subscription_id) as active_subscriptions,
        COUNT(DISTINCT event) as unique_events
      FROM webhook_logs 
      WHERE created_at >= $1
    `, [since]);
    
    return {
      success: true,
      data: { 
        stats: stats.rows[0],
        period: { days, since },
      },
    };
  }, {
    query: t.Object({
      days: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get webhook statistics (Admin)',
      description: 'Get webhook delivery statistics',
      tags: ['Webhooks'],
    },
  });

// Process external webhooks from payment providers, shipping services, etc.
async function processExternalWebhook(provider: string, event: string, payload: any) {
  console.log(`Processing webhook from ${provider}:`, { event, payload });
  
  switch (provider) {
    case 'stripe':
      await processStripeWebhook(event, payload);
      break;
    case 'paypal':
      await processPayPalWebhook(event, payload);
      break;
    case 'dhl':
      await processDHLWebhook(event, payload);
      break;
    case 'fedex':
      await processFedExWebhook(event, payload);
      break;
    default:
      console.warn(`Unknown webhook provider: ${provider}`);
  }
}

async function processStripeWebhook(event: string, payload: any) {
  switch (event) {
    case 'payment_intent.succeeded':
      // Handle successful payment
      await sendWebhook(WebhookEvent.PAYMENT_RECEIVED, {
        provider: 'stripe',
        paymentId: payload.id,
        amount: payload.amount,
        currency: payload.currency,
      });
      break;
    case 'payment_intent.payment_failed':
      // Handle failed payment
      await sendWebhook(WebhookEvent.PAYMENT_FAILED, {
        provider: 'stripe',
        paymentId: payload.id,
        error: payload.last_payment_error,
      });
      break;
  }
}

async function processPayPalWebhook(event: string, payload: any) {
  // Handle PayPal webhooks
  console.log('Processing PayPal webhook:', { event, payload });
}

async function processDHLWebhook(event: string, payload: any) {
  // Handle DHL shipping webhooks
  console.log('Processing DHL webhook:', { event, payload });
}

async function processFedExWebhook(event: string, payload: any) {
  // Handle FedEx shipping webhooks
  console.log('Processing FedEx webhook:', { event, payload });
}

function getEventDescription(event: WebhookEvent): string {
  const descriptions: Record<WebhookEvent, string> = {
    [WebhookEvent.ORDER_CREATED]: 'Triggered when a new order is created',
    [WebhookEvent.ORDER_UPDATED]: 'Triggered when order details are updated',
    [WebhookEvent.ORDER_STATUS_CHANGED]: 'Triggered when order status changes',
    [WebhookEvent.ORDER_PAID]: 'Triggered when order payment is confirmed',
    [WebhookEvent.ORDER_SHIPPED]: 'Triggered when order is shipped',
    [WebhookEvent.ORDER_DELIVERED]: 'Triggered when order is delivered',
    [WebhookEvent.ORDER_CANCELLED]: 'Triggered when order is cancelled',
    
    [WebhookEvent.USER_CREATED]: 'Triggered when a new user registers',
    [WebhookEvent.USER_UPDATED]: 'Triggered when user profile is updated',
    [WebhookEvent.USER_BLOCKED]: 'Triggered when user is blocked',
    [WebhookEvent.USER_VERIFIED]: 'Triggered when user email is verified',
    
    [WebhookEvent.SUBSCRIPTION_CREATED]: 'Triggered when a new subscription is created',
    [WebhookEvent.SUBSCRIPTION_RENEWED]: 'Triggered when subscription is renewed',
    [WebhookEvent.SUBSCRIPTION_EXPIRED]: 'Triggered when subscription expires',
    [WebhookEvent.SUBSCRIPTION_CANCELLED]: 'Triggered when subscription is cancelled',
    
    [WebhookEvent.PAYMENT_RECEIVED]: 'Triggered when payment is received',
    [WebhookEvent.PAYMENT_FAILED]: 'Triggered when payment fails',
    [WebhookEvent.PAYMENT_REFUNDED]: 'Triggered when payment is refunded',
    
    [WebhookEvent.INVENTORY_LOW]: 'Triggered when inventory is low',
    [WebhookEvent.INVENTORY_OUT_OF_STOCK]: 'Triggered when item is out of stock',
    
    [WebhookEvent.SYSTEM_MAINTENANCE]: 'Triggered during system maintenance',
    [WebhookEvent.SYSTEM_ERROR]: 'Triggered when system error occurs',
  };
  
  return descriptions[event] || 'No description available';
}