import { Elysia, t } from 'elysia';
import { 
  db, 
  orders, 
  orderGoods, 
  orderStatusHistory,
  users,
  config,
  eq, 
  and, 
  desc, 
  asc,
  sql
} from '@yuyu/db';
import { 
  orderCreateSchema, 
  orderUpdateSchema,
  orderGoodCreateSchema,
  orderGoodUpdateSchema,
  orderLookupSchema,
  OrderStatus,
  generateOrderNomerok,
  calculateOrderTotals
} from '@yuyu/shared';
import { requireAuth, requireAdmin } from '../middleware/auth';
import { NotFoundError, ValidationError, ForbiddenError } from '../middleware/error';
import { sendOrderCreatedEmail } from '../services/email';

export const orderRoutes = new Elysia({ prefix: '/orders' })
  
  // Public order lookup by nomerok
  .get('/lookup/:nomerok', async ({ params: { nomerok }, set }) => {
    const order = await db.query.orders.findFirst({
      where: eq(orders.nomerok, nomerok),
      with: {
        goods: true,
        statusHistory: {
          with: {
            user: {
              columns: {
                name: true,
              },
            },
          },
          orderBy: desc(orderStatusHistory.createdAt),
        },
      },
    });

    if (!order) {
      throw new NotFoundError('Order not found');
    }

    // Remove sensitive information for public lookup
    const publicOrder = {
      id: order.id,
      nomerok: order.nomerok,
      customerName: order.customerName,
      status: order.status,
      totalRuble: order.totalRuble,
      createdAt: order.createdAt,
      goods: order.goods?.map(good => ({
        name: good.name,
        quantity: good.quantity,
        priceYuan: good.priceYuan,
        totalRuble: good.totalRuble,
      })),
      statusHistory: order.statusHistory?.map(history => ({
        fromStatus: history.fromStatus,
        toStatus: history.toStatus,
        comment: history.comment,
        createdAt: history.createdAt,
        updatedBy: history.user?.name,
      })),
    };

    return {
      success: true,
      data: { order: publicOrder },
    };
  }, {
    params: t.Object({
      nomerok: t.String(),
    }),
    detail: {
      summary: 'Lookup order by nomerok',
      tags: ['Orders'],
    },
  })

  // Create new order (public)
  .post('/', async ({ body, set }) => {
    const validation = orderCreateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid order data');
    }

    const orderData = validation.data;

    // Get current exchange rate
    const kursConfig = await db.query.config.findFirst({
      where: eq(config.key, 'current_kurs'),
    });
    const currentKurs = kursConfig ? parseFloat(kursConfig.value) : 13.5;

    // Get commission rate
    const commissionConfig = await db.query.config.findFirst({
      where: eq(config.key, 'default_commission_rate'),
    });
    const commissionRate = commissionConfig ? parseFloat(commissionConfig.value) : 0.1;

    // Calculate totals
    const totals = calculateOrderTotals(
      orderData.goods,
      currentKurs,
      commissionRate
    );

    // Generate unique nomerok
    const nomerok = generateOrderNomerok();

    // Create order
    const [newOrder] = await db.insert(orders).values({
      nomerok,
      customerName: orderData.customerName,
      customerPhone: orderData.customerPhone,
      customerEmail: orderData.customerEmail,
      deliveryAddress: orderData.deliveryAddress,
      deliveryMethod: orderData.deliveryMethod,
      paymentMethod: orderData.paymentMethod,
      subtotalYuan: totals.subtotalYuan,
      totalCommission: totals.totalCommission,
      currentKurs,
      totalYuan: totals.totalYuan,
      totalRuble: totals.totalRuble,
      status: OrderStatus.CREATED,
    }).returning();

    // Create order goods
    const orderGoodsData = orderData.goods.map(good => {
      const goodTotal = good.quantity * good.priceYuan;
      const goodCommission = goodTotal * commissionRate;
      const goodTotalYuan = goodTotal + goodCommission;
      const goodTotalRuble = goodTotalYuan * currentKurs;

      return {
        orderId: newOrder.id,
        name: good.name,
        link: good.link,
        quantity: good.quantity,
        priceYuan: good.priceYuan,
        commission: goodCommission,
        totalYuan: goodTotalYuan,
        totalRuble: goodTotalRuble,
      };
    });

    await db.insert(orderGoods).values(orderGoodsData);

    // Create status history entry
    await db.insert(orderStatusHistory).values({
      orderId: newOrder.id,
      toStatus: OrderStatus.CREATED,
      comment: 'Заказ создан',
    });

    // Send notification email if email provided
    if (orderData.customerEmail) {
      try {
        await sendOrderCreatedEmail(
          orderData.customerEmail,
          orderData.customerName,
          nomerok,
          totals.finalTotal
        );
      } catch (error) {
        console.error('Failed to send order notification email:', error);
        // Don't fail order creation if email fails
      }
    }

    set.status = 201;
    return {
      success: true,
      message: 'Order created successfully',
      data: { 
        order: newOrder,
        lookupUrl: `/orders/lookup/${nomerok}`,
      },
    };
  }, {
    body: t.Object({
      customerName: t.String({ minLength: 1 }),
      customerPhone: t.String({ minLength: 1 }),
      customerEmail: t.Optional(t.String({ format: 'email' })),
      deliveryAddress: t.String({ minLength: 1 }),
      deliveryMethod: t.String({ minLength: 1 }),
      paymentMethod: t.String({ minLength: 1 }),
      goods: t.Array(t.Object({
        name: t.String({ minLength: 1 }),
        link: t.Optional(t.String()),
        quantity: t.Number({ minimum: 1 }),
        priceYuan: t.Number({ minimum: 0 }),
      }), { minItems: 1 }),
    }),
    detail: {
      summary: 'Create new order',
      tags: ['Orders'],
    },
  })

  // Admin routes
  .use(requireAdmin)

  // Get all orders with pagination and filtering
  .get('/', async ({ query }) => {
    const page = parseInt(query.page) || 1;
    const limit = parseInt(query.limit) || 10;
    const status = query.status as OrderStatus;
    const search = query.search;
    const offset = (page - 1) * limit;

    // Build where conditions
    const conditions = [];
    if (status) {
      conditions.push(eq(orders.status, status));
    }
    if (search) {
      conditions.push(
        sql`(${orders.nomerok} ILIKE ${`%${search}%`} OR ${orders.customerName} ILIKE ${`%${search}%`})`
      );
    }

    const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

    // Get orders
    const ordersResult = await db.query.orders.findMany({
      where: whereClause,
      with: {
        goods: true,
        user: {
          columns: {
            name: true,
            email: true,
          },
        },
      },
      orderBy: desc(orders.createdAt),
      limit,
      offset,
    });

    // Get total count
    const [{ count }] = await db
      .select({ count: sql<number>`count(*)` })
      .from(orders)
      .where(whereClause);

    const totalPages = Math.ceil(count / limit);

    return {
      success: true,
      data: ordersResult,
      pagination: {
        page,
        limit,
        total: count,
        totalPages,
        hasNext: page < totalPages,
        hasPrev: page > 1,
      },
    };
  }, {
    query: t.Object({
      page: t.Optional(t.String()),
      limit: t.Optional(t.String()),
      status: t.Optional(t.String()),
      search: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get all orders (Admin)',
      tags: ['Orders'],
    },
  })

  // Get order by ID
  .get('/:id', async ({ params: { id } }) => {
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, id),
      with: {
        goods: true,
        user: {
          columns: {
            name: true,
            email: true,
          },
        },
        statusHistory: {
          with: {
            user: {
              columns: {
                name: true,
              },
            },
          },
          orderBy: desc(orderStatusHistory.createdAt),
        },
      },
    });

    if (!order) {
      throw new NotFoundError('Order not found');
    }

    return {
      success: true,
      data: { order },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Get order by ID (Admin)',
      tags: ['Orders'],
    },
  })

  // Update order
  .put('/:id', async ({ params: { id }, body, user }) => {
    const validation = orderUpdateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid order update data');
    }

    const updateData = validation.data;

    // Find existing order
    const existingOrder = await db.query.orders.findFirst({
      where: eq(orders.id, id),
    });

    if (!existingOrder) {
      throw new NotFoundError('Order not found');
    }

    // Track status change
    const statusChanged = updateData.status && updateData.status !== existingOrder.status;

    // Update order
    const [updatedOrder] = await db.update(orders)
      .set({
        ...updateData,
        updatedAt: new Date(),
      })
      .where(eq(orders.id, id))
      .returning();

    // Add status history if status changed
    if (statusChanged && updateData.status) {
      await db.insert(orderStatusHistory).values({
        orderId: id,
        userId: user.id,
        fromStatus: existingOrder.status,
        toStatus: updateData.status,
        comment: updateData.notes || 'Статус изменен администратором',
      });
    }

    return {
      success: true,
      message: 'Order updated successfully',
      data: { order: updatedOrder },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    body: t.Object({
      customerName: t.Optional(t.String()),
      customerPhone: t.Optional(t.String()),
      customerEmail: t.Optional(t.String()),
      deliveryAddress: t.Optional(t.String()),
      deliveryMethod: t.Optional(t.String()),
      deliveryCost: t.Optional(t.Number()),
      paymentMethod: t.Optional(t.String()),
      paymentScreenshot: t.Optional(t.String()),
      discount: t.Optional(t.Number()),
      status: t.Optional(t.String()),
      notes: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Update order (Admin)',
      tags: ['Orders'],
    },
  })

  // Delete order
  .delete('/:id', async ({ params: { id } }) => {
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, id),
    });

    if (!order) {
      throw new NotFoundError('Order not found');
    }

    // Delete order (cascades to goods and status history)
    await db.delete(orders).where(eq(orders.id, id));

    return {
      success: true,
      message: 'Order deleted successfully',
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Delete order (Admin)',
      tags: ['Orders'],
    },
  })

  // Order goods management
  .post('/:orderId/goods', async ({ params: { orderId }, body }) => {
    const validation = orderGoodCreateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid order good data');
    }

    const goodData = validation.data;

    // Check if order exists
    const order = await db.query.orders.findFirst({
      where: eq(orders.id, orderId),
    });

    if (!order) {
      throw new NotFoundError('Order not found');
    }

    // Calculate good totals
    const goodTotal = goodData.quantity * goodData.priceYuan;
    const commissionRate = 0.1; // Get from config
    const goodCommission = goodTotal * commissionRate;
    const goodTotalYuan = goodTotal + goodCommission;
    const goodTotalRuble = goodTotalYuan * order.currentKurs;

    // Create order good
    const [newGood] = await db.insert(orderGoods).values({
      orderId,
      name: goodData.name,
      link: goodData.link,
      quantity: goodData.quantity,
      priceYuan: goodData.priceYuan,
      commission: goodCommission,
      totalYuan: goodTotalYuan,
      totalRuble: goodTotalRuble,
    }).returning();

    // Recalculate order totals
    const allGoods = await db.query.orderGoods.findMany({
      where: eq(orderGoods.orderId, orderId),
    });

    const totals = calculateOrderTotals(
      allGoods.map(g => ({ quantity: g.quantity, priceYuan: g.priceYuan })),
      order.currentKurs,
      commissionRate,
      Number(order.deliveryCost),
      Number(order.discount)
    );

    // Update order totals
    await db.update(orders)
      .set({
        subtotalYuan: totals.subtotalYuan,
        totalCommission: totals.totalCommission,
        totalYuan: totals.totalYuan,
        totalRuble: totals.finalTotal,
        updatedAt: new Date(),
      })
      .where(eq(orders.id, orderId));

    return {
      success: true,
      message: 'Order good added successfully',
      data: { good: newGood },
    };
  }, {
    params: t.Object({
      orderId: t.String(),
    }),
    body: t.Object({
      name: t.String({ minLength: 1 }),
      link: t.Optional(t.String()),
      quantity: t.Number({ minimum: 1 }),
      priceYuan: t.Number({ minimum: 0 }),
    }),
    detail: {
      summary: 'Add good to order (Admin)',
      tags: ['Orders'],
    },
  })

  // Update order good
  .put('/goods/:goodId', async ({ params: { goodId }, body }) => {
    const validation = orderGoodUpdateSchema.safeParse(body);
    if (!validation.success) {
      throw new ValidationError('Invalid order good update data');
    }

    const updateData = validation.data;

    // Find existing good
    const existingGood = await db.query.orderGoods.findFirst({
      where: eq(orderGoods.id, goodId),
      with: {
        order: true,
      },
    });

    if (!existingGood) {
      throw new NotFoundError('Order good not found');
    }

    // Calculate new totals if price or quantity changed
    let newTotals = {};
    if (updateData.priceYuan || updateData.quantity) {
      const newPrice = updateData.priceYuan || existingGood.priceYuan;
      const newQuantity = updateData.quantity || existingGood.quantity;
      const goodTotal = Number(newQuantity) * Number(newPrice);
      const commissionRate = 0.1;
      const goodCommission = goodTotal * commissionRate;
      const goodTotalYuan = goodTotal + goodCommission;
      const goodTotalRuble = goodTotalYuan * Number(existingGood.order!.currentKurs);

      newTotals = {
        commission: goodCommission,
        totalYuan: goodTotalYuan,
        totalRuble: goodTotalRuble,
      };
    }

    // Update good
    const [updatedGood] = await db.update(orderGoods)
      .set({
        ...updateData,
        ...newTotals,
        updatedAt: new Date(),
      })
      .where(eq(orderGoods.id, goodId))
      .returning();

    return {
      success: true,
      message: 'Order good updated successfully',
      data: { good: updatedGood },
    };
  }, {
    params: t.Object({
      goodId: t.String(),
    }),
    body: t.Object({
      name: t.Optional(t.String()),
      link: t.Optional(t.String()),
      quantity: t.Optional(t.Number()),
      priceYuan: t.Optional(t.Number()),
    }),
    detail: {
      summary: 'Update order good (Admin)',
      tags: ['Orders'],
    },
  })

  // Delete order good
  .delete('/goods/:goodId', async ({ params: { goodId } }) => {
    const good = await db.query.orderGoods.findFirst({
      where: eq(orderGoods.id, goodId),
    });

    if (!good) {
      throw new NotFoundError('Order good not found');
    }

    // Delete good
    await db.delete(orderGoods).where(eq(orderGoods.id, goodId));

    return {
      success: true,
      message: 'Order good deleted successfully',
    };
  }, {
    params: t.Object({
      goodId: t.String(),
    }),
    detail: {
      summary: 'Delete order good (Admin)',
      tags: ['Orders'],
    },
  })

  // Get order statistics
  .get('/stats/overview', async () => {
    // Get order counts by status
    const statusCounts = await db
      .select({
        status: orders.status,
        count: sql<number>`count(*)`,
      })
      .from(orders)
      .groupBy(orders.status);

    // Get total revenue
    const [{ totalRevenue }] = await db
      .select({
        totalRevenue: sql<number>`sum(${orders.totalRuble})`,
      })
      .from(orders)
      .where(eq(orders.status, OrderStatus.DELIVERED));

    // Get recent orders count
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const [{ recentOrdersCount }] = await db
      .select({
        recentOrdersCount: sql<number>`count(*)`,
      })
      .from(orders)
      .where(sql`${orders.createdAt} >= ${thirtyDaysAgo}`);

    return {
      success: true,
      data: {
        statusCounts,
        totalRevenue: totalRevenue || 0,
        recentOrdersCount: recentOrdersCount || 0,
      },
    };
  }, {
    detail: {
      summary: 'Get order statistics (Admin)',
      tags: ['Orders'],
    },
  });