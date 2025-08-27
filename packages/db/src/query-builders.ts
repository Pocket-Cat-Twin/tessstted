// Native MySQL Query Builders
import type { Pool, RowDataPacket, ResultSetHeader } from "mysql2/promise";
import type { User, Order, Subscription, Address } from "./schema";

export class QueryBuilder {
  private pool: Pool;

  constructor(pool: Pool) {
    this.pool = pool;
  }

  // User queries
  async createUser(userData: Omit<User, "id" | "created_at" | "updated_at">): Promise<string> {
    const sql = `
      INSERT INTO users (email, phone, password_hash, name, full_name, registration_method, role, status, email_verified, phone_verified, avatar, contact_email, contact_phone)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;
    
    const [result] = await this.pool.execute<ResultSetHeader>(sql, [
      userData.email,
      userData.phone,
      userData.password_hash,
      userData.name,
      userData.full_name,
      userData.registration_method,
      userData.role,
      userData.status,
      userData.email_verified,
      userData.phone_verified,
      userData.avatar,
      userData.contact_email,
      userData.contact_phone
    ]);
    
    return result.insertId.toString();
  }

  async getUserById(id: string): Promise<User | null> {
    const sql = "SELECT * FROM users WHERE id = ?";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [id]);
    return rows[0] as User || null;
  }

  async getUserByEmail(email: string): Promise<User | null> {
    const sql = "SELECT * FROM users WHERE email = ?";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [email]);
    return rows[0] as User || null;
  }

  async getUserByPhone(phone: string): Promise<User | null> {
    const sql = "SELECT * FROM users WHERE phone = ?";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [phone]);
    return rows[0] as User || null;
  }

  async getUserByEmailOrPhone(email?: string, phone?: string): Promise<User | null> {
    if (email) {
      return this.getUserByEmail(email);
    } else if (phone) {
      return this.getUserByPhone(phone);
    }
    return null;
  }

  // Order queries
  async createOrder(orderData: Omit<Order, "id" | "created_at" | "updated_at">): Promise<string> {
    const sql = `
      INSERT INTO orders (user_id, customer_id, goods, weight_kg, volume_cbm, total_price_cny, commission_rate, commission_amount, final_price, status, priority_processing)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;
    
    const [result] = await this.pool.execute<ResultSetHeader>(sql, [
      orderData.user_id,
      orderData.customer_id,
      orderData.goods,
      orderData.weight_kg,
      orderData.volume_cbm,
      orderData.total_price_cny,
      orderData.commission_rate,
      orderData.commission_amount,
      orderData.final_price,
      orderData.status,
      orderData.priority_processing
    ]);
    
    return result.insertId.toString();
  }

  async getOrdersByUserId(userId: string): Promise<Order[]> {
    const sql = "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [userId]);
    return rows as Order[];
  }

  // Subscription queries
  async createSubscription(subData: Omit<Subscription, "id" | "created_at" | "updated_at">): Promise<string> {
    const sql = `
      INSERT INTO subscriptions (user_id, tier, status, expires_at)
      VALUES (?, ?, ?, ?)
    `;
    
    const [result] = await this.pool.execute<ResultSetHeader>(sql, [
      subData.user_id,
      subData.tier,
      subData.status,
      subData.expires_at
    ]);
    
    return result.insertId.toString();
  }

  async getActiveSubscription(userId: string): Promise<Subscription | null> {
    const sql = "SELECT * FROM subscriptions WHERE user_id = ? AND status = \"active\" AND expires_at > NOW() ORDER BY expires_at DESC LIMIT 1";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [userId]);
    return rows[0] as Subscription || null;
  }

  // Address queries
  async createAddress(addressData: Omit<Address, "id" | "created_at" | "updated_at">): Promise<string> {
    // If this address is set as default, unset all other default addresses for this user
    if (addressData.is_default) {
      await this.pool.execute(
        "UPDATE addresses SET is_default = FALSE WHERE user_id = ?",
        [addressData.user_id]
      );
    }

    const sql = `
      INSERT INTO addresses (user_id, full_address, city, postal_code, country, address_comments, is_default)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    const [result] = await this.pool.execute<ResultSetHeader>(sql, [
      addressData.user_id,
      addressData.full_address,
      addressData.city,
      addressData.postal_code,
      addressData.country,
      addressData.address_comments,
      addressData.is_default
    ]);
    
    return result.insertId.toString();
  }

  async getAddressesByUserId(userId: string): Promise<Address[]> {
    const sql = "SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC, created_at DESC";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [userId]);
    return rows as Address[];
  }

  async getAddressById(addressId: string, userId: string): Promise<Address | null> {
    const sql = "SELECT * FROM addresses WHERE id = ? AND user_id = ?";
    const [rows] = await this.pool.execute<RowDataPacket[]>(sql, [addressId, userId]);
    return rows[0] as Address || null;
  }

  async updateAddress(addressId: string, userId: string, updateData: Partial<Omit<Address, "id" | "user_id" | "created_at" | "updated_at">>): Promise<boolean> {
    // If this address is being set as default, unset all other default addresses for this user
    if (updateData.is_default) {
      await this.pool.execute(
        "UPDATE addresses SET is_default = FALSE WHERE user_id = ? AND id != ?",
        [userId, addressId]
      );
    }

    const fields = Object.keys(updateData).map(key => `${key} = ?`).join(', ');
    const values = Object.values(updateData);
    
    if (fields.length === 0) return false;

    const sql = `UPDATE addresses SET ${fields} WHERE id = ? AND user_id = ?`;
    const [result] = await this.pool.execute<ResultSetHeader>(sql, [...values, addressId, userId]);
    
    return result.affectedRows > 0;
  }

  async deleteAddress(addressId: string, userId: string): Promise<boolean> {
    const sql = "DELETE FROM addresses WHERE id = ? AND user_id = ?";
    const [result] = await this.pool.execute<ResultSetHeader>(sql, [addressId, userId]);
    
    return result.affectedRows > 0;
  }
}

// Export convenience functions for standalone use
import { getPool } from "./connection.js";

export async function getUserByEmail(email: string): Promise<User | null> {
  const pool = await getPool();
  const builder = new QueryBuilder(pool);
  return builder.getUserByEmail(email);
}

export async function getUserById(id: string): Promise<User | null> {
  const pool = await getPool();
  const builder = new QueryBuilder(pool);
  return builder.getUserById(id);
}

export async function getUserByPhone(phone: string): Promise<User | null> {
  const pool = await getPool();
  const builder = new QueryBuilder(pool);
  return builder.getUserByPhone(phone);
}
