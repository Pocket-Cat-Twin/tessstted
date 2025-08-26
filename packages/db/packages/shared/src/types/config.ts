// Config and FAQ types for shared usage
export interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: string;
  order_index: number;
  published: boolean;
  created_at: Date;
  updated_at: Date;
}
