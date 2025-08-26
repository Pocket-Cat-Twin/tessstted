import app from "./index";

const port = parseInt(process.env.API_PORT || "3001");
const host = process.env.API_HOST || "0.0.0.0";

// Simple HTTP server for Node.js
const server = Bun.serve({
  port,
  hostname: host,
  fetch: app.fetch,
});

console.log(`🚀 YuYu API Server running on http://${host}:${port}`);
console.log(`📚 API Documentation: http://${host}:${port}/swagger`);
console.log(`🐬 Database: MySQL8 Native (No ORM)`);