const fs = require('fs');
const postgres = require('postgres');

// Try different connection methods
const connectionOptions = {
  host: 'localhost',
  port: 5432,
  database: 'yuyu_lolita',
  username: 'postgres',
};

const sql = postgres(connectionOptions);

async function runMigration() {
  try {
    console.log('🔗 Connecting to database...');
    
    // Test connection
    await sql`SELECT NOW()`;
    console.log('✅ Database connected successfully');
    
    // Read migration file
    console.log('📖 Reading consolidated migration file...');
    const migrationContent = fs.readFileSync('./migrations/0000_consolidated_schema.sql', 'utf8');
    console.log('✅ Consolidated migration file loaded (', migrationContent.length, 'bytes)');
    
    // Apply migration
    console.log('🚀 Applying migration...');
    await sql.unsafe(migrationContent);
    console.log('✅ Migration applied successfully');
    
    // Verify critical table exists
    const result = await sql`SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'overall_verification_status'`;
    if (result.length > 0) {
      console.log('✅ Critical column "overall_verification_status" verified');
    } else {
      console.log('⚠️  Column "overall_verification_status" not found - checking if migration completed');
    }
    
    console.log('🎉 Database migration completed successfully!');
    
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    console.error('Full error:', error);
    process.exit(1);
  } finally {
    await sql.end();
  }
}

runMigration();