// Централизованный модуль для генерации пользователей
// YuYu Lolita Shopping System - Стандартизированное создание пользователей
import * as bcrypt from "bcryptjs";
import { writeFileSync, existsSync, appendFileSync } from "fs";
import { join } from "path";
import { getPool } from "./connection.js";
import { getUserByEmail } from "./query-builders.js";

// Константы для стандартизации
export const USER_GENERATION_CONSTANTS = {
  ADMIN_EMAIL: "admin@yuyulolita.com",
  ADMIN_NAME: "admin",
  ADMIN_FULL_NAME: "Главный Администратор",
  BCRYPT_ROUNDS: 12, // Из config/windows.json
  PASSWORD_LENGTH: 16,
  CREDENTIALS_FILE: "credentials.txt"
} as const;

// Интерфейс для создания пользователя
export interface UserCreationData {
  email: string;
  password: string;
  role: 'admin' | 'user';
  name: string;
  fullName?: string;
  method: 'seeding' | 'api' | 'migration' | 'manual';
}

// Интерфейс для записи в credentials.txt
export interface CredentialsEntry {
  timestamp: string;
  email: string;
  password: string; // НЕШИФРОВАННЫЙ пароль для администратора
  role: string;
  method: string;
  name: string;
}

/**
 * Генерирует безопасный пароль согласно стандартам проекта
 * @param length Длина пароля (по умолчанию 16)
 * @returns Сгенерированный пароль
 */
export function generateSecurePassword(length: number = USER_GENERATION_CONSTANTS.PASSWORD_LENGTH): string {
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
  let password = '';
  
  // Обязательно включаем по одному символу каждого типа
  password += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random() * 26)]; // заглавная
  password += 'abcdefghijklmnopqrstuvwxyz'[Math.floor(Math.random() * 26)]; // строчная
  password += '0123456789'[Math.floor(Math.random() * 10)]; // цифра
  password += '!@#$%^&*'[Math.floor(Math.random() * 8)]; // спецсимвол
  
  // Заполняем остальное случайно
  for (let i = 4; i < length; i++) {
    password += charset[Math.floor(Math.random() * charset.length)];
  }
  
  // Перемешиваем пароль
  return password.split('').sort(() => Math.random() - 0.5).join('');
}

/**
 * Хэширует пароль с использованием bcrypt
 * @param password Нешифрованный пароль
 * @returns Хэшированный пароль
 */
export async function hashPassword(password: string): Promise<string> {
  return await bcrypt.hash(password, USER_GENERATION_CONSTANTS.BCRYPT_ROUNDS);
}

/**
 * Сохраняет учетные данные в credentials.txt
 * @param entry Запись с учетными данными
 */
export function saveCredentials(entry: CredentialsEntry): void {
  const credentialsPath = join(process.cwd(), USER_GENERATION_CONSTANTS.CREDENTIALS_FILE);
  
  // Создаем заголовок файла, если файл не существует
  if (!existsSync(credentialsPath)) {
    const header = "# YuYu Lolita Shopping System - User Credentials\n" +
                   "# ВНИМАНИЕ: Этот файл содержит нешифрованные пароли!\n" +
                   "# Держите его в безопасности и не коммитьте в git\n" +
                   "# Format: TIMESTAMP | EMAIL | PASSWORD | ROLE | METHOD | NAME\n\n";
    writeFileSync(credentialsPath, header, 'utf8');
  }
  
  // Формируем строку записи
  const logEntry = `${entry.timestamp} | ${entry.email} | ${entry.password} | ${entry.role} | ${entry.method} | ${entry.name}\n`;
  
  // Добавляем запись в файл
  appendFileSync(credentialsPath, logEntry, 'utf8');
}

/**
 * Создает пользователя с автоматическим сохранением учетных данных
 * @param userData Данные для создания пользователя
 * @returns Promise<boolean> Успех операции
 */
