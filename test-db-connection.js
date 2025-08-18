#!/usr/bin/env node

// Simple test script for database connection
// This will test our enhanced PostgreSQL connection handling

import { testConnection, ensureDatabaseHealth, getHealthReport } from './packages/db/src/index.ts';

console.log('🧪 Testing Enhanced Database Connection System');
console.log('==============================================');

async function runTests() {
  try {
    console.log('\n1️⃣  Testing basic connection...');
    const connected = await testConnection();
    console.log(`   Result: ${connected ? '✅ Connected' : '❌ Failed'}`);
    
    console.log('\n2️⃣  Testing database health system...');
    const healthy = await ensureDatabaseHealth();
    console.log(`   Result: ${healthy ? '✅ Healthy' : '❌ Issues detected'}`);
    
    console.log('\n3️⃣  Generating health report...');
    const report = getHealthReport();
    console.log(report);
    
    console.log('\n🎉 Database testing completed!');
    
  } catch (error) {
    console.error('\n❌ Test failed with error:');
    console.error('Error message:', error.message);
    console.error('Error code:', error.code);
    console.error('Full error:', error);
    
    console.log('\n🔧 This is expected if PostgreSQL is not running.');
    console.log('   Try running: .\scripts\db-doctor.ps1 -Diagnose');
    console.log('   Or: .\scripts\db-doctor.ps1 -Fix');
  }
  
  process.exit(0);
}

runTests();