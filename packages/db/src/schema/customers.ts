import { pgTable, uuid, varchar, text, timestamp, boolean } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

// Customers table
export const customers = pgTable('customers', {
  id: uuid('id').defaultRandom().primaryKey(),
  
  // Basic information
  name: varchar('name', { length: 255 }).notNull(),
  fullName: varchar('full_name', { length: 255 }), // ФИО (полное имя)
  
  // Contact information
  email: varchar('email', { length: 255 }),
  phone: varchar('phone', { length: 50 }),
  contactPhone: varchar('contact_phone', { length: 50 }), // Телефон контактный
  
  // Additional profile fields
  notes: text('notes'), // Дополнительная информация о клиенте
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Customer addresses table
export const customerAddresses = pgTable('customer_addresses', {
  id: uuid('id').defaultRandom().primaryKey(),
  customerId: uuid('customer_id').notNull().references(() => customers.id, { onDelete: 'cascade' }),
  
  // Address type (shipping, billing, etc.)
  addressType: varchar('address_type', { length: 50 }).default('shipping').notNull(),
  
  // Address details (as per tech spec requirements)
  fullAddress: text('full_address').notNull(), // Адрес доставки
  city: varchar('city', { length: 100 }).notNull(), // Город доставки
  postalCode: varchar('postal_code', { length: 20 }), // Индекс
  country: varchar('country', { length: 100 }).default('Россия').notNull(),
  
  // Additional address information  
  addressComments: text('address_comments'), // Комментарии к адресу
  
  // Metadata
  isDefault: boolean('is_default').default(false).notNull(),
  
  // Timestamps
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

// Zod schemas for validation
export const insertCustomerSchema = createInsertSchema(customers);
export const selectCustomerSchema = createSelectSchema(customers);
export const insertCustomerAddressSchema = createInsertSchema(customerAddresses);
export const selectCustomerAddressSchema = createSelectSchema(customerAddresses);

// Types
export type Customer = typeof customers.$inferSelect;
export type NewCustomer = typeof customers.$inferInsert;
export type CustomerAddress = typeof customerAddresses.$inferSelect;
export type NewCustomerAddress = typeof customerAddresses.$inferInsert;