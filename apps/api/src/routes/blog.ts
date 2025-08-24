import { Elysia, t } from "elysia";
import {
  db,
  blogCategories,
  storyTags,
  storyCategoryRelations,
  storyTagRelations,
  stories,
  eq,
  and,
  desc,
  asc,
  sql,
  inArray,
} from "@lolita-fashion/db";
import { requireAdmin } from "../middleware/auth";
import {
  NotFoundError,
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

export const blogRoutes = new Elysia({ prefix: "/blog" })

  // === PUBLIC ROUTES ===

  // Get all active categories
  .get(
    "/categories",
    async ({ query }) => {
      const limit = parseInt(query.limit || "50") || 50;
      const showOnHomepage = query.homepage === "true";

      const conditions = [eq(blogCategories.isActive, true)];
      if (showOnHomepage) {
        conditions.push(eq(blogCategories.showOnHomepage, true));
      }

      const categoriesData = await db.query.blogCategories.findMany({
        where: and(...conditions),
        orderBy: [asc(blogCategories.order), asc(blogCategories.name)],
        limit,
        columns: {
          id: true,
          name: true,
          slug: true,
          description: true,
          color: true,
          metaTitle: true,
          metaDescription: true,
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
        homepage: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get active blog categories",
        tags: ["Blog"],
      },
    },
  )

  // Get category by slug
  .get(
    "/categories/:slug",
    async ({ params: { slug } }) => {
      const category = await db.query.blogCategories.findFirst({
        where: and(
          eq(blogCategories.slug, slug),
          eq(blogCategories.isActive, true),
        ),
      });

      if (!category) {
        throw new NotFoundError("Category not found");
      }

      return {
        success: true,
        data: { category },
      };
    },
    {
      params: t.Object({
        slug: t.String(),
      }),
      detail: {
        summary: "Get category by slug",
        tags: ["Blog"],
      },
    },
  )

  // Get all active tags
  .get(
    "/tags",
    async ({ query }) => {
      const limit = parseInt(query.limit || "50") || 50;
      const popular = query.popular === "true";

      const tagsData = await db.query.storyTags.findMany({
        orderBy: popular
          ? [desc(storyTags.usageCount), asc(storyTags.name)]
          : [asc(storyTags.name)],
        limit,
        columns: {
          id: true,
          name: true,
          slug: true,
          color: true,
          usageCount: true,
        },
      });

      return {
        success: true,
        data: tagsData,
      };
    },
    {
      query: t.Object({
        limit: t.Optional(t.String()),
        popular: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get blog tags",
        tags: ["Blog"],
      },
    },
  )

  // Get stories by category
  .get(
    "/categories/:slug/stories",
    async ({ params: { slug }, query }) => {
      const page = parseInt(query.page || "1") || 1;
      const limit = parseInt(query.limit || "10") || 10;
      const offset = (page - 1) * limit;

      // Find category first
      const category = await db.query.blogCategories.findFirst({
        where: and(
          eq(blogCategories.slug, slug),
          eq(blogCategories.isActive, true),
        ),
      });

      if (!category) {
        throw new NotFoundError("Category not found");
      }

      // Get stories in this category
      const storiesData = await db
        .select({
          id: stories.id,
          title: stories.title,
          link: stories.link,
          excerpt: stories.excerpt,
          thumbnail: stories.thumbnail,
          publishedAt: stories.publishedAt,
          createdAt: stories.createdAt,
        })
        .from(stories)
        .innerJoin(
          storyCategoryRelations,
          eq(stories.id, storyCategoryRelations.storyId),
        )
        .where(
          and(
            eq(storyCategoryRelations.categoryId, category.id),
            eq(stories.status, "published"),
          ),
        )
        .orderBy(desc(stories.publishedAt))
        .limit(limit)
        .offset(offset);

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(stories)
        .innerJoin(
          storyCategoryRelations,
          eq(stories.id, storyCategoryRelations.storyId),
        )
        .where(
          and(
            eq(storyCategoryRelations.categoryId, category.id),
            eq(stories.status, "published"),
          ),
        );

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: {
          category,
          stories: storiesData,
          pagination: {
            page,
            limit,
            total: count,
            totalPages,
            hasNext: page < totalPages,
            hasPrev: page > 1,
          },
        },
      };
    },
    {
      params: t.Object({
        slug: t.String(),
      }),
      query: t.Object({
        page: t.Optional(t.String()),
        limit: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get stories by category",
        tags: ["Blog"],
      },
    },
  )

  // Get stories by tag
  .get(
    "/tags/:slug/stories",
    async ({ params: { slug }, query }) => {
      const page = parseInt(query.page || "1") || 1;
      const limit = parseInt(query.limit || "10") || 10;
      const offset = (page - 1) * limit;

      // Find tag first
      const tag = await db.query.storyTags.findFirst({
        where: eq(storyTags.slug, slug),
      });

      if (!tag) {
        throw new NotFoundError("Tag not found");
      }

      // Get stories with this tag
      const storiesData = await db
        .select({
          id: stories.id,
          title: stories.title,
          link: stories.link,
          excerpt: stories.excerpt,
          thumbnail: stories.thumbnail,
          publishedAt: stories.publishedAt,
          createdAt: stories.createdAt,
        })
        .from(stories)
        .innerJoin(storyTagRelations, eq(stories.id, storyTagRelations.storyId))
        .where(
          and(
            eq(storyTagRelations.tagId, tag.id),
            eq(stories.status, "published"),
          ),
        )
        .orderBy(desc(stories.publishedAt))
        .limit(limit)
        .offset(offset);

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(stories)
        .innerJoin(storyTagRelations, eq(stories.id, storyTagRelations.storyId))
        .where(
          and(
            eq(storyTagRelations.tagId, tag.id),
            eq(stories.status, "published"),
          ),
        );

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: {
          tag,
          stories: storiesData,
          pagination: {
            page,
            limit,
            total: count,
            totalPages,
            hasNext: page < totalPages,
            hasPrev: page > 1,
          },
        },
      };
    },
    {
      params: t.Object({
        slug: t.String(),
      }),
      query: t.Object({
        page: t.Optional(t.String()),
        limit: t.Optional(t.String()),
      }),
      detail: {
        summary: "Get stories by tag",
        tags: ["Blog"],
      },
    },
  )

  // === ADMIN ROUTES ===
  .use(requireAdmin)

  // Get all categories (admin)
  .get(
    "/admin/categories",
    async ({ query }) => {
      const page = parseInt(query.page || "1") || 1;
      const limit = parseInt(query.limit || "20") || 20;
      const offset = (page - 1) * limit;
      const search = query.search;

      let whereCondition;
      if (search) {
        whereCondition = sql`${blogCategories.name} ILIKE ${`%${search}%`}`;
      }

      const categoriesData = await db.query.blogCategories.findMany({
        where: whereCondition,
        orderBy: [asc(blogCategories.order), asc(blogCategories.name)],
        limit,
        offset,
      });

      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(blogCategories)
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
        summary: "Get all categories (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Create category
  .post(
    "/admin/categories",
    async ({ body, set }) => {
      const {
        name,
        description,
        color,
        metaTitle,
        metaDescription,
        order,
        isActive,
        showOnHomepage,
      } = body;

      // Generate slug from name
      const slug = createSlug(name);

      // Check if slug already exists
      const existingCategory = await db.query.blogCategories.findFirst({
        where: eq(blogCategories.slug, slug),
      });

      if (existingCategory) {
        throw new DuplicateError("Category with this name already exists");
      }

      const [newCategory] = await db
        .insert(blogCategories)
        .values({
          name,
          slug,
          description,
          color: color || "#3B82F6",
          metaTitle,
          metaDescription,
          order: order || 0,
          isActive: isActive ?? true,
          showOnHomepage: showOnHomepage ?? true,
        })
        .returning();

      set.status = 201;
      return {
        success: true,
        message: "Category created successfully",
        data: { category: newCategory },
      };
    },
    {
      body: t.Object({
        name: t.String({ minLength: 1, maxLength: 100 }),
        description: t.Optional(t.String()),
        color: t.Optional(t.String()),
        metaTitle: t.Optional(t.String()),
        metaDescription: t.Optional(t.String()),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
        showOnHomepage: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Create category (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Update category
  .put(
    "/admin/categories/:id",
    async ({ params: { id }, body }) => {
      const existingCategory = await db.query.blogCategories.findFirst({
        where: eq(blogCategories.id, id),
      });

      if (!existingCategory) {
        throw new NotFoundError("Category not found");
      }

      // Update slug if name is changed
      let slug = existingCategory.slug;
      if (body.name && body.name !== existingCategory.name) {
        slug = createSlug(body.name);

        // Check if new slug conflicts
        const conflictingCategory = await db.query.blogCategories.findFirst({
          where: and(
            eq(blogCategories.slug, slug),
            sql`${blogCategories.id} != ${id}`,
          ),
        });

        if (conflictingCategory) {
          throw new DuplicateError("Category with this name already exists");
        }
      }

      const [updatedCategory] = await db
        .update(blogCategories)
        .set({
          ...body,
          slug,
          updatedAt: new Date(),
        })
        .where(eq(blogCategories.id, id))
        .returning();

      return {
        success: true,
        message: "Category updated successfully",
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
        color: t.Optional(t.String()),
        metaTitle: t.Optional(t.String()),
        metaDescription: t.Optional(t.String()),
        order: t.Optional(t.Number()),
        isActive: t.Optional(t.Boolean()),
        showOnHomepage: t.Optional(t.Boolean()),
      }),
      detail: {
        summary: "Update category (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Delete category
  .delete(
    "/admin/categories/:id",
    async ({ params: { id } }) => {
      const category = await db.query.blogCategories.findFirst({
        where: eq(blogCategories.id, id),
      });

      if (!category) {
        throw new NotFoundError("Category not found");
      }

      // Delete category (cascade will handle relations)
      await db.delete(blogCategories).where(eq(blogCategories.id, id));

      return {
        success: true,
        message: "Category deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete category (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Get all tags (admin)
  .get(
    "/admin/tags",
    async ({ query }) => {
      const page = parseInt(query.page || "1") || 1;
      const limit = parseInt(query.limit || "50") || 50;
      const offset = (page - 1) * limit;
      const search = query.search;

      let whereCondition;
      if (search) {
        whereCondition = sql`${storyTags.name} ILIKE ${`%${search}%`}`;
      }

      const tagsData = await db.query.storyTags.findMany({
        where: whereCondition,
        orderBy: [desc(storyTags.usageCount), asc(storyTags.name)],
        limit,
        offset,
      });

      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(storyTags)
        .where(whereCondition);

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: tagsData,
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
        summary: "Get all tags (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Create tag
  .post(
    "/admin/tags",
    async ({ body, set }) => {
      const { name, color } = body;

      // Generate slug from name
      const slug = createSlug(name);

      // Check if slug already exists
      const existingTag = await db.query.storyTags.findFirst({
        where: eq(storyTags.slug, slug),
      });

      if (existingTag) {
        throw new DuplicateError("Tag with this name already exists");
      }

      const [newTag] = await db
        .insert(storyTags)
        .values({
          name,
          slug,
          color: color || "#6B7280",
          usageCount: 0,
        })
        .returning();

      set.status = 201;
      return {
        success: true,
        message: "Tag created successfully",
        data: { tag: newTag },
      };
    },
    {
      body: t.Object({
        name: t.String({ minLength: 1, maxLength: 50 }),
        color: t.Optional(t.String()),
      }),
      detail: {
        summary: "Create tag (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Update tag
  .put(
    "/admin/tags/:id",
    async ({ params: { id }, body }) => {
      const existingTag = await db.query.storyTags.findFirst({
        where: eq(storyTags.id, id),
      });

      if (!existingTag) {
        throw new NotFoundError("Tag not found");
      }

      // Update slug if name is changed
      let slug = existingTag.slug;
      if (body.name && body.name !== existingTag.name) {
        slug = createSlug(body.name);

        // Check if new slug conflicts
        const conflictingTag = await db.query.storyTags.findFirst({
          where: and(eq(storyTags.slug, slug), sql`${storyTags.id} != ${id}`),
        });

        if (conflictingTag) {
          throw new DuplicateError("Tag with this name already exists");
        }
      }

      const [updatedTag] = await db
        .update(storyTags)
        .set({
          ...body,
          slug,
          updatedAt: new Date(),
        })
        .where(eq(storyTags.id, id))
        .returning();

      return {
        success: true,
        message: "Tag updated successfully",
        data: { tag: updatedTag },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        name: t.Optional(t.String({ minLength: 1, maxLength: 50 })),
        color: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update tag (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Delete tag
  .delete(
    "/admin/tags/:id",
    async ({ params: { id } }) => {
      const tag = await db.query.storyTags.findFirst({
        where: eq(storyTags.id, id),
      });

      if (!tag) {
        throw new NotFoundError("Tag not found");
      }

      // Delete tag (cascade will handle relations)
      await db.delete(storyTags).where(eq(storyTags.id, id));

      return {
        success: true,
        message: "Tag deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete tag (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Assign categories to story
  .post(
    "/admin/stories/:storyId/categories",
    async ({ params: { storyId }, body }) => {
      const { categoryIds } = body;

      // Verify story exists
      const story = await db.query.stories.findFirst({
        where: eq(stories.id, storyId),
      });

      if (!story) {
        throw new NotFoundError("Story not found");
      }

      // Remove existing category relations
      await db
        .delete(storyCategoryRelations)
        .where(eq(storyCategoryRelations.storyId, storyId));

      // Add new category relations
      if (categoryIds.length > 0) {
        const relations = categoryIds.map((categoryId) => ({
          storyId,
          categoryId,
        }));

        await db.insert(storyCategoryRelations).values(relations);
      }

      return {
        success: true,
        message: "Story categories updated successfully",
      };
    },
    {
      params: t.Object({
        storyId: t.String(),
      }),
      body: t.Object({
        categoryIds: t.Array(t.String()),
      }),
      detail: {
        summary: "Assign categories to story (Admin)",
        tags: ["Blog"],
      },
    },
  )

  // Assign tags to story
  .post(
    "/admin/stories/:storyId/tags",
    async ({ params: { storyId }, body }) => {
      const { tagIds } = body;

      // Verify story exists
      const story = await db.query.stories.findFirst({
        where: eq(stories.id, storyId),
      });

      if (!story) {
        throw new NotFoundError("Story not found");
      }

      // Get existing tag relations
      const existingRelations = await db.query.storyTagRelations.findMany({
        where: eq(storyTagRelations.storyId, storyId),
      });

      const existingTagIds = existingRelations.map((r) => r.tagId);

      // Remove existing tag relations
      await db
        .delete(storyTagRelations)
        .where(eq(storyTagRelations.storyId, storyId));

      // Update usage counts (decrease for removed tags)
      if (existingTagIds.length > 0) {
        await db
          .update(storyTags)
          .set({ usageCount: sql`${storyTags.usageCount} - 1` })
          .where(inArray(storyTags.id, existingTagIds));
      }

      // Add new tag relations
      if (tagIds.length > 0) {
        const relations = tagIds.map((tagId) => ({
          storyId,
          tagId,
        }));

        await db.insert(storyTagRelations).values(relations);

        // Update usage counts (increase for new tags)
        await db
          .update(storyTags)
          .set({ usageCount: sql`${storyTags.usageCount} + 1` })
          .where(inArray(storyTags.id, tagIds));
      }

      return {
        success: true,
        message: "Story tags updated successfully",
      };
    },
    {
      params: t.Object({
        storyId: t.String(),
      }),
      body: t.Object({
        tagIds: t.Array(t.String()),
      }),
      detail: {
        summary: "Assign tags to story (Admin)",
        tags: ["Blog"],
      },
    },
  );
