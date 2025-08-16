#!/usr/bin/env node

// Smart server startup script with automatic port detection
import { createServer } from 'http';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Default configuration
const DEFAULT_PORT = 5173;
const DEFAULT_HOST = '0.0.0.0';
const FALLBACK_PORTS = [5173, 3000, 4173, 5000, 8000, 8080]; // Removed 3001 (reserved for API)

// Load environment variables
function loadEnv() {
  try {
    const envPath = join(__dirname, '../../.env');
    const envContent = readFileSync(envPath, 'utf8');
    
    envContent.split('\n').forEach(line => {
      const [key, value] = line.split('=');
      if (key && value) {
        process.env[key.trim()] = value.trim();
      }
    });
  } catch (error) {
    console.log('[INFO] No .env file found, using default settings');
  }
}

// Check if port is available
function isPortAvailable(port, host = 'localhost') {
  return new Promise((resolve) => {
    const server = createServer();
    
    server.listen(port, host, () => {
      server.close(() => resolve(true));
    });
    
    server.on('error', () => resolve(false));
  });
}

// Find an available port
async function findAvailablePort(preferredPort, host) {
  console.log(`[PORT] Checking preferred port: ${preferredPort}`);
  
  if (await isPortAvailable(preferredPort, host)) {
    return preferredPort;
  }
  
  console.log(`[PORT] Port ${preferredPort} is busy, searching for alternatives...`);
  
  for (const port of FALLBACK_PORTS) {
    if (port !== preferredPort && await isPortAvailable(port, host)) {
      console.log(`[PORT] Found available port: ${port}`);
      return port;
    }
  }
  
  throw new Error('No available ports found');
}

// Start the application
async function startServer() {
  console.log('[START] YuYu Lolita Web App - Smart Startup');
  console.log('==========================================');
  
  // Load environment variables
  loadEnv();
  
  // Get configuration
  const rawPort = process.env.PORT;
  const rawWebPort = process.env.WEB_PORT;
  let preferredPort = parseInt(rawWebPort || rawPort || DEFAULT_PORT, 10);
  
  // Ensure web app never uses API ports
  const apiPorts = [3001, 3002, 3003];
  if (apiPorts.includes(preferredPort)) {
    console.warn(`⚠️  WARNING: Web app cannot use API port ${preferredPort}. Using default: ${DEFAULT_PORT}`);
    preferredPort = DEFAULT_PORT;
  }
  
  const host = process.env.HOST || DEFAULT_HOST;
  
  console.log(`🔧 Web App Configuration:`);
  console.log(`   NODE_ENV: ${process.env.NODE_ENV || 'production'}`);
  console.log(`   PORT env: ${rawPort || 'undefined'}`);
  console.log(`   WEB_PORT env: ${rawWebPort || 'undefined'}`);
  console.log(`   Preferred port: ${preferredPort}`);
  console.log(`   Host: ${host}`);
  console.log('');
  
  try {
    // Find available port
    const availablePort = await findAvailablePort(preferredPort, host);
    
    // Set the port for the SvelteKit app
    process.env.PORT = availablePort.toString();
    
    console.log(`[SUCCESS] Starting server on port ${availablePort}`);
    console.log(`[INFO] Host: ${host}`);
    console.log(`[INFO] Environment: ${process.env.NODE_ENV || 'production'}`);
    console.log('');
    console.log(`🌐 Web App: http://localhost:${availablePort}`);
    console.log(`🌐 External: http://${host === '0.0.0.0' ? 'YOUR_IP' : host}:${availablePort}`);
    console.log('');
    
    // Import and start the SvelteKit handler
    const { handler } = await import('./build/handler.js');
    const server = createServer(handler);
    
    server.listen(availablePort, host, () => {
      console.log(`[READY] Server is running on http://${host}:${availablePort}`);
    });
    
    // Handle graceful shutdown
    process.on('SIGTERM', () => {
      console.log('[SHUTDOWN] Received SIGTERM, closing server...');
      server.close(() => {
        console.log('[SHUTDOWN] Server closed');
        process.exit(0);
      });
    });
    
    process.on('SIGINT', () => {
      console.log('[SHUTDOWN] Received SIGINT, closing server...');
      server.close(() => {
        console.log('[SHUTDOWN] Server closed');
        process.exit(0);
      });
    });
    
  } catch (error) {
    console.error('[ERROR] Failed to start server:', error.message);
    process.exit(1);
  }
}

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  console.error('[ERROR] Uncaught exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('[ERROR] Unhandled rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Start the server
startServer();