import type { Config } from "drizzle-kit";

// Windows-only Drizzle configuration
// This project is designed exclusively for Windows environments with PostgreSQL on port 5432
export default {
  schema: "./src/schema/index.ts",
  out: "./migrations",
  driver: "pg",
  dbCredentials: {
    connectionString:
      process.env.DATABASE_URL ||
      "postgresql://postgres:postgres@localhost:5432/yuyu_lolita",
  },
  verbose: true,
  strict: true,
} satisfies Config;
