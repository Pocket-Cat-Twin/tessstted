# 🗄️ Database Setup Guide

**YuYu Lolita Shopping System - MySQL8 Configuration**

This comprehensive guide covers database setup, security, and troubleshooting for the YuYu Lolita Shopping System.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Database User Setup](#database-user-setup)
5. [Database Initialization](#database-initialization)
6. [Testing & Validation](#testing--validation)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)
9. [Production Considerations](#production-considerations)

## 🚀 Quick Start

For experienced users, here's the minimal setup:

```bash
# 1. Copy environment template
Copy-Item .env.example .env

# 2. Configure database credentials in .env file
# Edit DB_PASSWORD and other settings

# 3. Create MySQL user (optional, recommended)
mysql -u root -p < scripts/setup-mysql-user.sql

# 4. Run complete database setup
npm run db:setup:full:windows
```

## 📋 Prerequisites

### Required Software

- **MySQL 8.0+** - Database server
- **Node.js 18+** - Runtime environment
- **Bun 1.0+** - Package manager and runtime
- **PowerShell 5.1+** - For Windows automation scripts

### MySQL Installation

Download MySQL 8.0 from [MySQL Downloads](https://dev.mysql.com/downloads/mysql/)

**Important**: During installation, remember your root password - you'll need it for setup.

### Verify Installation

```bash
# Check MySQL service
Get-Service MySQL80

# Test MySQL client
mysql --version

# Test Bun
bun --version
```

## ⚙️ Environment Configuration

### Step 1: Create Environment File

```bash
# Copy the example template
Copy-Item .env.example .env
```

### Step 2: Configure Database Settings

Edit `.env` file with your MySQL configuration:

```env
# MySQL8 Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=yuyu_lolita
DB_USER=root                    # Change to dedicated user in production
DB_PASSWORD=your_secure_password_here

# Additional MySQL settings
DB_CONNECTION_LIMIT=10
DB_WAIT_FOR_CONNECTIONS=true
DB_QUEUE_LIMIT=0
DB_CHARSET=utf8mb4
```

### Step 3: Validate Configuration

```bash
# Test environment configuration
npm run db:check:windows

# Test with auto-fix (creates .env from template if missing)
npm run db:check:fix:windows
```

## 👤 Database User Setup

### Option 1: Automated Setup (Recommended)

Use our PowerShell script to create a secure database user:

```bash
# Run interactive user setup
powershell -ExecutionPolicy Bypass -File scripts/setup-mysql-user-windows.ps1

# Or with parameters
powershell -ExecutionPolicy Bypass -File scripts/setup-mysql-user-windows.ps1 -GeneratePassword -NewUserName yuyu_app
```

### Option 2: Manual Setup

Run the SQL script directly:

```bash
# Edit the password in the script first
mysql -u root -p < scripts/setup-mysql-user.sql
```

### Option 3: Manual Commands

Connect to MySQL as root and run:

```sql
-- Create application user
CREATE USER 'yuyu_app'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant required permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON yuyu_lolita.* TO 'yuyu_app'@'localhost';
GRANT CREATE, ALTER, INDEX, DROP ON yuyu_lolita.* TO 'yuyu_app'@'localhost';
GRANT EXECUTE ON yuyu_lolita.* TO 'yuyu_app'@'localhost';
GRANT CREATE ON *.* TO 'yuyu_app'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;
```

**Update your .env file** with the new credentials:

```env
DB_USER=yuyu_app
DB_PASSWORD=your_secure_password
```

## 🛢️ Database Initialization

### Complete Setup (Recommended)

This runs all setup phases automatically:

```bash
npm run db:setup:full:windows
```

**What this does:**
1. ✅ Validates environment configuration
2. ✅ Checks MySQL service status
3. ✅ Creates database schema
4. ✅ Sets up database tables
5. ✅ Creates initial admin and test users
6. ✅ Runs health checks

### Step-by-Step Setup

If you prefer manual control:

```bash
# 1. Environment validation
npm run db:check:windows

# 2. Database migration (creates database and tables)
npm run db:migrate:windows

# 3. User seeding (creates admin and test users)
npm run db:seed:windows

# 4. Health check
npm run db:health:mysql
```

### Individual Operations

```bash
# Create database and tables only
npm run db:migrate:windows

# Create users only (requires existing database)
npm run db:seed:windows

# Test database connectivity
npm run db:health:mysql

# Test connection configuration
cd packages/db && bun run src/config.ts
```

## 🧪 Testing & Validation

### Health Check

```bash
# Comprehensive health check
npm run db:health:mysql
```

**Expected output:**
```
[HEALTHY] MySQL8 database is healthy and responsive
Database: yuyu_lolita
Version: 8.0.x
Uptime: xxx seconds
Connections: x/xxx (xxx idle)
```

### Connection Test

```bash
# Test raw connection
cd packages/db && bun run src/connection.ts

# Test configuration loading
cd packages/db && bun run src/config.ts
```

### PowerShell Validation

```bash
# Validate all PowerShell scripts
npm run test:powershell:integration

# Test environment specifically  
npm run test:powershell:environment

# Full enterprise validation
npm run validate:enterprise:full
```

## 🔧 Troubleshooting

### Common Issues

#### 1. "Access denied for user 'root'@'localhost'"

**Cause**: Incorrect MySQL password or user doesn't exist

**Solutions**:
```bash
# Check MySQL root password
mysql -u root -p

# Reset MySQL root password (if needed)
mysqld --skip-grant-tables
```

**Fix in .env**:
```env
DB_PASSWORD=your_correct_mysql_password
```

#### 2. "Database connection not initialized"

**Cause**: Environment variables not loaded properly

**Solutions**:
- Verify `.env` file exists in project root
- Check all required variables are set in `.env`
- Run environment validation: `npm run db:check:windows`

#### 3. "MySQL service not found"

**Cause**: MySQL not installed or service not started

**Solutions**:
```bash
# Check MySQL service
Get-Service MySQL*

# Start MySQL service
Start-Service MySQL80

# Enable auto-start
Set-Service MySQL80 -StartupType Automatic
```

#### 4. "Port 3306 already in use"

**Cause**: Another MySQL instance or service using port 3306

**Solutions**:
```bash
# Check what's using port 3306
netstat -an | findstr 3306

# Change port in .env file
DB_PORT=3307
```

#### 5. "Database 'yuyu_lolita' doesn't exist"

**Cause**: Database not created yet

**Solutions**:
```bash
# Run migration to create database
npm run db:migrate:windows

# Or create manually
mysql -u root -p -e "CREATE DATABASE yuyu_lolita CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Advanced Troubleshooting

#### Enable Debug Logging

Set environment variable for detailed logging:
```env
DEBUG=true
```

#### Check MySQL Configuration

```bash
# Check MySQL configuration
mysql -u root -p -e "SHOW VARIABLES LIKE 'port';"
mysql -u root -p -e "SHOW VARIABLES LIKE 'bind_address';"

# Check MySQL process list
mysql -u root -p -e "SHOW PROCESSLIST;"

# Check MySQL error log
# Location varies by installation
```

#### Network Issues

```bash
# Test network connectivity to MySQL
Test-NetConnection localhost -Port 3306

# Check firewall settings
Get-NetFirewallRule -DisplayName "*MySQL*"
```

## 🔒 Security Best Practices

### Database User Security

✅ **DO**:
- Create dedicated application users (not root)
- Use strong, unique passwords (12+ characters)
- Grant minimum required permissions only
- Use different users for different environments
- Regularly rotate passwords
- Monitor database access logs

❌ **DON'T**:
- Use root user in production
- Use weak passwords like "password" or "123456"
- Grant unnecessary permissions
- Share credentials across environments
- Log passwords in plain text
- Use default/empty passwords

### Password Requirements

**Minimum requirements**:
- At least 8 characters (12+ recommended)
- Mix of uppercase and lowercase letters
- At least one number
- At least one special character
- Not a common dictionary word

**Generate secure password**:
```bash
# Using PowerShell
Add-Type -AssemblyName System.Web
[System.Web.Security.Membership]::GeneratePassword(16, 4)
```

### Environment Security

- Never commit `.env` files to version control
- Use different `.env` files for each environment
- Secure `.env` file permissions (read-only for app user)
- Use environment-specific database names
- Enable MySQL SSL/TLS for remote connections

## 🏭 Production Considerations

### User Setup

Create environment-specific users:

```sql
-- Production user with limits
CREATE USER 'yuyu_prod'@'localhost' 
IDENTIFIED BY 'super_secure_production_password'
WITH MAX_CONNECTIONS_PER_HOUR 1000
     MAX_UPDATES_PER_HOUR 500
     MAX_USER_CONNECTIONS 10;

-- Staging user
CREATE USER 'yuyu_staging'@'localhost' 
IDENTIFIED BY 'secure_staging_password';

-- Development user  
CREATE USER 'yuyu_dev'@'localhost' 
IDENTIFIED BY 'dev_password';
```

### Configuration

**Production .env example**:
```env
# Production Database Configuration
DB_HOST=db.yourdomain.com
DB_PORT=3306
DB_NAME=yuyu_lolita_prod
DB_USER=yuyu_prod
DB_PASSWORD=super_secure_production_password_here

# Production connection settings
DB_CONNECTION_LIMIT=20
DB_WAIT_FOR_CONNECTIONS=true
DB_QUEUE_LIMIT=10

# Security
NODE_ENV=production
DEBUG=false
```

### Monitoring

Set up monitoring for:
- Database connection pool usage
- Query performance
- Error rates
- User connection patterns
- Failed authentication attempts

### Backup Strategy

```bash
# Full database backup
mysqldump -u yuyu_prod -p yuyu_lolita_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script (daily)
# Add to Windows Task Scheduler
```

### SSL/TLS Configuration

For remote database connections:

```env
# Add to .env for SSL connections
DB_SSL=true
DB_SSL_CERT_PATH=/path/to/client-cert.pem
DB_SSL_KEY_PATH=/path/to/client-key.pem
DB_SSL_CA_PATH=/path/to/ca-cert.pem
```

## 📞 Support

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting](#troubleshooting) section
2. Run diagnostic command: `npm run db:check:windows`
3. Enable debug logging and retry
4. Check MySQL error logs
5. Consult [CLAUDE.md](./CLAUDE.md) for technical implementation details

---

**Happy coding! 🎉**

*Last updated: August 2025*