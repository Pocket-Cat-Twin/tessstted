// MySQL8 Schema Definitions
// Native SQL schema without ORM

export interface User {
  id: string;
  email?: string;
  phone?: string;
  password_hash: string;
  name: string;
  full_name?: string;
  registration_method: "email" | "phone";
  role: "admin" | "user";
  status: "pending" | "active" | "blocked";
  email_verified: boolean;
  phone_verified: boolean;
  avatar?: string;
  contact_email?: string;
  contact_phone?: string;
  created_at: Date;
  updated_at: Date;
}

export interface Order {
  id: string;
  user_id: string;
  customer_id?: string;
  goods: string;
  weight_kg: number;
  volume_cbm: number;
  total_price_cny: number;
  commission_rate: number;
  commission_amount: number;
  final_price: number;
  status: "pending" | "processing" | "completed" | "cancelled";
  priority_processing: boolean;
  created_at: Date;
  updated_at: Date;
}

export interface Subscription {
  id: string;
  user_id: string;
  tier: "basic" | "premium" | "vip" | "elite";
  status: "active" | "expired" | "cancelled";
  expires_at: Date;
  created_at: Date;
  updated_at: Date;
}

// Add other interfaces as needed
export interface BlogPost {
  id: string;
  title: string;
  slug: string;
  content: string;
  excerpt?: string;
  status: "draft" | "published";
  created_at: Date;
  updated_at: Date;
}

export interface Story {
  id: string;
  title: string;
  link: string;
  content: string;
  status: "draft" | "published";
  created_at: Date;
  updated_at: Date;
}
