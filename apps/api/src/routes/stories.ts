import { Elysia, t } from "elysia";
import { db, stories, eq, and, desc, sql } from "@lolita-fashion/db";
import {
  storyCreateSchema,
  storyUpdateSchema,
  StoryStatus,
  createSlug,
} from "@lolita-fashion/shared";
import { requireAdmin } from "../middleware/auth";
import {
  NotFoundError,
  ValidationError,
  DuplicateError,
} from "../middleware/error";

export const storyRoutes = new Elysia({ prefix: "/stories" })

  // Public routes

  // Get published stories
  .get(
    "/",
    async ({ query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 10;
      const offset = (page - 1) * limit;

      // Get published stories
      const storiesResult = await db.query.stories.findMany({
        where: eq(stories.status, StoryStatus.PUBLISHED),
        with: {
          author: {
            columns: {
              name: true,
            },
          },
        },
        columns: {
          id: true,
          title: true,
          link: true,
          excerpt: true,
          thumbnail: true,
          publishedAt: true,
          createdAt: true,
        },
        orderBy: desc(stories.publishedAt),
        limit,
        offset,
      });

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(stories)
        .where(eq(stories.status, StoryStatus.PUBLISHED));

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: storiesResult,
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
      }),
      detail: {
        summary: "Get published stories",
        tags: ["Stories"],
      },
    },
  )

  // Get story by link (public)
  .get(
    "/:link",
    async ({ params: { link } }) => {
      const story = await db.query.stories.findFirst({
        where: and(
          eq(stories.link, link),
          eq(stories.status, StoryStatus.PUBLISHED),
        ),
        with: {
          author: {
            columns: {
              name: true,
            },
          },
        },
      });

      if (!story) {
        throw new NotFoundError("Story not found");
      }

      return {
        success: true,
        data: { story },
      };
    },
    {
      params: t.Object({
        link: t.String(),
      }),
      detail: {
        summary: "Get story by link",
        tags: ["Stories"],
      },
    },
  )

  // Admin routes
  .use(requireAdmin)

  // Get all stories (admin)
  .get(
    "/admin/all",
    async ({ query }) => {
      const page = parseInt(query.page) || 1;
      const limit = parseInt(query.limit) || 10;
      const status = query.status as StoryStatus;
      const search = query.search;
      const offset = (page - 1) * limit;

      // Build where conditions
      const conditions = [];
      if (status) {
        conditions.push(eq(stories.status, status));
      }
      if (search) {
        conditions.push(
          sql`(${stories.title} ILIKE ${`%${search}%`} OR ${stories.content} ILIKE ${`%${search}%`})`,
        );
      }

      const whereClause =
        conditions.length > 0 ? and(...conditions) : undefined;

      // Get stories
      const storiesResult = await db.query.stories.findMany({
        where: whereClause,
        with: {
          author: {
            columns: {
              name: true,
            },
          },
        },
        orderBy: desc(stories.createdAt),
        limit,
        offset,
      });

      // Get total count
      const [{ count }] = await db
        .select({ count: sql<number>`count(*)` })
        .from(stories)
        .where(whereClause);

      const totalPages = Math.ceil(count / limit);

      return {
        success: true,
        data: storiesResult,
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
        summary: "Get all stories (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Get story by ID (admin)
  .get(
    "/admin/:id",
    async ({ params: { id } }) => {
      const story = await db.query.stories.findFirst({
        where: eq(stories.id, id),
        with: {
          author: {
            columns: {
              name: true,
              email: true,
            },
          },
        },
      });

      if (!story) {
        throw new NotFoundError("Story not found");
      }

      return {
        success: true,
        data: { story },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Get story by ID (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Create story
  .post(
    "/",
    async ({ body, user, set }) => {
      const validation = storyCreateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid story data");
      }

      const storyData = validation.data;

      // Generate link from title if not provided
      const link = storyData.link || createSlug(storyData.title);

      // Check if link already exists
      const existingStory = await db.query.stories.findFirst({
        where: eq(stories.link, link),
      });

      if (existingStory) {
        throw new DuplicateError("Story with this link already exists");
      }

      // Create story
      const [newStory] = await db
        .insert(stories)
        .values({
          title: storyData.title,
          link,
          content: storyData.content,
          excerpt: storyData.excerpt,
          status: storyData.status || StoryStatus.DRAFT,
          metaTitle: storyData.metaTitle,
          metaDescription: storyData.metaDescription,
          authorId: user.id,
          ...(storyData.status === StoryStatus.PUBLISHED && {
            publishedAt: new Date(),
          }),
        })
        .returning();

      set.status = 201;
      return {
        success: true,
        message: "Story created successfully",
        data: { story: newStory },
      };
    },
    {
      body: t.Object({
        title: t.String({ minLength: 1 }),
        link: t.Optional(t.String()),
        content: t.String({ minLength: 1 }),
        excerpt: t.Optional(t.String()),
        status: t.Optional(t.String()),
        metaTitle: t.Optional(t.String()),
        metaDescription: t.Optional(t.String()),
      }),
      detail: {
        summary: "Create story (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Update story
  .put(
    "/:id",
    async ({ params: { id }, body }) => {
      const validation = storyUpdateSchema.safeParse(body);
      if (!validation.success) {
        throw new ValidationError("Invalid story update data");
      }

      const updateData = validation.data;

      // Find existing story
      const existingStory = await db.query.stories.findFirst({
        where: eq(stories.id, id),
      });

      if (!existingStory) {
        throw new NotFoundError("Story not found");
      }

      // Check if link is being changed and if it conflicts
      if (updateData.link && updateData.link !== existingStory.link) {
        const conflictingStory = await db.query.stories.findFirst({
          where: eq(stories.link, updateData.link),
        });

        if (conflictingStory) {
          throw new DuplicateError("Story with this link already exists");
        }
      }

      // Track publishing status change
      const wasPublished = existingStory.status === StoryStatus.PUBLISHED;
      const willBePublished = updateData.status === StoryStatus.PUBLISHED;
      const publishedAt =
        !wasPublished && willBePublished
          ? new Date()
          : wasPublished && willBePublished
            ? existingStory.publishedAt
            : null;

      // Update story
      const [updatedStory] = await db
        .update(stories)
        .set({
          ...updateData,
          ...(publishedAt !== null && { publishedAt }),
          updatedAt: new Date(),
        })
        .where(eq(stories.id, id))
        .returning();

      return {
        success: true,
        message: "Story updated successfully",
        data: { story: updatedStory },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        title: t.Optional(t.String()),
        link: t.Optional(t.String()),
        content: t.Optional(t.String()),
        excerpt: t.Optional(t.String()),
        status: t.Optional(t.String()),
        metaTitle: t.Optional(t.String()),
        metaDescription: t.Optional(t.String()),
      }),
      detail: {
        summary: "Update story (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Update story images
  .put(
    "/:id/images",
    async ({ params: { id }, body }) => {
      const { thumbnail, images } = body as {
        thumbnail?: string;
        images?: string[];
      };

      // Find story
      const existingStory = await db.query.stories.findFirst({
        where: eq(stories.id, id),
      });

      if (!existingStory) {
        throw new NotFoundError("Story not found");
      }

      // Update images
      const [updatedStory] = await db
        .update(stories)
        .set({
          ...(thumbnail && { thumbnail }),
          ...(images && { images }),
          updatedAt: new Date(),
        })
        .where(eq(stories.id, id))
        .returning();

      return {
        success: true,
        message: "Story images updated successfully",
        data: { story: updatedStory },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        thumbnail: t.Optional(t.String()),
        images: t.Optional(t.Array(t.String())),
      }),
      detail: {
        summary: "Update story images (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Publish/unpublish story
  .post(
    "/:id/publish",
    async ({ params: { id }, body }) => {
      const { publish } = body as { publish: boolean };

      // Find story
      const existingStory = await db.query.stories.findFirst({
        where: eq(stories.id, id),
      });

      if (!existingStory) {
        throw new NotFoundError("Story not found");
      }

      const newStatus = publish ? StoryStatus.PUBLISHED : StoryStatus.DRAFT;
      const publishedAt =
        publish && existingStory.status !== StoryStatus.PUBLISHED
          ? new Date()
          : !publish
            ? null
            : existingStory.publishedAt;

      // Update story status
      const [updatedStory] = await db
        .update(stories)
        .set({
          status: newStatus,
          publishedAt,
          updatedAt: new Date(),
        })
        .where(eq(stories.id, id))
        .returning();

      return {
        success: true,
        message: `Story ${publish ? "published" : "unpublished"} successfully`,
        data: { story: updatedStory },
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      body: t.Object({
        publish: t.Boolean(),
      }),
      detail: {
        summary: "Publish/unpublish story (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Delete story
  .delete(
    "/:id",
    async ({ params: { id } }) => {
      const story = await db.query.stories.findFirst({
        where: eq(stories.id, id),
      });

      if (!story) {
        throw new NotFoundError("Story not found");
      }

      // Delete story
      await db.delete(stories).where(eq(stories.id, id));

      return {
        success: true,
        message: "Story deleted successfully",
      };
    },
    {
      params: t.Object({
        id: t.String(),
      }),
      detail: {
        summary: "Delete story (Admin)",
        tags: ["Stories"],
      },
    },
  )

  // Get story statistics
  .get(
    "/stats/overview",
    async () => {
      // Get story counts by status
      const statusCounts = await db
        .select({
          status: stories.status,
          count: sql<number>`count(*)`,
        })
        .from(stories)
        .groupBy(stories.status);

      // Get recent stories count
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
      const [{ recentStoriesCount }] = await db
        .select({
          recentStoriesCount: sql<number>`count(*)`,
        })
        .from(stories)
        .where(sql`${stories.createdAt} >= ${thirtyDaysAgo}`);

      // Get total published stories
      const [{ publishedStoriesCount }] = await db
        .select({
          publishedStoriesCount: sql<number>`count(*)`,
        })
        .from(stories)
        .where(eq(stories.status, StoryStatus.PUBLISHED));

      return {
        success: true,
        data: {
          statusCounts,
          recentStoriesCount: recentStoriesCount || 0,
          publishedStoriesCount: publishedStoriesCount || 0,
        },
      };
    },
    {
      detail: {
        summary: "Get story statistics (Admin)",
        tags: ["Stories"],
      },
    },
  );
