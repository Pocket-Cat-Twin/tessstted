import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

// Create connection
const connectionString = process.env.DATABASE_URL || 'postgresql://postgres:password@localhost:5432/yuyu_lolita';

// For migrations
export const migrationClient = postgres(connectionString, { max: 1 });

// For queries
export const queryClient = postgres(connectionString);
export const db = drizzle(queryClient, { schema });

// Connection helper
export async function testConnection() {
  try {
    await queryClient`SELECT 1`;
    console.log('✅ Database connection successful');
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    return false;
  }
}

// Close connections
export async function closeConnections() {
  await queryClient.end();
  await migrationClient.end();
}

// Export types
export type Database = typeof db;