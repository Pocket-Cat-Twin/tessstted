// User types for shared usage
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
