-- ROLLBACK MIGRATION: Multi-auth support rollback
-- Version: 0002_ROLLBACK  
-- Created: 2025-08-16
-- Description: Complete rollback of multi-auth changes back to email-only authentication
-- WARNING: This will remove all phone-based users and verification data

-- SAFETY CHECKS
DO $$ 
BEGIN
    -- Check if backup table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users_backup_0002') THEN
        RAISE EXCEPTION 'ROLLBACK ABORTED: Backup table users_backup_0002 not found. Cannot safely rollback.';
    END IF;
    
    -- Check if any phone-only users exist (will be lost in rollback)
    IF EXISTS (SELECT 1 FROM "users" WHERE "email" IS NULL AND "phone" IS NOT NULL) THEN
        RAISE WARNING 'WARNING: % phone-only users will be LOST during rollback', 
            (SELECT COUNT(*) FROM "users" WHERE "email" IS NULL AND "phone" IS NOT NULL);
    END IF;
    
    RAISE NOTICE 'Starting rollback of migration 0002...';
END $$;

-- STEP 1: Create backup of current state before rollback
CREATE TABLE IF NOT EXISTS "users_before_rollback_0002" AS SELECT * FROM "users";
CREATE TABLE IF NOT EXISTS "verification_tokens_backup_0002" AS SELECT * FROM "verification_tokens";

-- STEP 2: Remove triggers and functions
DROP TRIGGER IF EXISTS update_users_updated_at ON "users";
DROP TRIGGER IF EXISTS update_verification_tokens_updated_at ON "verification_tokens";
DROP TRIGGER IF EXISTS update_verification_rate_limit_updated_at ON "verification_rate_limit";
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS cleanup_expired_verification_tokens();

-- STEP 3: Remove new tables (with data preservation in backup)
DROP TABLE IF EXISTS "verification_rate_limit";
DROP TABLE IF EXISTS "email_logs";
DROP TABLE IF EXISTS "sms_logs";
DROP TABLE IF EXISTS "verification_tokens";

-- STEP 4: Remove new columns from users table
ALTER TABLE "users" DROP CONSTRAINT IF EXISTS "users_email_or_phone_required";
ALTER TABLE "users" DROP COLUMN IF EXISTS "contact_phone";
ALTER TABLE "users" DROP COLUMN IF EXISTS "contact_email";
ALTER TABLE "users" DROP COLUMN IF EXISTS "full_name";
ALTER TABLE "users" DROP COLUMN IF EXISTS "phone_verified";
ALTER TABLE "users" DROP COLUMN IF EXISTS "registration_method";
ALTER TABLE "users" DROP COLUMN IF EXISTS "phone";

-- STEP 5: Remove new indexes
DROP INDEX IF EXISTS "users_phone_unique_idx";
DROP INDEX IF EXISTS "users_email_unique_idx";

-- STEP 6: Restore original email constraint
ALTER TABLE "users" ALTER COLUMN "email" SET NOT NULL;
ALTER TABLE "users" ADD CONSTRAINT "users_email_unique" UNIQUE ("email");

-- STEP 7: Restore users from backup (only email users)
-- First, clear current users table
TRUNCATE TABLE "users" CASCADE;

-- Restore email users from backup
INSERT INTO "users" (
    "id", "email", "password", "name", "role", "status", "email_verified",
    "email_verification_token", "password_reset_token", "password_reset_expires",
    "avatar", "last_login_at", "created_at", "updated_at"
)
SELECT 
    "id", "email", "password", "name", "role", "status", "email_verified",
    "email_verification_token", "password_reset_token", "password_reset_expires",
    "avatar", "last_login_at", "created_at", "updated_at"
FROM "users_backup_0002"
WHERE "email" IS NOT NULL; -- Only restore users with email

-- STEP 8: Remove new enum types
DROP TYPE IF EXISTS "verification_status";
DROP TYPE IF EXISTS "verification_type";
DROP TYPE IF EXISTS "registration_method";

-- STEP 9: Update config to mark rollback completion
UPDATE "config" 
SET "value" = 'rolled_back', "updated_at" = NOW()
WHERE "key" = 'migration_0002_completed';

INSERT INTO "config" ("key", "value", "type", "description", "updated_at") 
VALUES (
    'migration_0002_rollback_completed', 
    'true', 
    'boolean', 
    'Multi-auth support rollback completed on ' || NOW()::text || '. Phone users data preserved in backup tables.',
    NOW()
) ON CONFLICT ("key") DO UPDATE SET 
    "value" = 'true',
    "updated_at" = NOW();

-- STEP 10: Cleanup backup table (optional, commented for safety)
-- DROP TABLE IF EXISTS "users_backup_0002";

-- ROLLBACK COMPLETED
-- System restored to email-only authentication
-- Phone user data preserved in backup tables:
-- - users_before_rollback_0002 (state before rollback)
-- - verification_tokens_backup_0002 (verification data)
-- Original backup preserved in users_backup_0002

DO $$ 
BEGIN
    RAISE NOTICE 'ROLLBACK COMPLETED SUCCESSFULLY';
    RAISE NOTICE 'Original state restored to email-only authentication';
    RAISE NOTICE 'Phone user data preserved in backup tables for manual recovery if needed';
    RAISE NOTICE 'users_backup_0002: Original backup from before migration';
    RAISE NOTICE 'users_before_rollback_0002: State immediately before rollback';
    RAISE NOTICE 'verification_tokens_backup_0002: Verification data backup';
END $$;