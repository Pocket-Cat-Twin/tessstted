const fs = require('fs');

// Полная консолидированная схема со ВСЕМИ элементами
const fullSchema = `-- ПОЛНАЯ КОНСОЛИДИРОВАННАЯ СХЕМА БД
-- Версия: 0000 (обновленная)
-- Создана: 2025-08-25
-- Описание: Полная схема базы данных со всеми таблицами, enum'ами и связями
-- Включает ВСЕ элементы схемы TypeScript

-- ===============================================
-- STEP 1: CREATE ALL ENUMS
-- ===============================================

-- User management enums
DO $$ BEGIN
 CREATE TYPE "user_role" AS ENUM('user', 'admin');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "user_status" AS ENUM('pending', 'active', 'blocked');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "registration_method" AS ENUM('email', 'phone');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- КРИТИЧЕСКИ ВАЖНЫЙ ENUM (был пропущен в старой миграции!)
DO $$ BEGIN
 CREATE TYPE "user_verification_status" AS ENUM('unverified', 'partial', 'full');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Order management enums
DO $$ BEGIN
 CREATE TYPE "order_status" AS ENUM('created', 'processing', 'checking', 'paid', 'shipped', 'delivered', 'cancelled');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Story and content enums
DO $$ BEGIN
 CREATE TYPE "story_status" AS ENUM('draft', 'published', 'archived');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Configuration enum
DO $$ BEGIN
 CREATE TYPE "config_type" AS ENUM('string', 'number', 'boolean', 'json');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Subscription enums
DO $$ BEGIN
 CREATE TYPE "subscription_tier" AS ENUM('free', 'group', 'elite', 'vip_temp');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "subscription_status" AS ENUM('active', 'expired', 'cancelled', 'pending_payment');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Verification enums
DO $$ BEGIN
 CREATE TYPE "verification_type" AS ENUM('email_registration', 'phone_registration', 'password_reset', 'phone_change', 'email_change', 'login_2fa');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "verification_status" AS ENUM('pending', 'verified', 'expired', 'failed');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Notification enums
DO $$ BEGIN
 CREATE TYPE "notification_type" AS ENUM('subscription_expiring', 'subscription_expired', 'subscription_renewed', 'order_status', 'system_announcement', 'promotion');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "notification_channel" AS ENUM('email', 'sms', 'push', 'in_app');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "notification_status" AS ENUM('pending', 'sent', 'failed', 'delivered', 'read');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Webhook enums
DO $$ BEGIN
 CREATE TYPE "webhook_event" AS ENUM('user.created', 'user.updated', 'user.deleted', 'order.created', 'order.updated', 'order.status_changed', 'subscription.created', 'subscription.renewed', 'subscription.expired', 'subscription.cancelled', 'payment.completed', 'payment.failed');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 CREATE TYPE "webhook_status" AS ENUM('pending', 'success', 'failed', 'retry');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- ===============================================
-- STEP 2: CREATE CORE TABLES
-- ===============================================

-- Users table с ПОЛНОЙ схемой (включая все недостающие поля)
CREATE TABLE IF NOT EXISTS "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	
	-- Authentication - email OR phone required
	"email" varchar(255),
	"phone" varchar(50),
	"password" varchar(255) NOT NULL,
	
	-- Registration method tracking
	"registration_method" "registration_method" NOT NULL,
	
	-- User information
	"name" varchar(100),
	"full_name" varchar(200),
	
	-- Contact information (can be updated after registration)
	"contact_phone" varchar(50),
	"contact_email" varchar(255),
	
	-- User role and status
	"role" "user_role" DEFAULT 'user' NOT NULL,
	"status" "user_status" DEFAULT 'pending' NOT NULL,
	
	-- Enhanced verification status
	"email_verified" boolean DEFAULT false NOT NULL,
	"phone_verified" boolean DEFAULT false NOT NULL,
	
	-- Overall verification status (КРИТИЧЕСКИ ВАЖНОЕ ПОЛЕ!)
	"overall_verification_status" "user_verification_status" DEFAULT 'unverified' NOT NULL,
	
	-- Security enhancements (были пропущены в старой миграции!)
	"failed_login_attempts" integer DEFAULT 0 NOT NULL,
	"locked_until" timestamp,
	"email_verified_at" timestamp,
	"phone_verified_at" timestamp,
	
	-- Legacy verification tokens (deprecated - use verification_tokens table)
	"email_verification_token" varchar(255),
	"password_reset_token" varchar(255),
	"password_reset_expires" timestamp,
	
	-- Profile
	"avatar" text,
	
	-- Activity tracking
	"last_login_at" timestamp,
	
	-- Timestamps
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- User sessions table
CREATE TABLE IF NOT EXISTS "user_sessions" (
	"id" varchar(128) PRIMARY KEY NOT NULL,
	"user_id" uuid NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);

-- Customers table (ОБНОВЛЕННАЯ СХЕМА со всеми полями)
CREATE TABLE IF NOT EXISTS "customers" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(255) NOT NULL,
	"full_name" varchar(255),  -- Было пропущено!
	"email" varchar(255),
	"phone" varchar(50),
	"contact_phone" varchar(50),  -- Было пропущено!
	"notes" text,  -- Было пропущено!
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL  -- Было пропущено!
);

-- Customer addresses table (ОБНОВЛЕННАЯ СХЕМА)
CREATE TABLE IF NOT EXISTS "customer_addresses" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"customer_id" uuid NOT NULL,
	"address_type" varchar(50) DEFAULT 'shipping' NOT NULL,
	"full_address" text NOT NULL,
	"city" varchar(100) NOT NULL,
	"postal_code" varchar(20),
	"country" varchar(100) DEFAULT 'Россия' NOT NULL,
	"address_comments" text,  -- Было пропущено!
	"is_default" boolean DEFAULT false NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL  -- Было пропущено!
);

-- ===============================================
-- STEP 3: CREATE ORDER TABLES
-- ===============================================

-- Orders table
CREATE TABLE IF NOT EXISTS "orders" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"nomerok" varchar(50) NOT NULL,
	"user_id" uuid,
	"customer_id" uuid,
	"customer_name" varchar(100) NOT NULL,
	"customer_phone" varchar(50) NOT NULL,
	"customer_email" varchar(255),
	"delivery_address" text NOT NULL,
	"delivery_method" varchar(100) NOT NULL,
	"delivery_cost" numeric(10, 2) DEFAULT '0' NOT NULL,
	"payment_method" varchar(100) NOT NULL,
	"payment_screenshot" text,
	"subtotal_yuan" numeric(10, 2) NOT NULL,
	"total_commission" numeric(10, 2) NOT NULL,
	"current_kurs" numeric(8, 4) NOT NULL,
	"discount" numeric(10, 2) DEFAULT '0' NOT NULL,
	"total_yuan" numeric(10, 2) NOT NULL,
	"total_ruble" numeric(10, 2) NOT NULL,
	"status" "order_status" DEFAULT 'created' NOT NULL,
	"notes" text,
	"is_archived" boolean DEFAULT false NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "orders_nomerok_unique" UNIQUE("nomerok")
);

-- Order goods table
CREATE TABLE IF NOT EXISTS "order_goods" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"order_id" uuid NOT NULL,
	"name" varchar(500) NOT NULL,
	"link" text,
	"screenshot" text,
	"quantity" integer NOT NULL,
	"price_yuan" numeric(10, 2) NOT NULL,
	"commission" numeric(10, 2) NOT NULL,
	"total_yuan" numeric(10, 2) NOT NULL,
	"total_ruble" numeric(10, 2) NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- Order status history table
CREATE TABLE IF NOT EXISTS "order_status_history" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"order_id" uuid NOT NULL,
	"user_id" uuid,
	"from_status" "order_status",
	"to_status" "order_status" NOT NULL,
	"comment" text,
	"created_at" timestamp DEFAULT now() NOT NULL
);

-- ===============================================
-- STEP 4: CREATE SUBSCRIPTION TABLES
-- ===============================================

-- Subscription features table
CREATE TABLE IF NOT EXISTS "subscription_features" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"tier" "subscription_tier" NOT NULL,
	"max_storage_days" integer NOT NULL,
	"processing_time_hours" integer NOT NULL,
	"support_response_hours" integer NOT NULL,
	"can_participate_in_promotions" boolean DEFAULT false NOT NULL,
	"can_combine_orders" boolean DEFAULT false NOT NULL,
	"has_priority_processing" boolean DEFAULT false NOT NULL,
	"has_personal_support" boolean DEFAULT false NOT NULL,
	"has_product_inspection" boolean DEFAULT false NOT NULL,
	"description" varchar(500),
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- User subscriptions table
CREATE TABLE IF NOT EXISTS "user_subscriptions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"tier" "subscription_tier" NOT NULL,
	"status" "subscription_status" DEFAULT 'pending_payment' NOT NULL,
	"price" numeric(10, 2) NOT NULL,
	"currency" varchar(3) DEFAULT 'RUB' NOT NULL,
	"start_date" timestamp NOT NULL,
	"end_date" timestamp NOT NULL,
	"auto_renew" boolean DEFAULT false NOT NULL,
	"payment_reference" varchar(255),
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- Subscription history table
CREATE TABLE IF NOT EXISTS "subscription_history" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"subscription_id" uuid,
	"action" varchar(50) NOT NULL,
	"from_tier" "subscription_tier",
	"to_tier" "subscription_tier",
	"amount" numeric(10, 2),
	"payment_method" varchar(100),
	"notes" varchar(500),
	"created_at" timestamp DEFAULT now() NOT NULL
);

-- ===============================================
-- STEP 5: CREATE CONTENT TABLES
-- ===============================================

-- Stories table
CREATE TABLE IF NOT EXISTS "stories" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"title" varchar(200) NOT NULL,
	"link" varchar(100) NOT NULL,
	"content" text NOT NULL,
	"excerpt" varchar(500),
	"thumbnail" text,
	"images" json DEFAULT '[]'::json,
	"status" "story_status" DEFAULT 'draft' NOT NULL,
	"published_at" timestamp,
	"author_id" uuid NOT NULL,
	"meta_title" varchar(255),
	"meta_description" varchar(500),
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "stories_link_unique" UNIQUE("link")
);

-- Blog categories table
CREATE TABLE IF NOT EXISTS "blog_categories" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(100) NOT NULL,
	"slug" varchar(100) NOT NULL,
	"description" text,
	"color" varchar(7) DEFAULT '#3B82F6' NOT NULL,
	"meta_title" varchar(255),
	"meta_description" varchar(500),
	"order" integer DEFAULT 0 NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"show_on_homepage" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "blog_categories_slug_unique" UNIQUE("slug")
);

-- Story category relations
CREATE TABLE IF NOT EXISTS "story_category_relations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"story_id" uuid NOT NULL,
	"category_id" uuid NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);

-- Story tags table
CREATE TABLE IF NOT EXISTS "story_tags" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(50) NOT NULL,
	"slug" varchar(50) NOT NULL,
	"color" varchar(7) DEFAULT '#6B7280' NOT NULL,
	"usage_count" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "story_tags_name_unique" UNIQUE("name"),
	CONSTRAINT "story_tags_slug_unique" UNIQUE("slug")
);

-- Story tag relations
CREATE TABLE IF NOT EXISTS "story_tag_relations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"story_id" uuid NOT NULL,
	"tag_id" uuid NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);

-- ===============================================
-- STEP 6: CREATE VERIFICATION TABLES
-- ===============================================

-- Verification tokens table
CREATE TABLE IF NOT EXISTS "verification_tokens" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"type" "verification_type" NOT NULL,
	"status" "verification_status" DEFAULT 'pending' NOT NULL,
	"email" varchar(255),
	"phone" varchar(50),
	"token" varchar(255) NOT NULL,
	"code" varchar(10) NOT NULL,
	"attempt_count" integer DEFAULT 0 NOT NULL,
	"max_attempts" integer DEFAULT 3 NOT NULL,
	"expires_at" timestamp NOT NULL,
	"verified_at" timestamp,
	"ip_address" varchar(45),
	"user_agent" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "verification_tokens_token_unique" UNIQUE("token")
);

-- SMS logs table
CREATE TABLE IF NOT EXISTS "sms_logs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"phone" varchar(50) NOT NULL,
	"message" text NOT NULL,
	"provider" varchar(50) NOT NULL,
	"provider_id" varchar(255),
	"status" varchar(50) NOT NULL,
	"status_message" text,
	"cost" varchar(50),
	"sent_at" timestamp DEFAULT now() NOT NULL,
	"delivered_at" timestamp,
	"failed_at" timestamp
);

-- Email logs table
CREATE TABLE IF NOT EXISTS "email_logs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" varchar(255) NOT NULL,
	"subject" varchar(255) NOT NULL,
	"template_name" varchar(100),
	"status" varchar(50) NOT NULL,
	"status_message" text,
	"message_id" varchar(255),
	"sent_at" timestamp DEFAULT now() NOT NULL,
	"delivered_at" timestamp,
	"bounced_at" timestamp,
	"failed_at" timestamp
);

-- Verification rate limit table
CREATE TABLE IF NOT EXISTS "verification_rate_limit" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"identifier" varchar(255) NOT NULL,
	"type" "verification_type" NOT NULL,
	"attempt_count" integer DEFAULT 1 NOT NULL,
	"window_start" timestamp DEFAULT now() NOT NULL,
	"blocked_until" timestamp,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- ===============================================
-- STEP 7: CREATE NOTIFICATION TABLES
-- ===============================================

-- Notification history table
CREATE TABLE IF NOT EXISTS "notification_history" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"subscription_id" uuid,
	"order_id" uuid,
	"type" "notification_type" NOT NULL,
	"subtype" text,
	"channel" "notification_channel" NOT NULL,
	"recipient" text NOT NULL,
	"subject" text,
	"content" text NOT NULL,
	"status" "notification_status" DEFAULT 'pending' NOT NULL,
	"status_message" text,
	"scheduled_for" timestamp,
	"sent_at" timestamp,
	"delivered_at" timestamp,
	"read_at" timestamp,
	"metadata" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- Notification preferences table
CREATE TABLE IF NOT EXISTS "notification_preferences" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"email_enabled" boolean DEFAULT true NOT NULL,
	"sms_enabled" boolean DEFAULT false NOT NULL,
	"push_enabled" boolean DEFAULT true NOT NULL,
	"in_app_enabled" boolean DEFAULT true NOT NULL,
	"subscription_notifications" boolean DEFAULT true NOT NULL,
	"order_notifications" boolean DEFAULT true NOT NULL,
	"promotion_notifications" boolean DEFAULT false NOT NULL,
	"system_notifications" boolean DEFAULT true NOT NULL,
	"quiet_hours_start" text,
	"quiet_hours_end" text,
	"timezone" text DEFAULT 'Europe/Moscow' NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- Email templates table
CREATE TABLE IF NOT EXISTS "email_templates" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"display_name" text,
	"subject" text NOT NULL,
	"html_content" text NOT NULL,
	"text_content" text,
	"variables" text,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "email_templates_name_unique" UNIQUE("name")
);

-- ===============================================
-- STEP 8: CREATE WEBHOOK TABLES
-- ===============================================

-- Webhook subscriptions table
CREATE TABLE IF NOT EXISTS "webhook_subscriptions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"url" text NOT NULL,
	"events" json NOT NULL,
	"secret" varchar(255) NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"retry_count" integer DEFAULT 0 NOT NULL,
	"max_retries" integer DEFAULT 3 NOT NULL,
	"description" text,
	"headers" json,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	"last_triggered_at" timestamp
);

-- Webhook logs table
CREATE TABLE IF NOT EXISTS "webhook_logs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"subscription_id" uuid,
	"event" "webhook_event" NOT NULL,
	"payload" json NOT NULL,
	"url" text NOT NULL,
	"method" varchar(10) DEFAULT 'POST' NOT NULL,
	"headers" json,
	"status" "webhook_status" DEFAULT 'pending' NOT NULL,
	"http_status" integer,
	"response_body" text,
	"response_headers" json,
	"attempt_number" integer DEFAULT 1 NOT NULL,
	"processing_time_ms" integer,
	"error_message" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"sent_at" timestamp,
	"completed_at" timestamp
);

-- ===============================================
-- STEP 9: CREATE CONFIGURATION TABLES
-- ===============================================

-- Configuration table
CREATE TABLE IF NOT EXISTS "config" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"key" varchar(100) NOT NULL,
	"value" text NOT NULL,
	"description" text,
	"type" "config_type" DEFAULT 'string' NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "config_key_unique" UNIQUE("key")
);

-- FAQ Categories table (было ПОЛНОСТЬЮ пропущено в старой миграции!)
CREATE TABLE IF NOT EXISTS "faq_categories" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(100) NOT NULL,
	"slug" varchar(100) NOT NULL,
	"description" text,
	"order" integer DEFAULT 0 NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "faq_categories_slug_unique" UNIQUE("slug")
);

-- FAQs table
CREATE TABLE IF NOT EXISTS "faqs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"question" varchar(500) NOT NULL,
	"answer" text NOT NULL,
	"order" integer DEFAULT 0 NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- Uploads table
CREATE TABLE IF NOT EXISTS "uploads" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"original_name" varchar(255) NOT NULL,
	"filename" varchar(255) NOT NULL,
	"mimetype" varchar(100) NOT NULL,
	"size" integer NOT NULL,
	"path" text NOT NULL,
	"url" text NOT NULL,
	"uploaded_by" uuid,
	"created_at" timestamp DEFAULT now() NOT NULL
);

-- ===============================================
-- STEP 10: CREATE UNIQUE CONSTRAINTS AND INDEXES
-- ===============================================

-- Users table constraints
CREATE UNIQUE INDEX IF NOT EXISTS "users_email_unique_idx" ON "users" ("email") WHERE "email" IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS "users_phone_unique_idx" ON "users" ("phone") WHERE "phone" IS NOT NULL;

-- Add constraint to ensure user has either email OR phone
DO $$ BEGIN
    ALTER TABLE "users" ADD CONSTRAINT "users_email_or_phone_required" 
    CHECK (("email" IS NOT NULL) OR ("phone" IS NOT NULL));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Performance indexes for verification tables
CREATE INDEX IF NOT EXISTS "verification_tokens_user_id_idx" ON "verification_tokens" ("user_id");
CREATE INDEX IF NOT EXISTS "verification_tokens_token_idx" ON "verification_tokens" ("token");
CREATE INDEX IF NOT EXISTS "verification_tokens_type_status_idx" ON "verification_tokens" ("type", "status");
CREATE INDEX IF NOT EXISTS "verification_tokens_expires_at_idx" ON "verification_tokens" ("expires_at");

CREATE INDEX IF NOT EXISTS "sms_logs_phone_idx" ON "sms_logs" ("phone");
CREATE INDEX IF NOT EXISTS "sms_logs_status_idx" ON "sms_logs" ("status");
CREATE INDEX IF NOT EXISTS "sms_logs_sent_at_idx" ON "sms_logs" ("sent_at");

CREATE INDEX IF NOT EXISTS "email_logs_email_idx" ON "email_logs" ("email");
CREATE INDEX IF NOT EXISTS "email_logs_status_idx" ON "email_logs" ("status");
CREATE INDEX IF NOT EXISTS "email_logs_sent_at_idx" ON "email_logs" ("sent_at");

CREATE INDEX IF NOT EXISTS "verification_rate_limit_identifier_type_idx" ON "verification_rate_limit" ("identifier", "type");
CREATE INDEX IF NOT EXISTS "verification_rate_limit_window_start_idx" ON "verification_rate_limit" ("window_start");

-- Notification indexes
CREATE INDEX IF NOT EXISTS "notification_history_user_id_idx" ON "notification_history" ("user_id");
CREATE INDEX IF NOT EXISTS "notification_history_type_idx" ON "notification_history" ("type");
CREATE INDEX IF NOT EXISTS "notification_history_status_idx" ON "notification_history" ("status");
CREATE INDEX IF NOT EXISTS "notification_history_scheduled_for_idx" ON "notification_history" ("scheduled_for");
CREATE INDEX IF NOT EXISTS "notification_history_created_at_idx" ON "notification_history" ("created_at");
CREATE INDEX IF NOT EXISTS "notification_history_user_type_idx" ON "notification_history" ("user_id", "type");
CREATE INDEX IF NOT EXISTS "notification_history_subscription_idx" ON "notification_history" ("subscription_id", "type");
CREATE INDEX IF NOT EXISTS "notification_preferences_user_id_idx" ON "notification_preferences" ("user_id");

-- Email template indexes
CREATE INDEX IF NOT EXISTS "email_templates_name_idx" ON "email_templates" ("name");
CREATE INDEX IF NOT EXISTS "email_templates_is_active_idx" ON "email_templates" ("is_active");

-- ===============================================
-- STEP 11: CREATE FOREIGN KEY CONSTRAINTS
-- ===============================================

-- User sessions
DO $$ BEGIN
 ALTER TABLE "user_sessions" ADD CONSTRAINT "user_sessions_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Customer addresses
DO $$ BEGIN
 ALTER TABLE "customer_addresses" ADD CONSTRAINT "customer_addresses_customer_id_customers_id_fk" FOREIGN KEY ("customer_id") REFERENCES "customers"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Orders
DO $$ BEGIN
 ALTER TABLE "orders" ADD CONSTRAINT "orders_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "orders" ADD CONSTRAINT "orders_customer_id_customers_id_fk" FOREIGN KEY ("customer_id") REFERENCES "customers"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Order goods
DO $$ BEGIN
 ALTER TABLE "order_goods" ADD CONSTRAINT "order_goods_order_id_orders_id_fk" FOREIGN KEY ("order_id") REFERENCES "orders"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Order status history
DO $$ BEGIN
 ALTER TABLE "order_status_history" ADD CONSTRAINT "order_status_history_order_id_orders_id_fk" FOREIGN KEY ("order_id") REFERENCES "orders"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "order_status_history" ADD CONSTRAINT "order_status_history_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Subscriptions
DO $$ BEGIN
 ALTER TABLE "user_subscriptions" ADD CONSTRAINT "user_subscriptions_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "subscription_history" ADD CONSTRAINT "subscription_history_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "subscription_history" ADD CONSTRAINT "subscription_history_subscription_id_user_subscriptions_id_fk" FOREIGN KEY ("subscription_id") REFERENCES "user_subscriptions"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Stories
DO $$ BEGIN
 ALTER TABLE "stories" ADD CONSTRAINT "stories_author_id_users_id_fk" FOREIGN KEY ("author_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Story relations
DO $$ BEGIN
 ALTER TABLE "story_category_relations" ADD CONSTRAINT "story_category_relations_story_id_stories_id_fk" FOREIGN KEY ("story_id") REFERENCES "stories"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "story_category_relations" ADD CONSTRAINT "story_category_relations_category_id_blog_categories_id_fk" FOREIGN KEY ("category_id") REFERENCES "blog_categories"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "story_tag_relations" ADD CONSTRAINT "story_tag_relations_story_id_stories_id_fk" FOREIGN KEY ("story_id") REFERENCES "stories"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
 ALTER TABLE "story_tag_relations" ADD CONSTRAINT "story_tag_relations_tag_id_story_tags_id_fk" FOREIGN KEY ("tag_id") REFERENCES "story_tags"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Verification tokens
DO $$ BEGIN
 ALTER TABLE "verification_tokens" ADD CONSTRAINT "verification_tokens_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Notification preferences
DO $$ BEGIN
 ALTER TABLE "notification_preferences" ADD CONSTRAINT "notification_preferences_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Notification history
DO $$ BEGIN
 ALTER TABLE "notification_history" ADD CONSTRAINT "notification_history_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Webhook logs
DO $$ BEGIN
 ALTER TABLE "webhook_logs" ADD CONSTRAINT "webhook_logs_subscription_id_webhook_subscriptions_id_fk" FOREIGN KEY ("subscription_id") REFERENCES "webhook_subscriptions"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- Uploads
DO $$ BEGIN
 ALTER TABLE "uploads" ADD CONSTRAINT "uploads_uploaded_by_users_id_fk" FOREIGN KEY ("uploaded_by") REFERENCES "users"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- ===============================================
-- STEP 12: CREATE FUNCTIONS AND TRIGGERS
-- ===============================================

-- Function to cleanup expired verification tokens
CREATE OR REPLACE FUNCTION cleanup_expired_verification_tokens() 
RETURNS void AS $
BEGIN
    DELETE FROM "verification_tokens" 
    WHERE "expires_at" < NOW() 
    AND "status" = 'pending';
    
    DELETE FROM "verification_rate_limit" 
    WHERE "window_start" < NOW() - INTERVAL '24 hours';
END;
$ LANGUAGE plpgsql;

-- Function to auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- Apply triggers for updated_at columns
DROP TRIGGER IF EXISTS update_users_updated_at ON "users";
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON "users" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_customers_updated_at ON "customers";
CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON "customers" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_orders_updated_at ON "orders";
CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON "orders" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_order_goods_updated_at ON "order_goods";
CREATE TRIGGER update_order_goods_updated_at 
    BEFORE UPDATE ON "order_goods" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_subscriptions_updated_at ON "user_subscriptions";
CREATE TRIGGER update_user_subscriptions_updated_at 
    BEFORE UPDATE ON "user_subscriptions" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_subscription_features_updated_at ON "subscription_features";
CREATE TRIGGER update_subscription_features_updated_at 
    BEFORE UPDATE ON "subscription_features" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_stories_updated_at ON "stories";
CREATE TRIGGER update_stories_updated_at 
    BEFORE UPDATE ON "stories" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_blog_categories_updated_at ON "blog_categories";
CREATE TRIGGER update_blog_categories_updated_at 
    BEFORE UPDATE ON "blog_categories" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_story_tags_updated_at ON "story_tags";
CREATE TRIGGER update_story_tags_updated_at 
    BEFORE UPDATE ON "story_tags" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_verification_tokens_updated_at ON "verification_tokens";
CREATE TRIGGER update_verification_tokens_updated_at 
    BEFORE UPDATE ON "verification_tokens" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_verification_rate_limit_updated_at ON "verification_rate_limit";
CREATE TRIGGER update_verification_rate_limit_updated_at 
    BEFORE UPDATE ON "verification_rate_limit" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_notification_history_updated_at ON "notification_history";
CREATE TRIGGER update_notification_history_updated_at 
    BEFORE UPDATE ON "notification_history" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_notification_preferences_updated_at ON "notification_preferences";
CREATE TRIGGER update_notification_preferences_updated_at 
    BEFORE UPDATE ON "notification_preferences" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_webhook_subscriptions_updated_at ON "webhook_subscriptions";
CREATE TRIGGER update_webhook_subscriptions_updated_at 
    BEFORE UPDATE ON "webhook_subscriptions" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_config_updated_at ON "config";
CREATE TRIGGER update_config_updated_at 
    BEFORE UPDATE ON "config" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_email_templates_updated_at ON "email_templates";
CREATE TRIGGER update_email_templates_updated_at 
    BEFORE UPDATE ON "email_templates" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_faq_categories_updated_at ON "faq_categories";
CREATE TRIGGER update_faq_categories_updated_at 
    BEFORE UPDATE ON "faq_categories" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- STEP 13: COMPLETION LOG
-- ===============================================

-- Mark migration as completed
INSERT INTO "config" ("key", "value", "type", "description", "updated_at") 
VALUES (
    'migration_consolidated_completed', 
    'true', 
    'boolean', 
    'Consolidated database schema migration completed on ' || NOW()::text || ' - ПОЛНАЯ СХЕМА СО ВСЕМИ ЭЛЕМЕНТАМИ',
    NOW()
) ON CONFLICT ("key") DO UPDATE SET 
    "value" = 'true',
    "updated_at" = NOW();

-- ===============================================
-- MIGRATION COMPLETED SUCCESSFULLY
-- ===============================================

-- ✅ ПОЛНАЯ СХЕМА ВКЛЮЧАЕТ:
-- ✅ 28 таблиц со всеми колонками из TypeScript schema
-- ✅ 16 enum'ов включая user_verification_status
-- ✅ Все индексы и constraints
-- ✅ Все foreign key связи
-- ✅ Функции и triggers для updated_at
-- ✅ Критически важные поля: overall_verification_status, failed_login_attempts, etc.
-- ✅ Недостающие таблицы: faq_categories
-- ✅ Все недостающие колонки в users, customers, customer_addresses
-- ✅ Полная совместимость с TypeScript schema files
`;

