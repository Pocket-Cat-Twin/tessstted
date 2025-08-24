import { Elysia, t } from "elysia";
import {
  db,
  faqs,
  eq,
  and,
  asc,
  sql,
  like,
  or,
} from "@lolita-fashion/db";
import { requireAdmin } from "../middleware/auth";
import {
  NotFoundError,
} from "../middleware/error";

export const faqRoutes = new Elysia({ prefix: "/faq" })

  // === PUBLIC ROUTES ===

  // Get active FAQs
  .get(
    "/",
    async ({ query }) => {
      const limit = parseInt(query.limit || "20");
      const search = query.search;

      const whereConditions = [eq(faqs.isActive, true)];

      // Search in questions and answers
      if (search) {
        whereConditions.push(
          or(
            like(faqs.question, `%${search}%`),
            like(faqs.answer, `%${search}%`),
          ),
        );
      }

      const faqsData = await db.query.faqs.findMany({
        where: and(...whereConditions),
        orderBy: [asc(faqs.order), asc(faqs.question)],
        limit,
        columns: {
          id: true,
          question: true,
          answer: true,
          order: true,
        },
      });

      return {
        success: true,
        data: {
          faqs: faqsData,
          totalCount: faqsData.length,
        },
      };
    },
    {
      query: t.Object({
        limit: t.Optional(t.String()),
        search: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get active FAQs",
        tags: ["FAQ"],
      },
    },
  )

  // Get FAQ by ID (public)
  .get(
    "/:id",
    async ({ params: { id } }) => {
      const faq = await db.query.faqs.findFirst({
        where: and(eq(faqs.id, id), eq(faqs.isActive, true)),
      });

      if (!faq) {
        throw new NotFoundError("FAQ not found");
      }

      return {
        success: true,
        data: { faq },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Get FAQ by ID",
        tags: ["FAQ"],
      },
    },
  )

  // === ADMIN ROUTES ===
  .use(requireAdmin)

  // Get all FAQs (admin)
  .get(
    "/admin/all",
    async ({ query }) => {
      const page = parseInt(query.page || "1");
      const limit = parseInt(query.limit || "20");
      const offset = (page - 1) * limit;
      const search = query.search;

      const whereConditions = [];

      if (search) {
        whereConditions.push(
          or(
            like(faqs.question, `%${search}%`),
            like(faqs.answer, `%${search}%`),
          ),
        );
      }

      const whereClause =
        whereConditions.length > 0 ? and(...whereConditions) : undefined;

      const faqsData = await db.query.faqs.findMany({
        where: whereClause,
        orderBy: [asc(faqs.order), asc(faqs.question)],
        limit,
        offset,
      });

      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(faqs)
        .where(whereClause);

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: faqsData,
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
        search: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get all FAQs (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Get FAQ by ID (admin)
  .get(
    "/admin/:id",
    async ({ params: { id } }) => {
      const faq = await db.query.faqs.findFirst({
        where: eq(faqs.id, id),
      });

      if (!faq) {
        throw new NotFoundError("FAQ not found");
      }

      return {
        success: true,
        data: { faq },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Get FAQ by ID (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Create FAQ
  .post(
    "/admin",
    async ({ body, set }) => {
      const { question, answer, order, isActive } = body;

      const [newFaq] = await db
        .insert(faqs)
        .values({
          question,
          answer,
          order: order || 0,
          isActive: isActive ?? true,
        })
        .returning();

      set.status = 201;
      return {
        success: true,
        message: "FAQ created successfully",
        data: { faq: newFaq },
      };
    },
    {
      body: t.Object({
        question: t.String({ minLength: 1, maxLength: 500 }),
        answer: t.String({ minLength: 1 }),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Create FAQ (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Update FAQ
  .put(
    "/admin/:id",
    async ({ params: { id }, body }) => {
      const existingFaq = await db.query.faqs.findFirst({
        where: eq(faqs.id, id),
      });

      if (!existingFaq) {
        throw new NotFoundError("FAQ not found");
      }

      const [updatedFaq] = await db
        .update(faqs)
        .set({
          ...body,
          updatedAt: new Date(),
        })
        .where(eq(faqs.id, id))
        .returning();

      return {
        success: true,
        message: "FAQ updated successfully",
        data: { faq: updatedFaq },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        question: t.Optional(t.String({ minLength: 1, maxLength: 500 })),
        answer: t.Optional(t.String({ minLength: 1 })),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Update FAQ (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Delete FAQ
  .delete(
    "/admin/:id",
    async ({ params: { id } }) => {
      const faq = await db.query.faqs.findFirst({
        where: eq(faqs.id, id),
      });

      if (!faq) {
        throw new NotFoundError("FAQ not found");
      }

      // Delete FAQ
      await db.delete(faqs).where(eq(faqs.id, id));

      return {
        success: true,
        message: "FAQ deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete FAQ (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Reorder FAQs
  .post(
    "/admin/reorder",
    async ({ body }) => {
      const { faqIds } = body;

      // Update order for each FAQ
      const updatePromises = faqIds.map((faqId: string, index: number) =>
        db
          .update(faqs)
          .set({ order: index, updatedAt: new Date() })
          .where(eq(faqs.id, faqId)),
      );

      await Promise.all(updatePromises);

      return {
        success: true,
        message: "FAQ order updated successfully",
      };
    },
    {
      body: t.Object({
        faqIds: t.Array(t.String()),
      }),
      detail: {
        summary: "Reorder FAQs (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Get FAQ statistics
  .get(
    "/admin/stats",
    async () => {
      // Get total FAQ count
      const [{ totalFaqs }] = await db
        .select({ totalFaqs: sql<number>`count(*)` })
        .from(faqs);

      // Get active FAQ count
      const [{ activeFaqs }] = await db
        .select({ activeFaqs: sql<number>`count(*)` })
        .from(faqs)
        .where(eq(faqs.isActive, true));

      return {
        success: true,
        data: {
          totalFaqs: totalFaqs || 0,
          activeFaqs: activeFaqs || 0,
        },
      };
    },
    {
      detail: {
        summary: "Get FAQ statistics (Admin)",
        tags: ["FAQ"],
      },
    },
  );