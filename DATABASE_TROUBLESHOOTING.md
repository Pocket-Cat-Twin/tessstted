# Database Troubleshooting Guide

## Common Issues and Solutions

### 1. Column Does Not Exist Errors

**Symptoms:** `PostgresError: column "field_name" does not exist`

**Root Causes:**
- Schema in code doesn't match real database structure
- Missing or unapplied migrations
- Outdated backup/restore of database

**Resolution Steps:**
1. Check real table structure: `\d table_name` in psql
2. Compare with schema definitions in `packages/db/src/schema/`
3. Fix schema to match database OR create migration
4. Verify all relations and indexes match

### 2. Database Connection Issues

**Symptoms:** `password authentication failed` or connection refused

**Resolution:**
1. Check PostgreSQL is running: `ps aux | grep postgres`
2. Verify correct port in `.env` (project uses 5433, not 5432)
3. Update `pg_hba.conf` for trust authentication locally
4. Restart PostgreSQL after config changes

### 3. Migration/Schema Sync Issues

**Prevention:**
- Always run `\d table_name` to verify actual DB structure
- Keep schema files in sync with real database
- Test seeding after schema changes
- Use proper migration workflow

### 4. Environment Configuration

**Key Settings:**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/yuyu_lolita
DB_HOST=localhost
DB_PORT=5433  # Not 5432!
```

### 5. Quick Health Check

```bash
# Test database connection
psql postgresql://postgres:postgres@localhost:5433/yuyu_lolita -c "SELECT version();"

# Check schema
psql postgresql://postgres:postgres@localhost:5433/yuyu_lolita -c "\d users"

# Test API
curl http://localhost:3001
```

Last updated: 2025-08-20
Resolved issue: registration_method column missing error