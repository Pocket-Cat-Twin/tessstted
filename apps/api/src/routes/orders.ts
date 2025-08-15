import { Elysia, t } from "elysia";
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
  sql,
} from "@yuyu/db";
import {
  orderCreateSchema,
  orderUpdateSchema,
  orderGoodCreateSchema,
  orderGoodUpdateSchema,
  orderLookupSchema,
  OrderStatus,
  generateOrderNomerok,
  calculateOrderTotals,
  calculateCommission,
  calculateTotalCommission,
} from "@yuyu/shared";
import { requireAuth, requireAdmin } from "../middleware/auth";
import {
  orderSubscriptionMiddleware,
  orderCreationRateLimit,
  generateTierOrderNumber,
  subscriptionMiddleware,
} from "../middleware/subscription";
import {
  NotFoundError,
  ValidationError,
  ForbiddenError,
} from "../middleware/error";
import { sendOrderCreatedEmail } from "../services/email";
import { orderService } from "../services/order";

export const orderRoutes = new Elysia({ prefix: "/orders" })

  // Get processing information for user (with or without auth)
  .get(
    "/processing-info",
    async ({ query, store }) => {
      const userId = store?.user?.id;
      const processingInfo = await orderService.getOrderProcessingInfo(userId);

      return {
        success: true,
        data: { processingInfo },
      };
    },
    {
      query: t.Object({}),
      detail: {
        summary: "Get order processing information",
        description:
          "Get processing time, storage limits, and restrictions based on user subscription",
        tags: ["Orders"],
      },
    },
  )

  // Calculate order pricing with detailed commission breakdown
  .post(
    "/calculate",
    async ({ body }) => {
      // Get current exchange rate
      const kursConfig = await db.query.config.findFirst({
        where: eq(config.key, "current_kurs"),
      });
      const currentKurs = kursConfig ? parseFloat(kursConfig.value) : 13.5;

      const calculation = await orderService.calculateDetailedOrder(
        body.goods,
        currentKurs,
      );

      return {
        success: true,
        data: { calculation },
      };
    },
    {
      body: t.Object({
        goods: t.Array(
          t.Object({
            name: t.String(),
            quantity: t.Number({ minimum: 1 }),
            priceYuan: t.Number({ minimum: 0 }),
          }),
        ),
      }),
      detail: {
        summary: "Calculate order pricing",
        description:
          "Calculate detailed pricing including commission breakdown by tier",
        tags: ["Orders"],
      },
    },
  )

  // Validate order creation (checks subscription limits)
  .post(
    "/validate",
    async ({ body, store }) => {
      const userId = store?.user?.id;

      const validation = await orderService.validateOrderCreation(userId, {
        customerName: body.customerName,
        customerPhone: body.customerPhone,
        customerEmail: body.customerEmail,
        deliveryAddress: body.deliveryAddress,
        deliveryMethod: body.deliveryMethod,
        paymentMethod: body.paymentMethod,
        goods: body.goods,
      });

      return {
        success: true,
        data: { validation },
      };
    },
    {
      body: t.Object({
        customerName: t.String(),
        customerPhone: t.String(),
        customerEmail: t.Optional(t.String()),
        deliveryAddress: t.String(),
        deliveryMethod: t.String(),
        paymentMethod: t.String(),
        goods: t.Array(
          t.Object({
            name: t.String(),
            link: t.Optional(t.String()),
            quantity: t.Number({ minimum: 1 }),
            priceYuan: t.Number({ minimum: 0 }),
          }),
        ),
      }),
      detail: {
        summary: "Validate order creation",
        description:
          "Check if user can create order based on subscription limits",
        tags: ["Orders"],
      },
    },
  )

  // Get storage usage for authenticated user
  .use(requireAuth)
  .get(
    "/storage-usage",
    async ({ store }) => {
      const userId = store.user.id;
      const storageUsage = await orderService.getStorageUsage(userId);

      return {
        success: true,
        data: { storageUsage },
      };
    },
    {
      detail: {
        summary: "Get user storage usage",
        description:
          "Get current storage usage and limits based on subscription",
        tags: ["Orders"],
      },
    },
  )

  // Public order lookup by nomerok
  .get(
    "/lookup/:nomerok",
    async ({ params: { nomerok }, set }) => {
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
        throw new NotFoundError("Order not found");
      }

      // Remove sensitive information for public lookup
      const publicOrder = {
        id: order.id,
        nomerok: order.nomerok,
        customerName: order.customerName,
        status: order.status,
        totalRuble: order.totalRuble,
        createdAt: order.createdAt,
        goods: order.goods?.map((good) => ({
          name: good.name,
          quantity: good.quantity,
          priceYuan: good.priceYuan,
          totalRuble: good.totalRuble,
        })),
        statusHistory: order.statusHistory?.map((history) => ({
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
    },
    {
      params: t.Object({
        nomerok: t.String(),
      }),
      detail: {
        summary: "Lookup order by nomerok",
        tags: ["Orders"],
      },
    },
  )

  // Create new order (public) with subscription middleware
  .use(subscriptionMiddleware)
  .use(orderCreationRateLimit())
  .use(generateTierOrderNumber())
  .post(
    "/",
    async ({ body, set, store, orderNumber, rateLimit }) => {
      const validation = orderCreateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid order data");
      }

      const orderData = validation.data;
      const userId = store?.user?.id;

      // Validate order creation (check subscription limits)
      const validationResult = await orderService.validateOrderCreation(
        userId,
        orderData,
      );
      if (!validationResult.canCreate) {
        throw new ValidationError(validationResult.errors.join(", "));
      }

      // Get current exchange rate
      const kursConfig = await db.query.config.findFirst({
        where: eq(config.key, "current_kurs"),
      });
      const currentKurs = kursConfig ? parseFloat(kursConfig.value) : 13.5;

      // Calculate totals using new commission system
      const items = orderData.goods.map((good) => ({
        priceYuan: good.priceYuan,
        quantity: good.quantity,
      }));

      const commissionCalculation = calculateTotalCommission(
        items,
        currentKurs,
      );

      // Use tier-based order number from middleware
      const nomerok = orderNumber;

      // Create order with new commission calculation and processing deadlines
      const [newOrder] = await db
        .insert(orders)
        .values({
          nomerok,
          userId, // Link to user if authenticated
          customerName: orderData.customerName,
          customerPhone: orderData.customerPhone,
          customerEmail: orderData.customerEmail,
          deliveryAddress: orderData.deliveryAddress,
          deliveryMethod: orderData.deliveryMethod,
          paymentMethod: orderData.paymentMethod,
          subtotalYuan:
            commissionCalculation.totals.originalPriceYuan.toString(),
          totalCommission:
            commissionCalculation.totals.totalCommissionRuble.toString(),
          currentKurs: currentKurs.toString(),
          totalYuan: (
            commissionCalculation.totals.originalPriceYuan +
            commissionCalculation.totals.totalCommissionYuan
          ).toString(),
          totalRuble:
            commissionCalculation.totals.totalFinalPriceRuble.toString(),
          status: OrderStatus.CREATED,
        })
        .returning();

      // Create order goods with detailed commission calculation
      const orderGoodsData = orderData.goods.map((good, index) => {
        const itemCalculation = commissionCalculation.items[index];

        return {
          orderId: newOrder.id,
          name: good.name,
          link: good.link,
          quantity: good.quantity,
          priceYuan: good.priceYuan.toString(),
          commission: itemCalculation.commissionRuble.toString(),
          totalYuan: (
            good.priceYuan * good.quantity +
            itemCalculation.commissionYuan * good.quantity
          ).toString(),
          totalRuble: itemCalculation.totalFinalPrice.toString(),
        };
      });

      await db.insert(orderGoods).values(orderGoodsData);

      // Create status history entry
      await db.insert(orderStatusHistory).values({
        orderId: newOrder.id,
        toStatus: OrderStatus.CREATED,
        comment: "Заказ создан",
      });

      // Send notification email if email provided
      if (orderData.customerEmail) {
        try {
          await sendOrderCreatedEmail(
            orderData.customerEmail,
            orderData.customerName,
            nomerok,
            commissionCalculation.totals.totalFinalPriceRuble,
          );
        } catch (error) {
          console.error("Failed to send order notification email:", error);
          // Don't fail order creation if email fails
        }
      }

      set.status = 201;
      return {
        success: true,
        message: "Order created successfully",
        data: {
          order: newOrder,
          lookupUrl: `/orders/lookup/${nomerok}`,
          processingInfo: {
            subscriptionTier: validationResult.processingInfo.subscriptionTier,
            processingTimeHours:
              validationResult.processingInfo.processingTimeHours,
            storageTimeHours: validationResult.processingInfo.storageTimeHours,
            priorityProcessing:
              validationResult.processingInfo.priorityProcessing,
            processingDeadline: orderService.getProcessingDeadline(
              validationResult.processingInfo.subscriptionTier,
            ),
            storageExpiration: orderService.getStorageExpiration(
              validationResult.processingInfo.subscriptionTier,
            ),
          },
          warnings: validationResult.warnings,
          rateLimitInfo: rateLimit,
          commissionBreakdown: {
            totalItems: commissionCalculation.items.length,
            originalPrice: {
              yuan: commissionCalculation.totals.originalPriceYuan,
              ruble: commissionCalculation.totals.originalPriceRuble,
            },
            totalCommission: {
              yuan: commissionCalculation.totals.totalCommissionYuan,
              ruble: commissionCalculation.totals.totalCommissionRuble,
            },
            finalPrice: {
              yuan:
                commissionCalculation.totals.originalPriceYuan +
                commissionCalculation.totals.totalCommissionYuan,
              ruble: commissionCalculation.totals.totalFinalPriceRuble,
            },
            exchangeRate: currentKurs,
          },
        },
      };
    },
    {
      body: t.Object({
        customerName: t.String({ minLength: 1 }),
        customerPhone: t.String({ minLength: 1 }),
        customerEmail: t.Optional(t.String({ format: "email" })),
        deliveryAddress: t.String({ minLength: 1 }),
        deliveryMethod: t.String({ minLength: 1 }),
        paymentMethod: t.String({ minLength: 1 }),
        goods: t.Array(
          t.Object({
            name: t.String({ minLength: 1 }),
            link: t.Optional(t.String()),
            quantity: t.Number({ minimum: 1 }),
            priceYuan: t.Number({ minimum: 0 }),
          }),
          { minItems: 1 },
        ),
      }),
      detail: {
        summary: "Create new order",
        tags: ["Orders"],
      },
    },
  )

  // Admin routes
  .use(requireAdmin)

  // Get all orders with pagination and filtering
  .get(
    "/",
    async ({ query }) => {
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
          sql`(${orders.nomerok} ILIKE ${`%${search}%`} OR ${orders.customerName} ILIKE ${`%${search}%`})`,
        );
      }

      const whereClause =
        conditions.length > 0 ? and(...conditions) : undefined;

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
    },
    {
      query: t.Object({
        page: t.Optional(t.String()),
        limit: t.Optional(t.String()),
        status: t.Optional(t.String()),
        search: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get all orders (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Get order by ID with detailed commission breakdown
  .get(
    "/:id",
    async ({ params: { id } }) => {
      const order = await db.query.orders.findFirst({
        where: eq(orders.id, id),
        with: {
          goods: true,
          user: {
            columns: {
              name: true,
              email: true,
              phone: true,
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
        throw new NotFoundError("Order not found");
      }

      // Calculate commission breakdown for each item
      const commissionBreakdown =
        order.goods?.map((good) => {
          const itemCommission = calculateCommission({
            priceYuan: Number(good.priceYuan),
            exchangeRate: Number(order.currentKurs),
          });

          return {
            id: good.id,
            name: good.name,
            quantity: good.quantity,
            priceYuan: Number(good.priceYuan),
            commissionDetails: {
              type: itemCommission.calculationType,
              rate: itemCommission.commissionRate,
              commissionYuan: itemCommission.commissionYuan,
              commissionRuble: itemCommission.commissionRuble,
              originalPriceRuble: itemCommission.originalPriceRuble,
              finalPriceRuble: itemCommission.finalPriceRuble,
            },
            totals: {
              originalYuan: Number(good.priceYuan) * good.quantity,
              totalCommissionYuan:
                itemCommission.commissionYuan * good.quantity,
              totalCommissionRuble:
                itemCommission.commissionRuble * good.quantity,
              finalYuan:
                (Number(good.priceYuan) + itemCommission.commissionYuan) *
                good.quantity,
              finalRuble: itemCommission.finalPriceRuble * good.quantity,
            },
          };
        }) || [];

      // Get user's subscription info if available
      let userSubscriptionInfo = null;
      if (order.user) {
        const processingInfo = await orderService.getOrderProcessingInfo(
          order.userId!,
        );
        userSubscriptionInfo = {
          currentTier: processingInfo.subscriptionTier,
          processingTimeHours: processingInfo.processingTimeHours,
          storageTimeHours: processingInfo.storageTimeHours,
          priorityProcessing: processingInfo.priorityProcessing,
        };
      }

      return {
        success: true,
        data: {
          order,
          commissionBreakdown,
          userSubscriptionInfo,
          totals: {
            originalYuan: Number(order.subtotalYuan),
            totalCommissionYuan: commissionBreakdown.reduce(
              (sum, item) => sum + item.totals.totalCommissionYuan,
              0,
            ),
            totalCommissionRuble: Number(order.totalCommission),
            finalYuan: Number(order.totalYuan),
            finalRuble: Number(order.totalRuble),
            exchangeRate: Number(order.currentKurs),
          },
        },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Get order by ID with commission breakdown (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Update order
  .put(
    "/:id",
    async ({ params: { id }, body, user }) => {
      const validation = orderUpdateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid order update data");
      }

      const updateData = validation.data;

      // Find existing order
      const existingOrder = await db.query.orders.findFirst({
        where: eq(orders.id, id),
      });

      if (!existingOrder) {
        throw new NotFoundError("Order not found");
      }

      // Track status change
      const statusChanged =
        updateData.status && updateData.status !== existingOrder.status;

      // Update order
      const [updatedOrder] = await db
        .update(orders)
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
          comment: updateData.notes || "Статус изменен администратором",
        });
      }

      return {
        success: true,
        message: "Order updated successfully",
        data: { order: updatedOrder },
      };
    },
    {
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
        summary: "Update order (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Delete order
  .delete(
    "/:id",
    async ({ params: { id } }) => {
      const order = await db.query.orders.findFirst({
        where: eq(orders.id, id),
      });

      if (!order) {
        throw new NotFoundError("Order not found");
      }

      // Delete order (cascades to goods and status history)
      await db.delete(orders).where(eq(orders.id, id));

      return {
        success: true,
        message: "Order deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete order (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Order goods management
  .post(
    "/:orderId/goods",
    async ({ params: { orderId }, body }) => {
      const validation = orderGoodCreateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid order good data");
      }

      const goodData = validation.data;

      // Check if order exists
      const order = await db.query.orders.findFirst({
        where: eq(orders.id, orderId),
      });

      if (!order) {
        throw new NotFoundError("Order not found");
      }

      // Calculate good totals using new commission system
      const itemCommission = calculateCommission({
        priceYuan: goodData.priceYuan,
        exchangeRate: Number(order.currentKurs),
        quantity: goodData.quantity,
      });

      const totalQuantityPrice = goodData.priceYuan * goodData.quantity;
      const totalQuantityCommission =
        itemCommission.commissionYuan * goodData.quantity;
      const goodTotalYuan = totalQuantityPrice + totalQuantityCommission;
      const goodTotalRuble = itemCommission.finalPriceRuble * goodData.quantity;

      // Create order good
      const [newGood] = await db
        .insert(orderGoods)
        .values({
          orderId,
          name: goodData.name,
          link: goodData.link,
          quantity: goodData.quantity,
          priceYuan: goodData.priceYuan.toString(),
          commission: (
            itemCommission.commissionRuble * goodData.quantity
          ).toString(),
          totalYuan: goodTotalYuan.toString(),
          totalRuble: goodTotalRuble.toString(),
        })
        .returning();

      // Recalculate order totals
      const allGoods = await db.query.orderGoods.findMany({
        where: eq(orderGoods.orderId, orderId),
      });

      const allItems = allGoods.map((g) => ({
        quantity: g.quantity,
        priceYuan: Number(g.priceYuan),
      }));

      const newTotalCalculation = calculateTotalCommission(
        allItems,
        Number(order.currentKurs),
      );

      // Update order totals
      await db
        .update(orders)
        .set({
          subtotalYuan: newTotalCalculation.totals.originalPriceYuan.toString(),
          totalCommission:
            newTotalCalculation.totals.totalCommissionRuble.toString(),
          totalYuan: (
            newTotalCalculation.totals.originalPriceYuan +
            newTotalCalculation.totals.totalCommissionYuan
          ).toString(),
          totalRuble:
            newTotalCalculation.totals.totalFinalPriceRuble.toString(),
          updatedAt: new Date(),
        })
        .where(eq(orders.id, orderId));

      return {
        success: true,
        message: "Order good added successfully",
        data: { good: newGood },
      };
    },
    {
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
        summary: "Add good to order (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Update order good
  .put(
    "/goods/:goodId",
    async ({ params: { goodId }, body }) => {
      const validation = orderGoodUpdateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid order good update data");
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
        throw new NotFoundError("Order good not found");
      }

      // Calculate new totals if price or quantity changed
      let newTotals = {};
      if (updateData.priceYuan || updateData.quantity) {
        const newPrice = updateData.priceYuan || Number(existingGood.priceYuan);
        const newQuantity = updateData.quantity || existingGood.quantity;

        // Use new commission system
        const itemCommission = calculateCommission({
          priceYuan: newPrice,
          exchangeRate: Number(existingGood.order!.currentKurs),
          quantity: newQuantity,
        });

        const totalQuantityCommission =
          itemCommission.commissionYuan * newQuantity;
        const goodTotalYuan = newPrice * newQuantity + totalQuantityCommission;
        const goodTotalRuble = itemCommission.finalPriceRuble * newQuantity;

        newTotals = {
          commission: (itemCommission.commissionRuble * newQuantity).toString(),
          totalYuan: goodTotalYuan.toString(),
          totalRuble: goodTotalRuble.toString(),
        };
      }

      // Update good
      const [updatedGood] = await db
        .update(orderGoods)
        .set({
          ...updateData,
          ...newTotals,
          updatedAt: new Date(),
        })
        .where(eq(orderGoods.id, goodId))
        .returning();

      return {
        success: true,
        message: "Order good updated successfully",
        data: { good: updatedGood },
      };
    },
    {
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
        summary: "Update order good (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Delete order good
  .delete(
    "/goods/:goodId",
    async ({ params: { goodId } }) => {
      const good = await db.query.orderGoods.findFirst({
        where: eq(orderGoods.id, goodId),
      });

      if (!good) {
        throw new NotFoundError("Order good not found");
      }

      // Delete good
      await db.delete(orderGoods).where(eq(orderGoods.id, goodId));

      return {
        success: true,
        message: "Order good deleted successfully",
      };
    },
    {
      params: t.Object({
        goodId: t.String(),
      }),
      detail: {
        summary: "Delete order good (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Get order statistics
  .get(
    "/stats/overview",
    async () => {
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
    },
    {
      detail: {
        summary: "Get order statistics (Admin)",
        tags: ["Orders"],
      },
    },
  )

  // Bulk Operations

  // Bulk status update
  .post(
    "/bulk/status",
    async ({ body, user }) => {
      const { orderIds, status, comment } = body;

      // Validate status
      if (!Object.values(OrderStatus).includes(status as OrderStatus)) {
        throw new ValidationError("Invalid order status");
      }

      // Validate order IDs
      if (!orderIds || orderIds.length === 0) {
        throw new ValidationError("No order IDs provided");
      }

      // Find existing orders
      const existingOrders = await db.query.orders.findMany({
        where: sql`${orders.id} = ANY(${orderIds})`,
        columns: {
          id: true,
          status: true,
        },
      });

      if (existingOrders.length === 0) {
        throw new NotFoundError("No valid orders found");
      }

      // Update orders
      await db
        .update(orders)
        .set({
          status: status as OrderStatus,
          updatedAt: new Date(),
        })
        .where(sql`${orders.id} = ANY(${orderIds})`);

      // Add status history for each order
      const statusHistoryEntries = existingOrders.map((order) => ({
        orderId: order.id,
        userId: user.id,
        fromStatus: order.status,
        toStatus: status as OrderStatus,
        comment: comment || `Bulk status update to ${status}`,
      }));

      if (statusHistoryEntries.length > 0) {
        await db.insert(orderStatusHistory).values(statusHistoryEntries);
      }

      return {
        success: true,
        message: `Updated ${existingOrders.length} orders to status: ${status}`,
        data: {
          updatedCount: existingOrders.length,
          updatedOrders: existingOrders.map((o) => o.id),
        },
      };
    },
    {
      body: t.Object({
        orderIds: t.Array(t.String(), { minItems: 1, maxItems: 100 }),
        status: t.String(),
        comment: t.Optional(t.String()),
      }),
      detail: {
        summary: "Bulk update order status (Admin)",
        description: "Update status for multiple orders at once",
        tags: ["Orders"],
      },
    },
  )

  // Bulk export orders to CSV
  .post(
    "/bulk/export",
    async ({ body }) => {
      const { orderIds, format } = body;

      // Find orders to export
      const whereClause =
        orderIds && orderIds.length > 0
          ? sql`${orders.id} = ANY(${orderIds})`
          : undefined;

      const ordersToExport = await db.query.orders.findMany({
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
        limit: 1000, // Limit to prevent huge exports
      });

      if (ordersToExport.length === 0) {
        throw new NotFoundError("No orders found for export");
      }

      // Convert to CSV format
      const csvHeaders = [
        "Номерок",
        "Статус",
        "Имя клиента",
        "Телефон",
        "Email",
        "Адрес доставки",
        "Сумма (юани)",
        "Сумма (рубли)",
        "Комиссия",
        "Дата создания",
        "Пользователь",
        "Товары",
      ];

      const csvRows = ordersToExport.map((order) => [
        order.nomerok,
        order.status,
        order.customerName,
        order.customerPhone || "",
        order.customerEmail || "",
        order.deliveryAddress || "",
        order.totalYuan,
        order.totalRuble,
        order.totalCommission,
        order.createdAt.toISOString().split("T")[0],
        order.user?.name || "Гость",
        order.goods?.map((g) => `${g.name} (${g.quantity} шт.)`).join("; ") ||
          "",
      ]);

      const csvContent = [csvHeaders, ...csvRows]
        .map((row) => row.map((cell) => `"${cell}"`).join(","))
        .join("\n");

      return {
        success: true,
        message: `Exported ${ordersToExport.length} orders`,
        data: {
          format: "csv",
          content: csvContent,
          filename: `orders_export_${new Date().toISOString().split("T")[0]}.csv`,
          count: ordersToExport.length,
        },
      };
    },
    {
      body: t.Object({
        orderIds: t.Optional(t.Array(t.String())),
        format: t.Optional(t.String()),
      }),
      detail: {
        summary: "Bulk export orders (Admin)",
        description: "Export orders to CSV format",
        tags: ["Orders"],
      },
    },
  )

  // Bulk assign orders to user
  .post(
    "/bulk/assign",
    async ({ body }) => {
      const { orderIds, userId } = body;

      // Validate user exists if provided
      if (userId) {
        const user = await db.query.users.findFirst({
          where: eq(users.id, userId),
        });

        if (!user) {
          throw new NotFoundError("User not found");
        }
      }

      // Update orders
      const result = await db
        .update(orders)
        .set({
          userId: userId || null,
          updatedAt: new Date(),
        })
        .where(sql`${orders.id} = ANY(${orderIds})`)
        .returning({ id: orders.id });

      return {
        success: true,
        message: `Assigned ${result.length} orders to ${userId ? "user" : "guest"}`,
        data: {
          updatedCount: result.length,
          assignedTo: userId || "guest",
        },
      };
    },
    {
      body: t.Object({
        orderIds: t.Array(t.String(), { minItems: 1, maxItems: 100 }),
        userId: t.Optional(t.String()),
      }),
      detail: {
        summary: "Bulk assign orders to user (Admin)",
        description: "Assign multiple orders to a user or set as guest orders",
        tags: ["Orders"],
      },
    },
  )

  // Bulk delete orders
  .post(
    "/bulk/delete",
    async ({ body }) => {
      const { orderIds, confirm } = body;

      if (!confirm) {
        throw new ValidationError("Confirmation required for bulk deletion");
      }

      // Find orders to delete
      const ordersToDelete = await db.query.orders.findMany({
        where: sql`${orders.id} = ANY(${orderIds})`,
        columns: {
          id: true,
          nomerok: true,
          status: true,
        },
      });

      if (ordersToDelete.length === 0) {
        throw new NotFoundError("No valid orders found for deletion");
      }

      // Delete orders (cascades to goods and status history)
      await db.delete(orders).where(sql`${orders.id} = ANY(${orderIds})`);

      return {
        success: true,
        message: `Deleted ${ordersToDelete.length} orders`,
        data: {
          deletedCount: ordersToDelete.length,
          deletedOrders: ordersToDelete.map((o) => ({
            id: o.id,
            nomerok: o.nomerok,
            status: o.status,
          })),
        },
      };
    },
    {
      body: t.Object({
        orderIds: t.Array(t.String(), { minItems: 1, maxItems: 100 }),
        confirm: t.Boolean(),
      }),
      detail: {
        summary: "Bulk delete orders (Admin)",
        description: "Delete multiple orders at once (requires confirmation)",
        tags: ["Orders"],
      },
    },
  )

  // Bulk order summary
  .post(
    "/bulk/summary",
    async ({ body }) => {
      const { orderIds } = body;

      const ordersData = await db.query.orders.findMany({
        where: sql`${orders.id} = ANY(${orderIds})`,
        with: {
          goods: true,
        },
      });

      if (ordersData.length === 0) {
        throw new NotFoundError("No orders found");
      }

      // Calculate summary statistics
      const summary = {
        totalOrders: ordersData.length,
        totalValue: {
          yuan: ordersData.reduce(
            (sum, order) => sum + Number(order.totalYuan),
            0,
          ),
          ruble: ordersData.reduce(
            (sum, order) => sum + Number(order.totalRuble),
            0,
          ),
          commission: ordersData.reduce(
            (sum, order) => sum + Number(order.totalCommission),
            0,
          ),
        },
        statusBreakdown: ordersData.reduce(
          (acc, order) => {
            acc[order.status] = (acc[order.status] || 0) + 1;
            return acc;
          },
          {} as Record<string, number>,
        ),
        totalItems: ordersData.reduce(
          (sum, order) =>
            sum +
            (order.goods?.reduce(
              (goodSum, good) => goodSum + good.quantity,
              0,
            ) || 0),
          0,
        ),
        dateRange: {
          earliest: new Date(
            Math.min(...ordersData.map((o) => o.createdAt.getTime())),
          ),
          latest: new Date(
            Math.max(...ordersData.map((o) => o.createdAt.getTime())),
          ),
        },
      };

      return {
        success: true,
        data: { summary },
      };
    },
    {
      body: t.Object({
        orderIds: t.Array(t.String(), { minItems: 1 }),
      }),
      detail: {
        summary: "Get bulk order summary (Admin)",
        description: "Get summary statistics for multiple orders",
        tags: ["Orders"],
      },
    },
  );
