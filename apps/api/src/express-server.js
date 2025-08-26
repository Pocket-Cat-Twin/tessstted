const express = require('express');
const mysql = require('mysql2/promise');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const cors = require('cors');
require('dotenv').config();

const app = express();
const port = process.env.API_PORT || 3001;

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  credentials: true
}));
app.use(express.json());

// Database connection
const dbConfig = {
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 3306,
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'yuyu_lolita',
  charset: 'utf8mb4'
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    success: true,
    message: 'YuYu Lolita API is running',
    timestamp: new Date().toISOString(),
    database: 'MySQL8'
  });
});

// Register endpoint
app.post('/auth/register', async (req, res) => {
  try {
    const { email, password, name, registrationMethod = 'email' } = req.body;

    if (!email || !password || !name) {
      return res.status(400).json({
        success: false,
        error: 'Email, password and name are required'
      });
    }

    // Create database connection
    const connection = await mysql.createConnection(dbConfig);
    
    // Check if user already exists
    const [existing] = await connection.execute(
      'SELECT id FROM users WHERE email = ?',
      [email]
    );

    if (existing.length > 0) {
      await connection.end();
      return res.status(400).json({
        success: false,
        error: 'User already exists'
      });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);
    
    // Generate UUID for user ID
    const userId = require('crypto').randomUUID();

    // Insert user
    await connection.execute(
      `INSERT INTO users (id, email, password_hash, name, registration_method, role, status, email_verified, created_at, updated_at) 
       VALUES (?, ?, ?, ?, ?, 'user', 'pending', false, NOW(), NOW())`,
      [userId, email, hashedPassword, name, registrationMethod]
    );

    await connection.end();

    // Generate JWT token
    const token = jwt.sign(
      { userId, email, name },
      process.env.JWT_SECRET || 'test-secret',
      { expiresIn: '24h' }
    );

    res.json({
      success: true,
      message: 'User registered successfully',
      data: {
        user: {
          id: userId,
          email,
          name,
          role: 'user',
          status: 'pending',
          emailVerified: false
        },
        token
      }
    });

  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Login endpoint
app.post('/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        success: false,
        error: 'Email and password are required'
      });
    }

    // Create database connection
    const connection = await mysql.createConnection(dbConfig);
    
    // Find user
    const [users] = await connection.execute(
      'SELECT id, email, password_hash, name, role, status, email_verified FROM users WHERE email = ?',
      [email]
    );

    if (users.length === 0) {
      await connection.end();
      return res.status(400).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    const user = users[0];

    // Check password
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    
    if (!isValidPassword) {
      await connection.end();
      return res.status(400).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    await connection.end();

    // Generate JWT token
    const token = jwt.sign(
      { userId: user.id, email: user.email, name: user.name },
      process.env.JWT_SECRET || 'test-secret',
      { expiresIn: '24h' }
    );

    res.json({
      success: true,
      message: 'Login successful',
      data: {
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role,
          status: user.status,
          emailVerified: user.email_verified
        },
        token
      }
    });

  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`🚀 YuYu API Server (Express) running on http://0.0.0.0:${port}`);
  console.log(`🐬 Database: MySQL8 Native`);
  console.log(`📚 Available endpoints:`);
  console.log(`   GET  /health`);
  console.log(`   POST /auth/register`);
  console.log(`   POST /auth/login`);
});