import { z } from "zod";

// Story status enum
export enum StoryStatus {
  DRAFT = "draft",
  PUBLISHED = "published",
  ARCHIVED = "archived",
}

// Story schema
export const storySchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1).max(200),
  link: z.string().min(1).max(100), // URL slug
  content: z.string().min(1),
  excerpt: z.string().max(500).optional(),
  thumbnail: z.string().optional(),
  images: z.array(z.string()).default([]),
  status: z.nativeEnum(StoryStatus).default(StoryStatus.DRAFT),
  publishedAt: z.date().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
  authorId: z.string().uuid(),
});

// Story creation schema
export const storyCreateSchema = z.object({
  title: z.string().min(1).max(200),
  link: z.string().min(1).max(100),
  content: z.string().min(1),
  excerpt: z.string().max(500).optional(),
  status: z.nativeEnum(StoryStatus).default(StoryStatus.DRAFT),
});

// Story update schema
export const storyUpdateSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  link: z.string().min(1).max(100).optional(),
  content: z.string().min(1).optional(),
  excerpt: z.string().max(500).optional(),
  status: z.nativeEnum(StoryStatus).optional(),
});

// Story query schema
export const storyQuerySchema = z.object({
  status: z.nativeEnum(StoryStatus).optional(),
  page: z.number().int().min(1).default(1),
  limit: z.number().int().min(1).max(100).default(10),
});

// Types
export type Story = z.infer<typeof storySchema>;
export type StoryCreate = z.infer<typeof storyCreateSchema>;
export type StoryUpdate = z.infer<typeof storyUpdateSchema>;
export type StoryQuery = z.infer<typeof storyQuerySchema>;

// Story with author information (for API responses)
export type StoryWithAuthor = Omit<Story, 'authorId'> & {
  author: {
    name: string;
  };
  metaTitle?: string;
  metaDescription?: string;
};
