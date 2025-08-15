import { pgTable, uuid, varchar, text, timestamp, boolean, pgEnum } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

// User role enum
export const userRoleEnum = pgEnum('user_role', ['user', 'admin']);

// User status enum  
export const userStatusEnum = pgEnum('user_status', ['pending', 'active', 'blocked']);

// Registration method enum
export const registrationMethodEnum = pgEnum('registration_method', ['email', 'phone']);

// Users table
export const users = pgTable('users', {
  id: uuid('id').defaultRandom().primaryKey(),
  
  // Authentication - email OR phone required
  email: varchar('email', { length: 255 }).unique(),
  phone: varchar('phone', { length: 50 }).unique(),
  password: varchar('password', { length: 255 }).notNull(),
  
  // Registration method tracking
  registrationMethod: registrationMethodEnum('registration_method').notNull(),
  
  // User information
  name: varchar('name', { length: 100 }),
  fullName: varchar('full_name', { length: 200 }),
  
  // Contact information (can be updated after registration)
  contactPhone: varchar('contact_phone', { length: 50 }),
  contactEmail: varchar('contact_email', { length: 255 }),
  
  // User role and status
  role: userRoleEnum('role').default('user').notNull(),
  status: userStatusEnum('status').default('pending').notNull(),
  
  // Verification status
  emailVerified: boolean('email_verified').default(false).notNull(),
  phoneVerified: boolean('phone_verified').default(false).notNull(),
  
  // Legacy verification tokens (deprecated - use verification_tokens table)
  emailVerificationToken: varchar('email_verification_token', { length: 255 }),
  passwordResetToken: varchar('password_reset_token', { length: 255 }),
  passwordResetExpires: timestamp('password_reset_expires'),
  
  // Profile
  avatar: text('avatar'),
  
  // Activity tracking
  lastLoginAt: timestamp('last_login_at'),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// User sessions table for authentication
export const userSessions = pgTable('user_sessions', {
  id: varchar('id', { length: 128 }).primaryKey(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  expiresAt: timestamp('expires_at', { withTimezone: true, mode: 'date' }).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// Zod schemas for validation
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
export const insertUserSessionSchema = createInsertSchema(userSessions);
export const selectUserSessionSchema = createSelectSchema(userSessions);

// Types
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type UserSession = typeof userSessions.$inferSelect;
export type NewUserSession = typeof userSessions.$inferInsert;