-- ==================================================================
-- MySQL User Setup for YuYu Lolita Shopping System
-- Security-focused database user creation script
-- ==================================================================

-- This script creates a dedicated application user instead of using root
-- Run this as MySQL root user or administrator

-- ==================================================================
-- DROP EXISTING USER (if exists)
-- ==================================================================

-- Drop user if exists (MySQL 5.7+ syntax)
DROP USER IF EXISTS 'yuyu_app'@'localhost';
DROP USER IF EXISTS 'yuyu_app'@'%';

-- ==================================================================
-- CREATE APPLICATION DATABASE USER
-- ==================================================================

-- Create dedicated application user with strong password
-- Replace 'CHANGE_THIS_PASSWORD' with a secure password
CREATE USER 'yuyu_app'@'localhost' IDENTIFIED BY 'CHANGE_THIS_PASSWORD';

-- Optional: Allow connections from any host (less secure, use only if needed)
-- CREATE USER 'yuyu_app'@'%' IDENTIFIED BY 'CHANGE_THIS_PASSWORD';

-- ==================================================================
-- GRANT MINIMUM REQUIRED PRIVILEGES
-- ==================================================================

-- Database-level privileges for yuyu_lolita database
GRANT SELECT, INSERT, UPDATE, DELETE ON yuyu_lolita.* TO 'yuyu_app'@'localhost';

-- Schema modification privileges (needed for migrations)
GRANT CREATE, ALTER, INDEX, DROP ON yuyu_lolita.* TO 'yuyu_app'@'localhost';

-- Stored procedure and function privileges (if needed in future)
GRANT EXECUTE ON yuyu_lolita.* TO 'yuyu_app'@'localhost';

-- Grant database creation privilege (needed for initial setup)
GRANT CREATE ON *.* TO 'yuyu_app'@'localhost';

-- Lock tables privilege (needed for backups and some operations)
GRANT LOCK TABLES ON yuyu_lolita.* TO 'yuyu_app'@'localhost';

-- ==================================================================
-- APPLY PRIVILEGE CHANGES
-- ==================================================================

FLUSH PRIVILEGES;

-- ==================================================================
-- VERIFY USER CREATION
-- ==================================================================

-- Show created user
SELECT User, Host, plugin, authentication_string 
FROM mysql.user 
WHERE User = 'yuyu_app';

-- Show granted privileges
SHOW GRANTS FOR 'yuyu_app'@'localhost';

-- ==================================================================
-- USAGE INSTRUCTIONS
-- ==================================================================

/*

1. BEFORE RUNNING THIS SCRIPT:
   - Connect to MySQL as root or administrator
   - Replace 'CHANGE_THIS_PASSWORD' with a secure password
   - Consider your security requirements for host access

2. TO RUN THIS SCRIPT:
   mysql -u root -p < setup-mysql-user.sql

3. AFTER RUNNING THIS SCRIPT:
   - Update your .env file with new credentials:
     DB_USER=yuyu_app
     DB_PASSWORD=your_secure_password_here
   - Test the connection before deploying

4. SECURITY BEST PRACTICES:
   - Use a strong password (at least 16 characters)
   - Mix uppercase, lowercase, numbers, and symbols
   - Never use the same password across environments
   - Regularly rotate passwords
   - Monitor database access logs

5. TROUBLESHOOTING:
   - If connection fails: Check user exists and password is correct
   - If permission denied: Verify grants were applied correctly
   - If host issues: Consider '%' for remote connections (less secure)

6. PRODUCTION CONSIDERATIONS:
   - Create separate users for different environments
   - Use SSL/TLS for database connections
   - Enable MySQL audit logging
   - Implement connection limits per user
   - Regular security audits

*/

-- ==================================================================
-- SAMPLE PRODUCTION SETUP (uncomment and modify as needed)
-- ==================================================================

/*

-- Production user with connection limits
CREATE USER 'yuyu_prod'@'localhost' 
IDENTIFIED BY 'super_secure_production_password_here'
WITH MAX_CONNECTIONS_PER_HOUR 1000
     MAX_UPDATES_PER_HOUR 500
     MAX_USER_CONNECTIONS 10;

-- Staging user
CREATE USER 'yuyu_staging'@'localhost' 
IDENTIFIED BY 'secure_staging_password_here';

-- Development user (more permissive)
CREATE USER 'yuyu_dev'@'localhost' 
IDENTIFIED BY 'dev_password_here';

-- Apply same grants to additional users
GRANT SELECT, INSERT, UPDATE, DELETE ON yuyu_lolita.* TO 'yuyu_prod'@'localhost';
GRANT CREATE, ALTER, INDEX, DROP ON yuyu_lolita.* TO 'yuyu_prod'@'localhost';

FLUSH PRIVILEGES;

*/

-- ==================================================================
-- END OF SCRIPT
-- ==================================================================