export async function createUserWithCredentialsSave(userData: UserCreationData): Promise<boolean> {
  const pool = await getPool();
  
  try {
    // Проверяем, существует ли пользователь
    const existing = await getUserByEmail(userData.email);
    if (existing) {
      console.log(`⚠️  Пользователь ${userData.email} уже существует, пропускаем`);
      return false;
    }
    
    // Хэшируем пароль
    const hashedPassword = await hashPassword(userData.password);
    const userName = userData.name || userData.email.split('@')[0] || 'user';
    const userFullName = userData.fullName || userName;
    
    // Создаем пользователя в базе данных
    await pool.execute(`
      INSERT INTO users (
        id, email, password_hash, name, full_name, registration_method, 
        role, status, email_verified, created_at, updated_at
      ) VALUES (UUID(), ?, ?, ?, ?, 'email', ?, 'active', true, NOW(), NOW())
    `, [userData.email, hashedPassword, userName, userFullName, userData.role]);
    
    // Сохраняем учетные данные в credentials.txt
    const credentialsEntry: CredentialsEntry = {
      timestamp: new Date().toISOString(),
      email: userData.email,
      password: userData.password, // НЕШИФРОВАННЫЙ пароль!
      role: userData.role,
      method: userData.method,
      name: userName
    };
    
    saveCredentials(credentialsEntry);
    
    console.log(`✅ Пользователь ${userData.email} создан успешно (роль: ${userData.role})`);
    console.log(`📝 Учетные данные сохранены в ${USER_GENERATION_CONSTANTS.CREDENTIALS_FILE}`);
    
    return true;
    
  } catch (error) {
    console.error(`❌ Ошибка создания пользователя ${userData.email}:`, error);
    throw error;
  }
}

/**
 * Создает администратора с автоматически сгенерированным паролем
 * @param method Метод создания (для логирования)
 * @returns Promise<string> Сгенерированный пароль
 */
export async function createAdminUser(method: UserCreationData['method'] = 'seeding'): Promise<string> {
  const adminPassword = generateSecurePassword();
  
  const success = await createUserWithCredentialsSave({
    email: USER_GENERATION_CONSTANTS.ADMIN_EMAIL,
    password: adminPassword,
    role: 'admin',
    name: USER_GENERATION_CONSTANTS.ADMIN_NAME,
    fullName: USER_GENERATION_CONSTANTS.ADMIN_FULL_NAME,
    method: method
  });
  
  if (!success) {
    throw new Error('Failed to create admin user');
  }
  
  return adminPassword;
}

/**
 * Создает тестового пользователя
 * @param email Email пользователя
 * @param name Имя пользователя
 * @param password Пароль (если не указан, генерируется автоматически)
 * @param method Метод создания
 * @returns Promise<string> Пароль пользователя
 */
export async function createTestUser(
  email: string, 
  name: string, 
  password?: string, 
  method: UserCreationData['method'] = 'seeding'
): Promise<string> {
  const userPassword = password || generateSecurePassword();
  
  const success = await createUserWithCredentialsSave({
    email: email,
    password: userPassword,
    role: 'user',
    name: name,
    fullName: `Тестовый пользователь ${name}`,
    method: method
  });
  
  if (!success) {
    throw new Error(`Failed to create test user ${email}`);
  }
  
  return userPassword;
}

/**
 * Выводит информационное сообщение о сохраненных учетных данных
 */
export function displayCredentialsInfo(): void {
  console.log('');
  console.log('🔐 ========================================');
  console.log('🔐 УЧЕТНЫЕ ДАННЫЕ СОХРАНЕНЫ');
  console.log('🔐 ========================================');
  console.log(`📝 Файл: ${USER_GENERATION_CONSTANTS.CREDENTIALS_FILE}`);
  console.log('🔐 Содержит нешифрованные пароли!');
  console.log('🔒 Держите файл в безопасности');
  console.log('⚠️  НЕ коммитьте его в git');
  console.log('🔐 ========================================');
  console.log('');
}