// Order types for shared usage
export interface Order {
  id: string;
  user_id: string;
  customer_id?: string;
  goods: string;
  weight_kg: number;
  volume_cbm: number;
  total_price_cny: number;
  total_price_rub: number;
  commission_rate: number;
  commission_amount: number;
  status: "pending" | "processing" | "shipped" | "delivered" | "cancelled";
  shipping_method: "air" | "sea" | "land";
  tracking_number?: string;
  notes?: string;
  created_at: Date;
  updated_at: Date;
}

export interface OrderCreate {
  customer_id?: string;
  goods: string;
  weight_kg: number;
  volume_cbm: number;
  total_price_cny: number;
  total_price_rub: number;
  commission_rate: number;
  commission_amount: number;
  shipping_method: "air" | "sea" | "land";
  notes?: string;
}
