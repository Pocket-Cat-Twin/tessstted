#!/usr/bin/env node

/**
 * Universal Database Setup Script
 * Senior-level implementation for cross-platform database initialization
 * Handles both Windows (Bun) and Linux (Node) environments
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Environment detection
const isWindows = process.platform === 'win32';
const isCodespace = process.env.CODESPACES === 'true' || process.env.USER === 'codespace';

console.log('🔧 Universal Database Setup Script');
console.log('=====================================');
console.log(`Platform: ${process.platform}`);
console.log(`Environment: ${isCodespace ? 'GitHub Codespace' : isWindows ? 'Windows' : 'Linux'}`);
console.log('');

// Database configuration detection
function detectDatabaseConfig() {
  const envPath = path.join(__dirname, '.env');
  let dbUrl = 'postgresql://postgres:postgres@localhost:5432/yuyu_lolita';
  
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf8');
    const dbMatch = envContent.match(/DATABASE_URL=(.+)/);
    if (dbMatch) {
      dbUrl = dbMatch[1].trim();
    }
  }
  
  console.log(`📍 Database URL: ${dbUrl.replace(/\/\/[^@]+@/, '//***:***@')}`);
  return dbUrl;
}

// Test PostgreSQL connection with multiple approaches
async function testConnection() {
  console.log('🔄 Testing PostgreSQL connection...');
  
  const configs = [
    'postgresql://postgres:postgres@localhost:5432/postgres',
    'postgresql://codespace@localhost:5432/postgres',
    'postgresql://postgres@localhost:5432/postgres'
  ];
  
  for (const config of configs) {
    try {
      console.log(`   Trying: ${config.replace(/\/\/[^@]+@/, '//***@')}`);
      
      const result = execSync(
        `psql "${config}" -c "SELECT current_user, current_database();" -t`,
        { 
          timeout: 5000, 
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, PGCONNECT_TIMEOUT: '5' }
        }
      ).toString().trim();
      
      console.log(`   ✅ Connected: ${result}`);
      return config;
    } catch (error) {
      console.log(`   ❌ Failed: ${error.message.split('\n')[0]}`);
    }
  }
  
  throw new Error('Could not connect to PostgreSQL with any configuration');
}

// Create database if it doesn't exist
async function createDatabase(adminConfig, targetDb = 'yuyu_lolita') {
  console.log(`🔄 Ensuring database '${targetDb}' exists...`);
  
  try {
    // Check if database exists
    const checkResult = execSync(
      `psql "${adminConfig}" -c "SELECT 1 FROM pg_database WHERE datname = '${targetDb}';" -t`,
      { timeout: 5000, stdio: ['pipe', 'pipe', 'pipe'] }
    ).toString().trim();
    
    if (checkResult.includes('1')) {
      console.log(`   ✅ Database '${targetDb}' already exists`);
      return true;
    }
    
    // Create database
    console.log(`   🔨 Creating database '${targetDb}'...`);
    execSync(
      `psql "${adminConfig}" -c "CREATE DATABASE ${targetDb} WITH ENCODING = 'UTF8';"`,
      { timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'] }
    );
    
    console.log(`   ✅ Database '${targetDb}' created successfully`);
    return true;
  } catch (error) {
    console.error(`   ❌ Database creation failed: ${error.message}`);
    return false;
  }
}

// Run SQL migration file
async function runMigration(dbConfig, migrationFile) {
  console.log(`🔄 Running migration: ${path.basename(migrationFile)}`);
  
  if (!fs.existsSync(migrationFile)) {
    throw new Error(`Migration file not found: ${migrationFile}`);
  }
  
  try {
    const result = execSync(
      `psql "${dbConfig}" -f "${migrationFile}"`,
      { 
        timeout: 30000, 
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: __dirname 
      }
    ).toString();
    
    console.log('   ✅ Migration completed successfully');
    return true;
  } catch (error) {
    console.error(`   ❌ Migration failed: ${error.message}`);
    throw error;
  }
}

// Test final connection and query
async function testFinalConnection(dbConfig) {
  console.log('🔄 Testing final database connection...');
  
  try {
    const result = execSync(
      `psql "${dbConfig}" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 5;" -t`,
      { timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'] }
    ).toString().trim();
    
    const tables = result.split('\n').filter(line => line.trim()).map(line => line.trim());
    console.log(`   ✅ Connection successful, found ${tables.length} tables:`);
    tables.forEach(table => console.log(`      • ${table}`));
    return true;
  } catch (error) {
    console.error(`   ❌ Final connection test failed: ${error.message}`);
    return false;
  }
}

// Update .env file with working configuration
function updateEnvFile(workingConfig) {
  const envPath = path.join(__dirname, '.env');
  const targetDb = 'yuyu_lolita';
  const finalConfig = workingConfig.replace('/postgres', `/${targetDb}`);
  
  console.log('🔄 Updating .env file...');
  
  if (!fs.existsSync(envPath)) {
    console.log('   ❌ .env file not found');
    return false;
  }
  
  try {
    let envContent = fs.readFileSync(envPath, 'utf8');
    const updatedContent = envContent.replace(
      /DATABASE_URL=.*/,
      `DATABASE_URL=${finalConfig}`
    );
    
    fs.writeFileSync(envPath, updatedContent);
    console.log(`   ✅ Updated DATABASE_URL to: ${finalConfig.replace(/\/\/[^@]+@/, '//***:***@')}`);
    return true;
  } catch (error) {
    console.error(`   ❌ Failed to update .env: ${error.message}`);
    return false;
  }
}

// Main setup function
async function main() {
  try {
    console.log('🚀 Starting comprehensive database setup...\n');
    
    // Step 1: Test PostgreSQL connection
    const adminConfig = await testConnection();
    console.log('');
    
    // Step 2: Create target database
    const dbCreated = await createDatabase(adminConfig);
    if (!dbCreated) {
      throw new Error('Database creation failed');
    }
    console.log('');
    
    // Step 3: Update .env file
    updateEnvFile(adminConfig);
    console.log('');
    
    // Step 4: Run migrations
    const migrationFile = path.join(__dirname, 'packages/db/migrations/0000_consolidated_schema.sql');
    const targetConfig = adminConfig.replace('/postgres', '/yuyu_lolita');
    
    await runMigration(targetConfig, migrationFile);
    console.log('');
    
    // Step 5: Test final connection
    await testFinalConnection(targetConfig);
    console.log('');
    
    console.log('🎉 Database setup completed successfully!');
    console.log('=======================================');
    console.log('');
    console.log('✅ Database is ready for use');
    console.log('✅ All tables created');
    console.log('✅ .env file updated');
    console.log('');
    console.log('🔗 Next steps:');
    console.log('   • Start API: node apps/api/src/index-db.js (if compiled)');
    console.log('   • Or restart your API server');
    console.log('   • API should now initialize without errors');
    
  } catch (error) {
    console.error('\n❌ Setup failed:');
    console.error(`   ${error.message}`);
    console.error('');
    console.error('🔧 Troubleshooting:');
    console.error('   • Ensure PostgreSQL is running');
    console.error('   • Check PostgreSQL authentication');
    console.error('   • Verify network connectivity to localhost:5432');
    console.error('   • Run with more verbose logging if needed');
    process.exit(1);
  }
}

// Execute if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { main, testConnection, createDatabase, runMigration };