// Story types for shared usage
export interface Story {
  id: string;
  title: string;
  content: string;
  author_id: string;
  published: boolean;
  link: string;
  created_at: Date;
  updated_at: Date;
}

export interface StoryWithAuthor extends Story {
  author_name: string;
  author_email?: string;
}
