-- Initial database setup for PostgreSQL
-- This file will be executed when the database container starts

-- Create database if not exists (already handled by Docker environment)

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance (will be created by Drizzle migrations)

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE yuyu_lolita TO yuyu_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO yuyu_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO yuyu_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO yuyu_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO yuyu_user;