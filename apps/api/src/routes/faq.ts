import { Elysia, t } from "elysia";
import {
  db,
  faqs,
  faqCategories,
  eq,
  and,
  desc,
  asc,
  sql,
  like,
  or,
} from "@yuyu/db";
import { requireAuth, requireAdmin } from "../middleware/auth";
import {
  NotFoundError,
  ValidationError,
  DuplicateError,
} from "../middleware/error";

// Helper function to create slug from name
function createSlug(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export const faqRoutes = new Elysia({ prefix: "/faq" })

  // === PUBLIC ROUTES ===

  // Get all active FAQ categories
  .get(
    "/categories",
    async ({ query }) => {
      const limit = parseInt(query.limit) || 50;

      const categoriesData = await db.query.faqCategories.findMany({
        where: eq(faqCategories.isActive, true),
        orderBy: [asc(faqCategories.order), asc(faqCategories.name)],
        limit,
        columns: {
          id: true,
          name: true,
          slug: true,
          description: true,
        },
      });

      return {
        success: true,
        data: categoriesData,
      };
    },
    {
      query: t.Object({
        limit: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get active FAQ categories",
        tags: ["FAQ"],
      },
    },
  )

  // Get active FAQs
  .get(
    "/",
    async ({ query }) => {
      const limit = parseInt(query.limit) || 20;
      const categorySlug = query.category;
      const search = query.search;

      let whereConditions = [eq(faqs.isActive, true)];

      // Filter by category if specified
      if (categorySlug) {
        const category = await db.query.faqCategories.findFirst({
          where: and(
            eq(faqCategories.slug, categorySlug),
            eq(faqCategories.isActive, true),
          ),
        });

        if (category) {
          whereConditions.push(eq(faqs.categoryId, category.id));
        }
      }

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
        with: {
          category: {
            columns: {
              id: true,
              name: true,
              slug: true,
            },
          },
        },
        orderBy: [asc(faqs.order), asc(faqs.question)],
        limit,
        columns: {
          id: true,
          question: true,
          answer: true,
          order: true,
        },
      });

      // Group by category
      const groupedFaqs = faqsData.reduce(
        (acc, faq) => {
          const categoryName = faq.category?.name || "General";
          if (!acc[categoryName]) {
            acc[categoryName] = {
              category: faq.category,
              faqs: [],
            };
          }
          acc[categoryName].faqs.push(faq);
          return acc;
        },
        {} as Record<string, { category: any; faqs: any[] }>,
      );

      return {
        success: true,
        data: {
          faqs: faqsData,
          grouped: groupedFaqs,
          totalCount: faqsData.length,
        },
      };
    },
    {
      query: t.Object({
        limit: t.Optional(t.String()),
        category: t.Optional(t.String()),
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
        with: {
          category: {
            columns: {
              id: true,
              name: true,
              slug: true,
            },
          },
        },
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

  // Get FAQs by category slug
  .get(
    "/category/:slug",
    async ({ params: { slug }, query }) => {
      const limit = parseInt(query.limit) || 20;
      const search = query.search;

      // Find category first
      const category = await db.query.faqCategories.findFirst({
        where: and(
          eq(faqCategories.slug, slug),
          eq(faqCategories.isActive, true),
        ),
      });

      if (!category) {
        throw new NotFoundError("FAQ category not found");
      }

      let whereConditions = [
        eq(faqs.categoryId, category.id),
        eq(faqs.isActive, true),
      ];

      // Add search condition if provided
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
          category,
          faqs: faqsData,
          totalCount: faqsData.length,
        },
      };
    },
    {
      params: t.Object({
        slug: t.String(),
      }),
      query: t.Object({
        limit: t.Optional(t.String()),
        search: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get FAQs by category",
        tags: ["FAQ"],
      },
    },
  )

  // === ADMIN ROUTES ===
  .use(requireAdmin)

  // Get all FAQ categories (admin)
  .get(
    "/admin/categories",
    async ({ query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 20;
      const offset = (page - 1) * limit;
      const search = query.search;

      let whereCondition;
      if (search) {
        whereCondition = like(faqCategories.name, `%${search}%`);
      }

      const categoriesData = await db.query.faqCategories.findMany({
        where: whereCondition,
        orderBy: [asc(faqCategories.order), asc(faqCategories.name)],
        limit,
        offset,
      });

      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(faqCategories)
        .where(whereCondition);

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: categoriesData,
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
        summary: "Get all FAQ categories (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Create FAQ category
  .post(
    "/admin/categories",
    async ({ body, set }) => {
      const { name, description, order, isActive } = body;

      // Generate slug from name
      const slug = createSlug(name);

      // Check if slug already exists
      const existingCategory = await db.query.faqCategories.findFirst({
        where: eq(faqCategories.slug, slug),
      });

      if (existingCategory) {
        throw new DuplicateError("FAQ category with this name already exists");
      }

      const [newCategory] = await db
        .insert(faqCategories)
        .values({
          name,
          slug,
          description,
          order: order || 0,
          isActive: isActive ?? true,
        })
        .returning();

      set.status = 201;
      return {
        success: true,
        message: "FAQ category created successfully",
        data: { category: newCategory },
      };
    },
    {
      body: t.Object({
        name: t.String({ minLength: 1, maxLength: 100 }),
        description: t.Optional(t.String()),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Create FAQ category (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Update FAQ category
  .put(
    "/admin/categories/:id",
    async ({ params: { id }, body }) => {
      const existingCategory = await db.query.faqCategories.findFirst({
        where: eq(faqCategories.id, id),
      });

      if (!existingCategory) {
        throw new NotFoundError("FAQ category not found");
      }

      // Update slug if name is changed
      let slug = existingCategory.slug;
      if (body.name && body.name !== existingCategory.name) {
        slug = createSlug(body.name);

        // Check if new slug conflicts
        const conflictingCategory = await db.query.faqCategories.findFirst({
          where: and(
            eq(faqCategories.slug, slug),
            sql`${faqCategories.id} != ${id}`,
          ),
        });

        if (conflictingCategory) {
          throw new DuplicateError(
            "FAQ category with this name already exists",
          );
        }
      }

      const [updatedCategory] = await db
        .update(faqCategories)
        .set({
          ...body,
          slug,
          updatedAt: new Date(),
        })
        .where(eq(faqCategories.id, id))
        .returning();

      return {
        success: true,
        message: "FAQ category updated successfully",
        data: { category: updatedCategory },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        name: t.Optional(t.String({ minLength: 1, maxLength: 100 })),
        description: t.Optional(t.String()),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Update FAQ category (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Delete FAQ category
  .delete(
    "/admin/categories/:id",
    async ({ params: { id } }) => {
      const category = await db.query.faqCategories.findFirst({
        where: eq(faqCategories.id, id),
      });

      if (!category) {
        throw new NotFoundError("FAQ category not found");
      }

      // Check if category has FAQs
      const faqCount = await db
        .select({ count: sql<number>`count(*)` })
        .from(faqs)
        .where(eq(faqs.categoryId, id));

      if (faqCount[0].count > 0) {
        // Set FAQs to null category instead of failing
        await db
          .update(faqs)
          .set({ categoryId: null })
          .where(eq(faqs.categoryId, id));
      }

      // Delete category
      await db.delete(faqCategories).where(eq(faqCategories.id, id));

      return {
        success: true,
        message: "FAQ category deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete FAQ category (Admin)",
        tags: ["FAQ"],
      },
    },
  )

  // Get all FAQs (admin)
  .get(
    "/admin/all",
    async ({ query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 20;
      const offset = (page - 1) * limit;
      const search = query.search;
      const categoryId = query.categoryId;

      let whereConditions = [];

      if (search) {
        whereConditions.push(
          or(
            like(faqs.question, `%${search}%`),
            like(faqs.answer, `%${search}%`),
          ),
        );
      }

      if (categoryId) {
        whereConditions.push(eq(faqs.categoryId, categoryId));
      }

      const whereClause =
        whereConditions.length > 0 ? and(...whereConditions) : undefined;

      const faqsData = await db.query.faqs.findMany({
        where: whereClause,
        with: {
          category: {
            columns: {
              id: true,
              name: true,
              slug: true,
            },
          },
        },
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
        categoryId: t.Optional(t.String()),
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
        with: {
          category: true,
        },
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
      const { question, answer, categoryId, order, isActive } = body;

      // Verify category exists if provided
      if (categoryId) {
        const category = await db.query.faqCategories.findFirst({
          where: eq(faqCategories.id, categoryId),
        });

        if (!category) {
          throw new NotFoundError("FAQ category not found");
        }
      }

      const [newFaq] = await db
        .insert(faqs)
        .values({
          question,
          answer,
          categoryId: categoryId || null,
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
        categoryId: t.Optional(t.String()),
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

      // Verify category exists if being changed
      if (body.categoryId) {
        const category = await db.query.faqCategories.findFirst({
          where: eq(faqCategories.id, body.categoryId),
        });

        if (!category) {
          throw new NotFoundError("FAQ category not found");
        }
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
        categoryId: t.Optional(t.String()),
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

  // Reorder FAQs within a category
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

  // Reorder FAQ categories
  .post(
    "/admin/categories/reorder",
    async ({ body }) => {
      const { categoryIds } = body;

      // Update order for each category
      const updatePromises = categoryIds.map(
        (categoryId: string, index: number) =>
          db
            .update(faqCategories)
            .set({ order: index, updatedAt: new Date() })
            .where(eq(faqCategories.id, categoryId)),
      );

      await Promise.all(updatePromises);

      return {
        success: true,
        message: "FAQ category order updated successfully",
      };
    },
    {
      body: t.Object({
        categoryIds: t.Array(t.String()),
      }),
      detail: {
        summary: "Reorder FAQ categories (Admin)",
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

      // Get FAQ count by category
      const categoryStats = await db
        .select({
          categoryId: faqs.categoryId,
          categoryName: faqCategories.name,
          count: sql<number>`count(*)`,
        })
        .from(faqs)
        .leftJoin(faqCategories, eq(faqs.categoryId, faqCategories.id))
        .groupBy(faqs.categoryId, faqCategories.name);

      // Get total categories count
      const [{ totalCategories }] = await db
        .select({ totalCategories: sql<number>`count(*)` })
        .from(faqCategories);

      return {
        success: true,
        data: {
          totalFaqs: totalFaqs || 0,
          activeFaqs: activeFaqs || 0,
          totalCategories: totalCategories || 0,
          categoryStats,
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
