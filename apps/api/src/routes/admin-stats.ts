import { Elysia, t } from "elysia";
import {
  db,
  users,
  orders,
  userSubscriptions,
  stories,
  faqs,
  eq,
  and,
  desc,
  asc,
  sql,
  gte,
  lte,
} from "@yuyu/db";
import { requireAdmin } from "../middleware/auth";

export const adminStatsRoutes = new Elysia({ prefix: "/admin/stats" })
  .use(requireAdmin)

  // Get comprehensive dashboard statistics
  .get(
    "/dashboard",
    async ({ query }) => {
      const period = query.period || "30"; // days
      const daysAgo = parseInt(period);
      const startDate = new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000);

      // User Statistics
      const [{ totalUsers }] = await db
        .select({ totalUsers: sql<number>`count(*)` })
        .from(users);

      const [{ newUsers }] = await db
        .select({ newUsers: sql<number>`count(*)` })
        .from(users)
        .where(gte(users.createdAt, startDate));

      const [{ activeUsers }] = await db
        .select({ activeUsers: sql<number>`count(*)` })
        .from(users)
        .where(eq(users.status, "active"));

      const [{ verifiedUsers }] = await db
        .select({ verifiedUsers: sql<number>`count(*)` })
        .from(users)
        .where(eq(users.emailVerified, true));

      // Order Statistics
      const [{ totalOrders }] = await db
        .select({ totalOrders: sql<number>`count(*)` })
        .from(orders);

      const [{ newOrders }] = await db
        .select({ newOrders: sql<number>`count(*)` })
        .from(orders)
        .where(gte(orders.createdAt, startDate));

      const [{ completedOrders }] = await db
        .select({ completedOrders: sql<number>`count(*)` })
        .from(orders)
        .where(eq(orders.status, "completed"));

      const [{ totalRevenue }] = await db
        .select({
          totalRevenue: sql<number>`COALESCE(SUM(${orders.totalRuble}), 0)`,
        })
        .from(orders)
        .where(eq(orders.status, "completed"));

      // Recent revenue (last period)
      const [{ recentRevenue }] = await db
        .select({
          recentRevenue: sql<number>`COALESCE(SUM(${orders.totalRuble}), 0)`,
        })
        .from(orders)
        .where(
          and(eq(orders.status, "completed"), gte(orders.createdAt, startDate)),
        );

      // Subscription Statistics
      const [{ totalSubscriptions }] = await db
        .select({ totalSubscriptions: sql<number>`count(*)` })
        .from(userSubscriptions);

      const [{ activeSubscriptions }] = await db
        .select({ activeSubscriptions: sql<number>`count(*)` })
        .from(userSubscriptions)
        .where(sql`${userSubscriptions.endDate} > NOW()`);

      const [{ newSubscriptions }] = await db
        .select({ newSubscriptions: sql<number>`count(*)` })
        .from(userSubscriptions)
        .where(gte(userSubscriptions.createdAt, startDate));

      // Content Statistics
      const [{ totalStories }] = await db
        .select({ totalStories: sql<number>`count(*)` })
        .from(stories);

      const [{ publishedStories }] = await db
        .select({ publishedStories: sql<number>`count(*)` })
        .from(stories)
        .where(eq(stories.status, "published"));

      const [{ totalFAQs }] = await db
        .select({ totalFAQs: sql<number>`count(*)` })
        .from(faqs);

      const [{ activeFAQs }] = await db
        .select({ activeFAQs: sql<number>`count(*)` })
        .from(faqs)
        .where(eq(faqs.isActive, true));

      // Order status distribution
      const orderStatusCounts = await db
        .select({
          status: orders.status,
          count: sql<number>`count(*)`,
        })
        .from(orders)
        .groupBy(orders.status);

      // User role distribution
      const userRoleCounts = await db
        .select({
          role: users.role,
          count: sql<number>`count(*)`,
        })
        .from(users)
        .groupBy(users.role);

      // Subscription tier distribution
      const subscriptionTierCounts = await db
        .select({
          tier: userSubscriptions.tier,
          count: sql<number>`count(*)`,
        })
        .from(userSubscriptions)
        .where(sql`${userSubscriptions.endDate} > NOW()`)
        .groupBy(userSubscriptions.tier);

      return {
        success: true,
        data: {
          overview: {
            users: {
              total: totalUsers || 0,
              new: newUsers || 0,
              active: activeUsers || 0,
              verified: verifiedUsers || 0,
              verificationRate: totalUsers
                ? Math.round((verifiedUsers / totalUsers) * 100)
                : 0,
            },
            orders: {
              total: totalOrders || 0,
              new: newOrders || 0,
              completed: completedOrders || 0,
              completionRate: totalOrders
                ? Math.round((completedOrders / totalOrders) * 100)
                : 0,
            },
            revenue: {
              total: totalRevenue || 0,
              recent: recentRevenue || 0,
              average: totalOrders
                ? Math.round(totalRevenue / totalOrders || 0)
                : 0,
            },
            subscriptions: {
              total: totalSubscriptions || 0,
              active: activeSubscriptions || 0,
              new: newSubscriptions || 0,
              activeRate: totalSubscriptions
                ? Math.round((activeSubscriptions / totalSubscriptions) * 100)
                : 0,
            },
            content: {
              stories: {
                total: totalStories || 0,
                published: publishedStories || 0,
                publishRate: totalStories
                  ? Math.round((publishedStories / totalStories) * 100)
                  : 0,
              },
              faqs: {
                total: totalFAQs || 0,
                active: activeFAQs || 0,
              },
            },
          },
          distributions: {
            orderStatus: orderStatusCounts,
            userRoles: userRoleCounts,
            subscriptionTiers: subscriptionTierCounts,
          },
          period: {
            days: daysAgo,
            startDate: startDate.toISOString(),
            endDate: new Date().toISOString(),
          },
        },
      };
    },
    {
      query: t.Object({
        period: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get comprehensive dashboard statistics",
        description: "Get overview statistics for admin dashboard",
        tags: ["Admin", "Statistics"],
      },
    },
  )

  // Get detailed order statistics with time series
  .get(
    "/orders",
    async ({ query }) => {
      const period = parseInt(query.period) || 30;
      const groupBy = query.groupBy || "day"; // day, week, month
      const startDate = new Date(Date.now() - period * 24 * 60 * 60 * 1000);

      // Time series data based on groupBy
      let dateFormat: string;
      let dateInterval: string;

      switch (groupBy) {
        case "week":
          dateFormat = 'YYYY-"W"WW';
          dateInterval = "1 week";
          break;
        case "month":
          dateFormat = "YYYY-MM";
          dateInterval = "1 month";
          break;
        default: // day
          dateFormat = "YYYY-MM-DD";
          dateInterval = "1 day";
          break;
      }

      // Order counts over time
      const orderTimeSeries = await db.execute(sql`
      SELECT 
        TO_CHAR(${orders.createdAt}, ${dateFormat}) as period,
        COUNT(*)::int as order_count,
        COUNT(CASE WHEN ${orders.status} = 'completed' THEN 1 END)::int as completed_count,
        COALESCE(SUM(CASE WHEN ${orders.status} = 'completed' THEN ${orders.totalRuble} ELSE 0 END), 0)::int as revenue
      FROM ${orders}
      WHERE ${orders.createdAt} >= ${startDate}
      GROUP BY TO_CHAR(${orders.createdAt}, ${dateFormat})
      ORDER BY period ASC
    `);

      // Top selling items (mock data - you'd need actual product tracking)
      const topItems = await db
        .select({
          status: orders.status,
          count: sql<number>`count(*)`,
          revenue: sql<number>`COALESCE(SUM(${orders.totalRuble}), 0)`,
        })
        .from(orders)
        .where(gte(orders.createdAt, startDate))
        .groupBy(orders.status)
        .orderBy(desc(sql`count(*)`))
        .limit(10);

      return {
        success: true,
        data: {
          timeSeries: orderTimeSeries.rows,
          topItems,
          period: {
            days: period,
            groupBy,
            startDate: startDate.toISOString(),
            endDate: new Date().toISOString(),
          },
        },
      };
    },
    {
      query: t.Object({
        period: t.Optional(t.String()),
        groupBy: t.Optional(
          t.Union([t.Literal("day"), t.Literal("week"), t.Literal("month")]),
        ),
      }),
      detail: {
        summary: "Get detailed order statistics",
        description: "Get order statistics with time series data",
        tags: ["Admin", "Statistics"],
      },
    },
  )

  // Get user growth and engagement statistics
  .get(
    "/users",
    async ({ query }) => {
      const period = parseInt(query.period) || 30;
      const startDate = new Date(Date.now() - period * 24 * 60 * 60 * 1000);

      // User registration over time
      const registrationTimeSeries = await db.execute(sql`
      SELECT 
        TO_CHAR(${users.createdAt}, 'YYYY-MM-DD') as date,
        COUNT(*)::int as registrations,
        COUNT(CASE WHEN ${users.emailVerified} = true THEN 1 END)::int as verified_registrations
      FROM ${users}
      WHERE ${users.createdAt} >= ${startDate}
      GROUP BY TO_CHAR(${users.createdAt}, 'YYYY-MM-DD')
      ORDER BY date ASC
    `);

      // User engagement metrics (based on order activity)
      const engagementStats = await db.execute(sql`
      SELECT 
        COUNT(DISTINCT ${orders.userId})::int as active_users,
        COUNT(DISTINCT CASE WHEN ${orders.createdAt} >= ${startDate} THEN ${orders.userId} END)::int as recent_active_users,
        AVG(order_count.count)::numeric as avg_orders_per_user
      FROM (
        SELECT ${orders.userId}, COUNT(*) as count
        FROM ${orders}
        WHERE ${orders.userId} IS NOT NULL
        GROUP BY ${orders.userId}
      ) as order_count
      FULL OUTER JOIN ${orders} ON ${orders.userId} = order_count.userId
    `);

      return {
        success: true,
        data: {
          registrationTimeSeries: registrationTimeSeries.rows,
          engagement: engagementStats.rows[0],
          period: {
            days: period,
            startDate: startDate.toISOString(),
            endDate: new Date().toISOString(),
          },
        },
      };
    },
    {
      query: t.Object({
        period: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get user growth and engagement statistics",
        description: "Get user registration trends and engagement metrics",
        tags: ["Admin", "Statistics"],
      },
    },
  )

  // Get financial summary
  .get(
    "/financial",
    async ({ query }) => {
      const period = parseInt(query.period) || 30;
      const startDate = new Date(Date.now() - period * 24 * 60 * 60 * 1000);

      // Revenue trends
      const revenueTimeSeries = await db.execute(sql`
      SELECT 
        TO_CHAR(${orders.createdAt}, 'YYYY-MM-DD') as date,
        COALESCE(SUM(CASE WHEN ${orders.status} = 'completed' THEN ${orders.totalRuble} ELSE 0 END), 0)::int as revenue,
        COUNT(CASE WHEN ${orders.status} = 'completed' THEN 1 END)::int as completed_orders
      FROM ${orders}
      WHERE ${orders.createdAt} >= ${startDate}
      GROUP BY TO_CHAR(${orders.createdAt}, 'YYYY-MM-DD')
      ORDER BY date ASC
    `);

      // Revenue by status
      const revenueByStatus = await db
        .select({
          status: orders.status,
          totalRevenue: sql<number>`COALESCE(SUM(${orders.totalRuble}), 0)`,
          orderCount: sql<number>`count(*)`,
          averageValue: sql<number>`COALESCE(AVG(${orders.totalRuble}), 0)`,
        })
        .from(orders)
        .where(gte(orders.createdAt, startDate))
        .groupBy(orders.status);

      return {
        success: true,
        data: {
          timeSeries: revenueTimeSeries.rows,
          byStatus: revenueByStatus,
          period: {
            days: period,
            startDate: startDate.toISOString(),
            endDate: new Date().toISOString(),
          },
        },
      };
    },
    {
      query: t.Object({
        period: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get financial statistics",
        description: "Get revenue trends and financial metrics",
        tags: ["Admin", "Statistics"],
      },
    },
  );