console.log('✅ Создаем полную консолидированную схему...');
fs.writeFileSync('./migrations/0000_consolidated_schema.sql', fullSchema);
console.log('✅ Файл 0000_consolidated_schema.sql обновлен полной схемой');

// Обновляем журнал для одной миграции
const journal = {
  "version": "5",
  "dialect": "pg",
  "entries": [
    {
      "idx": 0,
      "version": "5", 
      "when": Date.now(),
      "tag": "0000_consolidated_schema",
      "breakpoints": true
    }
  ]
};

fs.writeFileSync('./migrations/meta/_journal.json', JSON.stringify(journal, null, 2));
console.log('✅ Журнал _journal.json обновлен для одной миграции');

// Удаляем дополнительные файлы миграций
try {
  fs.unlinkSync('./migrations/0001_eager_mentor.sql');
  console.log('✅ Удален файл 0001_eager_mentor.sql');
} catch (e) {
  console.log('- Файл 0001_eager_mentor.sql уже удален');
}

// Удаляем snapshot новой миграции
try {
  fs.unlinkSync('./migrations/meta/0001_snapshot.json');  
  console.log('✅ Удален файл 0001_snapshot.json');
} catch (e) {
  console.log('- Файл 0001_snapshot.json не найден');
}

console.log('🎉 ВСЕ ГОТОВО! Теперь у вас ОДНА полная миграция со ВСЕМИ элементами схемы');
console.log('📊 Включает: 28 таблиц, 16 enum-ов, все недостающие колонки');
console.log('✅ overall_verification_status и все критические поля включены');