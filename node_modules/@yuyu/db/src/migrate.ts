import { migrate } from 'drizzle-orm/postgres-js/migrator';
import { drizzle } from 'drizzle-orm/postgres-js';
import { migrationClient } from './connection';

async function runMigrations() {
  console.log('🔄 Running database migrations...');
  
  try {
    const db = drizzle(migrationClient);
    await migrate(db, { migrationsFolder: './migrations' });
    console.log('✅ Migrations completed successfully');
  } catch (error) {
    console.error('❌ Migration failed:', error);
    process.exit(1);
  } finally {
    await migrationClient.end();
  }
}

if (import.meta.main) {
  runMigrations();
}