-- Migration: Add multi-auth support (email OR phone registration)
-- Version: 0002
-- Created: 2025-08-16
-- Description: Updates users table to support both email and phone authentication

-- STEP 1: Create registration_method enum if not exists
DO $$ BEGIN
 CREATE TYPE "registration_method" AS ENUM('email', 'phone');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- STEP 2: Create verification_type enum if not exists  
DO $$ BEGIN
 CREATE TYPE "verification_type" AS ENUM('email_registration', 'phone_registration', 'password_reset', 'phone_change', 'email_change', 'login_2fa');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- STEP 3: Create verification_status enum if not exists
DO $$ BEGIN
 CREATE TYPE "verification_status" AS ENUM('pending', 'verified', 'expired', 'failed');
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- STEP 4: Backup existing users table structure for rollback
CREATE TABLE IF NOT EXISTS "users_backup_0002" AS SELECT * FROM "users";

-- STEP 5: Modify users table schema
-- Remove NOT NULL constraint from email (allow phone-only users)
ALTER TABLE "users" ALTER COLUMN "email" DROP NOT NULL;

-- Make email field unique only when not null
ALTER TABLE "users" DROP CONSTRAINT IF EXISTS "users_email_unique";
CREATE UNIQUE INDEX "users_email_unique_idx" ON "users" ("email") WHERE "email" IS NOT NULL;

-- Add phone field with unique constraint when not null
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "phone" varchar(50);
CREATE UNIQUE INDEX "users_phone_unique_idx" ON "users" ("phone") WHERE "phone" IS NOT NULL;

-- Add registration method tracking
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "registration_method" "registration_method" DEFAULT 'email';

-- Add phone verification support
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "phone_verified" boolean DEFAULT false;

-- Add contact information fields (separate from auth credentials)
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "contact_email" varchar(255);
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "contact_phone" varchar(50);
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "full_name" varchar(200);

-- STEP 6: Update existing users to have email as registration method
UPDATE "users" SET "registration_method" = 'email' WHERE "registration_method" IS NULL;
UPDATE "users" SET "phone_verified" = false WHERE "phone_verified" IS NULL;

-- STEP 7: Add constraint to ensure user has either email OR phone
ALTER TABLE "users" ADD CONSTRAINT "users_email_or_phone_required" 
CHECK (("email" IS NOT NULL) OR ("phone" IS NOT NULL));

-- STEP 8: Create verification_tokens table if not exists
CREATE TABLE IF NOT EXISTS "verification_tokens" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid REFERENCES "users"("id") ON DELETE cascade,
	"type" "verification_type" NOT NULL,
	"status" "verification_status" DEFAULT 'pending' NOT NULL,
	"email" varchar(255),
	"phone" varchar(50),
	"token" varchar(255) NOT NULL UNIQUE,
	"code" varchar(10) NOT NULL,
	"attempt_count" integer DEFAULT 0 NOT NULL,
	"max_attempts" integer DEFAULT 3 NOT NULL,
	"expires_at" timestamp NOT NULL,
	"verified_at" timestamp,
	"ip_address" varchar(45),
	"user_agent" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);

-- STEP 9: Create SMS and email logs tables if not exists
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

-- STEP 10: Create rate limiting table if not exists
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

-- STEP 11: Create indexes for performance
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

-- STEP 12: Update foreign key constraints
DO $$ BEGIN
 ALTER TABLE "verification_tokens" ADD CONSTRAINT "verification_tokens_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;

-- STEP 13: Create cleanup function for expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_verification_tokens() 
RETURNS void AS $$
BEGIN
    DELETE FROM "verification_tokens" 
    WHERE "expires_at" < NOW() 
    AND "status" = 'pending';
    
    DELETE FROM "verification_rate_limit" 
    WHERE "window_start" < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- STEP 14: Create trigger to auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON "users";
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON "users" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_verification_tokens_updated_at ON "verification_tokens";
CREATE TRIGGER update_verification_tokens_updated_at 
    BEFORE UPDATE ON "verification_tokens" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_verification_rate_limit_updated_at ON "verification_rate_limit";
CREATE TRIGGER update_verification_rate_limit_updated_at 
    BEFORE UPDATE ON "verification_rate_limit" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- STEP 15: Log migration completion
INSERT INTO "config" ("key", "value", "type", "description", "updated_at") 
VALUES (
    'migration_0002_completed', 
    'true', 
    'boolean', 
    'Multi-auth support migration completed on ' || NOW()::text,
    NOW()
) ON CONFLICT ("key") DO UPDATE SET 
    "value" = 'true',
    "updated_at" = NOW();

-- Migration completed successfully
-- Users can now register/login with either email OR phone
-- Enhanced verification system with SMS support
-- Rate limiting and comprehensive logging
-- Rollback available via users_backup_0002 table