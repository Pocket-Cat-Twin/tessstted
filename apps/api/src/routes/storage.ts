import { Elysia, t } from 'elysia';
import { requireAuth, requireAdmin } from '../middleware/auth';
import { subscriptionMiddleware } from '../middleware/subscription';
import { NotFoundError, ValidationError, ForbiddenError } from '../middleware/error';
import { storageService } from '../services/storage';

export const storageRoutes = new Elysia({ prefix: '/storage' })

  // Get storage tiers info (public)
  .get('/tiers', async () => {
    return {
      success: true,
      data: {
        tiers: [
          {
            id: 'free',
            name: 'Обычный подписчик',
            maxStorageDays: 14,
            description: 'Хранение на складе до 14 дней',
            features: ['Базовое хранение', 'Уведомления об истечении'],
          },
          {
            id: 'group',
            name: 'Групповая подписка',
            maxStorageDays: 90,
            description: 'Хранение на складе до 3 месяцев',
            features: ['Продленное хранение', 'Приоритетные уведомления', 'Объединение посылок'],
          },
          {
            id: 'elite',
            name: 'Элитный подписчик',
            maxStorageDays: -1,
            description: 'Неограниченное хранение',
            features: ['Безлимитное хранение', 'Персональный менеджер', 'Гибкие условия'],
          },
          {
            id: 'vip_temp',
            name: 'Разовый VIP-доступ',
            maxStorageDays: 30,
            description: 'Хранение до 30 дней (ограниченный период)',
            features: ['VIP хранение', 'Ускоренная обработка', 'Временный доступ'],
          },
        ],
      },
    };
  }, {
    detail: {
      summary: 'Get storage tier information',
      description: 'Get storage limits and features for all subscription tiers',
      tags: ['Storage'],
    },
  })

  // User storage management (requires auth)
  .use(requireAuth)
  .use(subscriptionMiddleware)

  // Get user's storage status
  .get('/status', async ({ store }) => {
    const userId = store.user.id;
    const storageInfo = await storageService.getUserStorageInfo(userId);

    return {
      success: true,
      data: { storage: storageInfo },
    };
  }, {
    detail: {
      summary: 'Get user storage status',
      description: 'Get current storage usage, limits, and expiry information',
      tags: ['Storage'],
    },
  })

  // Get user's items in storage
  .get('/items', async ({ store, query }) => {
    const userId = store.user.id;
    const status = query.status as 'approaching_expiry' | 'expired' | undefined;

    const items = await storageService.getStorageItems({ 
      userId,
      status,
    });

    return {
      success: true,
      data: { 
        items,
        count: items.length,
      },
    };
  }, {
    query: t.Object({
      status: t.Optional(t.Union([
        t.Literal('approaching_expiry'),
        t.Literal('expired'),
      ])),
    }),
    detail: {
      summary: 'Get user storage items',
      description: 'Get list of items currently in storage for the user',
      tags: ['Storage'],
    },
  })

  // Get storage warnings for user
  .get('/warnings', async ({ store }) => {
    const userId = store.user.id;
    const storageInfo = await storageService.getUserStorageInfo(userId);

    const warnings: string[] = [];

    if (storageInfo.itemsExpired.length > 0) {
      warnings.push(`У вас ${storageInfo.itemsExpired.length} заказов с истекшим сроком хранения`);
    }

    if (storageInfo.itemsApproachingExpiry.length > 0) {
      warnings.push(`${storageInfo.itemsApproachingExpiry.length} заказов скоро истекут (до 3 дней)`);
    }

    if (storageInfo.nextExpiryDate) {
      const daysUntilNext = Math.ceil((storageInfo.nextExpiryDate.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
      if (daysUntilNext <= 7) {
        warnings.push(`Следующий заказ истекает через ${daysUntilNext} дней`);
      }
    }

    // Tier-specific warnings
    if (storageInfo.currentTier === 'free') {
      warnings.push('Обновите подписку для увеличения срока хранения');
    } else if (storageInfo.currentTier === 'vip_temp') {
      warnings.push('VIP доступ временный - рассмотрите постоянную подписку');
    }

    return {
      success: true,
      data: {
        warnings,
        hasWarnings: warnings.length > 0,
        storageInfo: {
          tier: storageInfo.currentTier,
          itemsCount: storageInfo.itemsInStorage,
          maxDays: storageInfo.maxStorageDays,
        },
      },
    };
  }, {
    detail: {
      summary: 'Get storage warnings',
      description: 'Get current storage warnings and recommendations for user',
      tags: ['Storage'],
    },
  })

  // Admin storage management
  .use(requireAdmin)

  // Get all storage statistics
  .get('/admin/stats', async () => {
    const stats = await storageService.getStorageStats();

    return {
      success: true,
      data: { stats },
    };
  }, {
    detail: {
      summary: 'Get storage statistics (Admin)',
      description: 'Get comprehensive storage statistics and metrics',
      tags: ['Storage'],
    },
  })

  // Get all items in storage with filtering
  .get('/admin/items', async ({ query }) => {
    const filters: any = {};

    if (query.tier) {
      filters.tier = query.tier;
    }
    if (query.status) {
      filters.status = query.status;
    }
    if (query.userId) {
      filters.userId = query.userId;
    }

    const items = await storageService.getStorageItems(filters);

    return {
      success: true,
      data: {
        items,
        count: items.length,
        filters: filters,
      },
    };
  }, {
    query: t.Object({
      tier: t.Optional(t.Union([
        t.Literal('free'),
        t.Literal('group'),
        t.Literal('elite'),
        t.Literal('vip_temp'),
      ])),
      status: t.Optional(t.Union([
        t.Literal('approaching_expiry'),
        t.Literal('expired'),
      ])),
      userId: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get all storage items (Admin)',
      description: 'Get filtered list of all items in storage',
      tags: ['Storage'],
    },
  })

  // Process storage expiration notifications
  .post('/admin/process-expirations', async () => {
    const result = await storageService.processStorageExpirations();

    return {
      success: true,
      message: `Processed ${result.processed} storage items`,
      data: {
        notificationsToSend: result.notificationsToSend.length,
        expiredItems: result.expiredItems.length,
        summary: {
          notifications: result.notificationsToSend,
          expired: result.expiredItems.map(item => ({
            orderNumber: item.orderNumber,
            daysOverdue: Math.abs(item.daysUntilExpiry || 0),
            tier: item.subscriptionTier,
          })),
        },
      },
    };
  }, {
    detail: {
      summary: 'Process storage expirations (Admin)',
      description: 'Process expiring storage items and generate notifications',
      tags: ['Storage'],
    },
  })

  // Move specific order from storage to delivery
  .post('/admin/move-to-delivery/:orderId', async ({ params: { orderId }, store }) => {
    const adminUserId = store.user.id;
    const result = await storageService.moveToDelivery(orderId, adminUserId);

    return {
      success: true,
      message: result.message,
      data: { orderId },
    };
  }, {
    params: t.Object({
      orderId: t.String(),
    }),
    detail: {
      summary: 'Move order to delivery (Admin)',
      description: 'Move order from storage to delivery status',
      tags: ['Storage'],
    },
  })

  // Extend storage for specific order
  .post('/admin/extend-storage/:orderId', async ({ params: { orderId }, body, store }) => {
    const adminUserId = store.user.id;
    const result = await storageService.extendStorage(orderId, body.additionalDays, adminUserId);

    return {
      success: true,
      message: result.message,
      data: { 
        orderId,
        additionalDays: body.additionalDays,
      },
    };
  }, {
    params: t.Object({
      orderId: t.String(),
    }),
    body: t.Object({
      additionalDays: t.Number({ minimum: 1, maximum: 365 }),
      reason: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Extend storage time (Admin)',
      description: 'Extend storage time for specific order',
      tags: ['Storage'],
    },
  })

  // Get storage items approaching expiry (for scheduled alerts)
  .get('/admin/expiring-soon', async ({ query }) => {
    const days = parseInt(query.days) || 3;
    
    const items = await storageService.getStorageItems({ 
      status: 'approaching_expiry' 
    });

    // Filter items expiring within specified days
    const expiringSoon = items.filter(item => 
      item.daysUntilExpiry !== null && item.daysUntilExpiry <= days
    );

    return {
      success: true,
      data: {
        items: expiringSoon,
        count: expiringSoon.length,
        daysThreshold: days,
        summary: {
          byTier: expiringSoon.reduce((acc, item) => {
            acc[item.subscriptionTier] = (acc[item.subscriptionTier] || 0) + 1;
            return acc;
          }, {} as Record<string, number>),
        },
      },
    };
  }, {
    query: t.Object({
      days: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get items expiring soon (Admin)',
      description: 'Get items approaching storage expiry within specified days',
      tags: ['Storage'],
    },
  })

  // Bulk operations for storage management
  .post('/admin/bulk-operations', async ({ body, store }) => {
    const adminUserId = store.user.id;
    const { operation, orderIds } = body;

    const results = {
      successful: [] as string[],
      failed: [] as { orderId: string; error: string }[],
    };

    for (const orderId of orderIds) {
      try {
        if (operation === 'move_to_delivery') {
          await storageService.moveToDelivery(orderId, adminUserId);
          results.successful.push(orderId);
        } else if (operation === 'extend_storage') {
          await storageService.extendStorage(orderId, body.additionalDays || 7, adminUserId);
          results.successful.push(orderId);
        } else {
          results.failed.push({ orderId, error: 'Unknown operation' });
        }
      } catch (error) {
        results.failed.push({ 
          orderId, 
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    return {
      success: true,
      message: `Bulk operation completed: ${results.successful.length} successful, ${results.failed.length} failed`,
      data: results,
    };
  }, {
    body: t.Object({
      operation: t.Union([
        t.Literal('move_to_delivery'),
        t.Literal('extend_storage'),
      ]),
      orderIds: t.Array(t.String(), { minItems: 1 }),
      additionalDays: t.Optional(t.Number({ minimum: 1, maximum: 365 })),
    }),
    detail: {
      summary: 'Bulk storage operations (Admin)',
      description: 'Perform bulk operations on multiple storage items',
      tags: ['Storage'],
    },
  });