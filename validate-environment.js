#!/usr/bin/env node

/**
 * Environment Validation Script
 * Senior-level validation system to prevent future database initialization issues
 * Validates environment, database configuration, and system readiness
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🔍 Environment Validation System');
console.log('================================');

// Configuration
const requiredEnvVars = [
  'DATABASE_URL',
  'API_PORT', 
  'NODE_ENV'
];

const optionalEnvVars = [
  'JWT_SECRET',
  'CORS_ORIGIN',
  'SKIP_SEED'
];

// Validation functions
function validateEnvironmentFile() {
  console.log('📋 Validating .env configuration...');
  
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) {
    console.error('   ❌ .env file not found');
    return false;
  }
  
  const envContent = fs.readFileSync(envPath, 'utf8');
  const issues = [];
  
  // Check required variables
  for (const varName of requiredEnvVars) {
    const regex = new RegExp(`^${varName}=(.+)`, 'm');
    const match = envContent.match(regex);
    
    if (!match) {
      issues.push(`Missing required variable: ${varName}`);
    } else if (match[1].trim() === '') {
      issues.push(`Empty value for required variable: ${varName}`);
    } else {
      console.log(`   ✅ ${varName}: ${varName === 'DATABASE_URL' ? match[1].replace(/\/\/[^@]+@/, '//***:***@') : match[1]}`);
    }
  }
  
  // Validate DATABASE_URL format
  const dbUrlMatch = envContent.match(/^DATABASE_URL=(.+)/m);
  if (dbUrlMatch) {
    const dbUrl = dbUrlMatch[1].trim();
    if (!dbUrl.startsWith('postgresql://')) {
      issues.push('DATABASE_URL must start with postgresql://');
    }
    
    try {
      const url = new URL(dbUrl);
      if (!url.hostname) issues.push('DATABASE_URL missing hostname');
      if (!url.port && !url.hostname.includes('localhost')) issues.push('DATABASE_URL missing port');
      if (!url.pathname || url.pathname === '/') issues.push('DATABASE_URL missing database name');
    } catch (e) {
      issues.push('DATABASE_URL has invalid format');
    }
  }
  
  if (issues.length > 0) {
    console.error('   ❌ Environment issues found:');
    issues.forEach(issue => console.error(`      • ${issue}`));
    return false;
  }
  
  console.log('   ✅ Environment configuration is valid');
  return true;
}

function validatePostgreSQL() {
  console.log('🐘 Validating PostgreSQL setup...');
  
  try {
    // Check if PostgreSQL is listening
    const netstatResult = execSync('netstat -tlnp 2>/dev/null | grep :5432 || ss -tlnp | grep :5432', 
      { encoding: 'utf8', timeout: 5000 });
    
    if (netstatResult.includes(':5432')) {
      console.log('   ✅ PostgreSQL is listening on port 5432');
    } else {
      console.error('   ❌ PostgreSQL not listening on port 5432');
      return false;
    }
  } catch (e) {
    console.error('   ❌ Could not check PostgreSQL status');
    return false;
  }
  
  return true;
}

function validateDatabaseConnection() {
  console.log('🔗 Validating database connection...');
  
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) {
    console.error('   ❌ Cannot test connection without .env file');
    return false;
  }
  
  const envContent = fs.readFileSync(envPath, 'utf8');
  const dbUrlMatch = envContent.match(/^DATABASE_URL=(.+)/m);
  
  if (!dbUrlMatch) {
    console.error('   ❌ DATABASE_URL not found in .env');
    return false;
  }
  
  const dbUrl = dbUrlMatch[1].trim();
  
  try {
    // Test basic connection
    const result = execSync(`psql "${dbUrl}" -c "SELECT current_database(), current_user;" -t`, 
      { encoding: 'utf8', timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'] });
    
    console.log(`   ✅ Database connection successful`);
    console.log(`   📊 Result: ${result.trim()}`);
    return true;
  } catch (e) {
    console.error('   ❌ Database connection failed');
    console.error(`   🔧 Error: ${e.message.split('\n')[0]}`);
    return false;
  }
}

function validateDatabaseSchema() {
  console.log('📊 Validating database schema...');
  
  const envPath = path.join(__dirname, '.env');
  const envContent = fs.readFileSync(envPath, 'utf8');
  const dbUrlMatch = envContent.match(/^DATABASE_URL=(.+)/m);
  
  if (!dbUrlMatch) {
    console.error('   ❌ Cannot validate schema without DATABASE_URL');
    return false;
  }
  
  const dbUrl = dbUrlMatch[1].trim();
  
  try {
    // Check for essential tables
    const tablesResult = execSync(`psql "${dbUrl}" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" -t`, 
      { encoding: 'utf8', timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'] });
    
    const tables = tablesResult.split('\n').filter(line => line.trim()).map(line => line.trim());
    
    const essentialTables = ['users', 'config', 'orders'];
    const missingTables = essentialTables.filter(table => !tables.includes(table));
    
    if (missingTables.length > 0) {
      console.error(`   ⚠️  Missing essential tables: ${missingTables.join(', ')}`);
      console.log(`   📋 Available tables (${tables.length}): ${tables.join(', ')}`);
      return false;
    }
    
    console.log(`   ✅ Schema validation passed (${tables.length} tables found)`);
    console.log(`   📋 Tables: ${tables.join(', ')}`);
    return true;
  } catch (e) {
    console.error('   ❌ Schema validation failed');
    console.error(`   🔧 Error: ${e.message.split('\n')[0]}`);
    return false;
  }
}

function generateReport(results) {
  console.log('\n📋 VALIDATION REPORT');
  console.log('===================');
  
  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  
  console.log(`Overall Status: ${passed}/${total} checks passed`);
  console.log('');
  
  results.forEach(result => {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    console.log(`${status} - ${result.name}`);
    if (result.message) {
      console.log(`      ${result.message}`);
    }
  });
  
  if (passed === total) {
    console.log('\n🎉 All validations passed! System is ready.');
    console.log('');
    console.log('🚀 You can now start the API server:');
    console.log('   • node apps/api/src/index-db.js (if compiled)');
    console.log('   • Or use your preferred development command');
  } else {
    console.log('\n⚠️  Some validations failed. Please address the issues above.');
    console.log('');
    console.log('🔧 Common fixes:');
    console.log('   • Run: node setup-database.js');
    console.log('   • Check PostgreSQL service status');
    console.log('   • Verify .env configuration');
    console.log('   • Ensure database and tables exist');
  }
}

// Main execution
async function main() {
  const results = [];
  
  // Run all validations
  results.push({
    name: 'Environment Configuration',
    passed: validateEnvironmentFile(),
    message: 'Checks .env file and required variables'
  });
  
  results.push({
    name: 'PostgreSQL Service',
    passed: validatePostgreSQL(),
    message: 'Verifies PostgreSQL is running and accessible'
  });
  
  results.push({
    name: 'Database Connection', 
    passed: validateDatabaseConnection(),
    message: 'Tests actual database connectivity'
  });
  
  results.push({
    name: 'Database Schema',
    passed: validateDatabaseSchema(), 
    message: 'Validates essential tables exist'
  });
  
  // Generate report
  generateReport(results);
  
  // Exit with appropriate code
  const allPassed = results.every(r => r.passed);
  process.exit(allPassed ? 0 : 1);
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { validateEnvironmentFile, validatePostgreSQL, validateDatabaseConnection, validateDatabaseSchema };