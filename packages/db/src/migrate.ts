// MySQL8 Migration System
import { getPool } from "./connection";
import type { Pool } from "mysql2/promise";

export class MySQLMigrator {
  private pool: Pool;

  constructor(pool: Pool) {
    this.pool = pool;
  }

  async createInitialSchema(): Promise<void> {
    const sql = `
      CREATE DATABASE IF NOT EXISTS yuyu_lolita 
      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
      
      USE yuyu_lolita;
      
      -- Users table
      CREATE TABLE IF NOT EXISTS users (
        id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
        email VARCHAR(255) UNIQUE,
        phone VARCHAR(20) UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        name VARCHAR(100) NOT NULL,
        full_name VARCHAR(200),
        registration_method ENUM("email", "phone") NOT NULL,
        role ENUM("admin", "user") DEFAULT "user",
        status ENUM("pending", "active", "blocked") DEFAULT "pending",
        email_verified BOOLEAN DEFAULT FALSE,
        phone_verified BOOLEAN DEFAULT FALSE,
        avatar TEXT,
        contact_email VARCHAR(255),
        contact_phone VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        INDEX idx_email (email),
        INDEX idx_phone (phone),
        INDEX idx_status (status)
      ) ENGINE=InnoDB;

      -- Subscriptions table
      CREATE TABLE IF NOT EXISTS subscriptions (
        id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
        user_id CHAR(36) NOT NULL,
        tier ENUM("basic", "premium", "vip", "elite") NOT NULL,
        status ENUM("active", "expired", "cancelled") DEFAULT "active",
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_user_id (user_id),
        INDEX idx_status (status),
        INDEX idx_expires_at (expires_at)
      ) ENGINE=InnoDB;

      -- Orders table  
      CREATE TABLE IF NOT EXISTS orders (
        id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
        user_id CHAR(36) NOT NULL,
        customer_id CHAR(36),
        goods TEXT NOT NULL,
        weight_kg DECIMAL(8,2) NOT NULL,
        volume_cbm DECIMAL(8,3) NOT NULL,
        total_price_cny DECIMAL(10,2) NOT NULL,
        commission_rate DECIMAL(5,4) NOT NULL,
        commission_amount DECIMAL(10,2) NOT NULL,
        final_price DECIMAL(10,2) NOT NULL,
        status ENUM("pending", "processing", "completed", "cancelled") DEFAULT "pending",
        priority_processing BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_user_id (user_id),
        INDEX idx_status (status),
        INDEX idx_created_at (created_at)
      ) ENGINE=InnoDB;

      -- Blog posts
      CREATE TABLE IF NOT EXISTS blog_posts (
        id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
        title VARCHAR(500) NOT NULL,
        slug VARCHAR(500) UNIQUE NOT NULL,
        content LONGTEXT NOT NULL,
        excerpt TEXT,
        status ENUM("draft", "published") DEFAULT "draft",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        INDEX idx_slug (slug),
        INDEX idx_status (status)
      ) ENGINE=InnoDB;

      -- Stories
      CREATE TABLE IF NOT EXISTS stories (
        id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
        title VARCHAR(500) NOT NULL,
        link VARCHAR(500) UNIQUE NOT NULL,
        content LONGTEXT NOT NULL,
        status ENUM("draft", "published") DEFAULT "draft",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        INDEX idx_link (link),
        INDEX idx_status (status)
      ) ENGINE=InnoDB;
    `;

    await this.pool.execute(sql);
  }
}

export const runMigrations = async (): Promise<void> => {
  const pool = await getPool();
  const migrator = new MySQLMigrator(pool);
  await migrator.createInitialSchema();
};
