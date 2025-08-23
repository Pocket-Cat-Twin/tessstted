DO $$ BEGIN
 CREATE TYPE "user_role" AS ENUM('user', 'admin');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 CREATE TYPE "user_status" AS ENUM('pending', 'active', 'blocked');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 CREATE TYPE "order_status" AS ENUM('created', 'processing', 'checking', 'paid', 'shipped', 'delivered', 'cancelled');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 CREATE TYPE "story_status" AS ENUM('draft', 'published', 'archived');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 CREATE TYPE "config_type" AS ENUM('string', 'number', 'boolean', 'json');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "user_sessions" (
	"id" varchar(128) PRIMARY KEY NOT NULL,
	"user_id" uuid NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" varchar(255) NOT NULL,
	"password" varchar(255) NOT NULL,
	"name" varchar(100) NOT NULL,
	"phone" varchar(50),
	"role" "user_role" DEFAULT 'user' NOT NULL,
	"status" "user_status" DEFAULT 'pending' NOT NULL,
	"email_verified" boolean DEFAULT false NOT NULL,
	"email_verification_token" varchar(255),
	"password_reset_token" varchar(255),
	"password_reset_expires" timestamp,
	"avatar" text,
	"last_login_at" timestamp,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "users_email_unique" UNIQUE("email")
);
--> statement-breakpoint
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
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "order_status_history" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"order_id" uuid NOT NULL,
	"user_id" uuid,
	"from_status" "order_status",
	"to_status" "order_status" NOT NULL,
	"comment" text,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "orders" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"nomerok" varchar(50) NOT NULL,
	"user_id" uuid,
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
--> statement-breakpoint
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
--> statement-breakpoint
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
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "email_templates" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(100) NOT NULL,
	"subject" varchar(255) NOT NULL,
	"html_content" text NOT NULL,
	"text_content" text,
	"variables" text,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "email_templates_name_unique" UNIQUE("name")
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "faqs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"question" varchar(500) NOT NULL,
	"answer" text NOT NULL,
	"order" integer DEFAULT 0 NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
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
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "user_sessions" ADD CONSTRAINT "user_sessions_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "order_goods" ADD CONSTRAINT "order_goods_order_id_orders_id_fk" FOREIGN KEY ("order_id") REFERENCES "orders"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "order_status_history" ADD CONSTRAINT "order_status_history_order_id_orders_id_fk" FOREIGN KEY ("order_id") REFERENCES "orders"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "order_status_history" ADD CONSTRAINT "order_status_history_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "orders" ADD CONSTRAINT "orders_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE set null ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "stories" ADD CONSTRAINT "stories_author_id_users_id_fk" FOREIGN KEY ("author_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
