# 🔧 Contributing to Lolita Fashion Shopping

## 🚨 CRITICAL: Workspace Naming Conventions

**⚠️ NAMESPACE CONSISTENCY IS MANDATORY**

### ✅ CORRECT Usage:
```typescript
// ✅ Use @lolita-fashion/* for ALL internal packages
import { db, users } from "@lolita-fashion/db";
import { formatDate } from "@lolita-fashion/shared";
```

### ❌ WRONG Usage:
```typescript
// ❌ NEVER use @yuyu/* - this will break the build!
import { db, users } from "@yuyu/db";
import { formatDate } from "@yuyu/shared";
```

## 🛡️ Pre-Development Checklist

Before making ANY changes:

1. **📦 Install dependencies with locking:**
   ```bash
   bun install --frozen-lockfile
   ```

2. **🔍 Run quality checks:**
   ```bash
   bun run validate  # Runs linting, type-check, and build
   ```

3. **🧪 Test your changes:**
   ```bash
   bun run dev       # Test development mode
   bun run build     # Test production build
   ```

## 🚀 Development Workflow

### 1. Code Changes
- ✅ Use TypeScript strictly (no `any` types)
- ✅ Handle null/undefined values properly
- ✅ Use proper error handling with try/catch
- ✅ Follow the existing code patterns

### 2. CSS/Styling
- ❌ **NEVER use `@apply` directives in Svelte `<style>` blocks**
- ✅ Use Tailwind classes directly in HTML: `class="w-full px-3 py-2"`
- ✅ Use proper CSS for complex styling needs

### 3. Database Schema
- ✅ Always generate migrations: `bun run db:generate`
- ✅ Test migrations on fresh DB: `bun run db:setup`
- ❌ **NEVER edit migration files manually**

### 4. Import Organization
```typescript
// ✅ CORRECT order:
import { Elysia } from "elysia";                    // External packages
import { db, users } from "@lolita-fashion/db";    // Internal packages
import { validateUser } from "../utils/validation"; // Relative imports
```

## 🔧 Available Scripts

### Development
```bash
bun run dev          # Start development servers
bun run type-check   # TypeScript validation
bun run lint         # Code linting with auto-fix
bun run format       # Code formatting
```

### Production
```bash
bun run build        # Production build
bun run validate     # Full validation (lint + types + build)
```

### Database
```bash
bun run db:generate  # Generate new migration
bun run db:setup     # Fresh database setup
bun run emergency:db # Emergency database recovery
```

## 🛡️ Error Prevention Rules

### TypeScript Errors
- ✅ **Always handle nullable values:**
  ```typescript
  // ✅ CORRECT
  const userId = store?.user?.id;
  const email = user.email || user.phone || user.id;
  
  // ❌ WRONG
  const userId = store.user.id;  // Can be null
  ```

### Import Errors
- ✅ **Check package names in import statements**
- ✅ **Use absolute paths for internal packages**
- ✅ **Prefer workspace references over relative paths for packages**

### Build Errors
- ✅ **Test both development and production builds**
- ✅ **Ensure all static assets exist**
- ✅ **Validate environment variables**

## 🚨 Emergency Procedures

### Build Failing?
1. Check namespace consistency: `grep -r "@yuyu/" apps/ packages/`
2. Validate TypeScript: `bun run type-check`
3. Check missing dependencies: `bun install`

### Database Issues?
1. Run recovery: `bun run emergency:db`
2. Fresh setup: `bun run db:setup`
3. Check connection: Review `.env` DATABASE_URL

### Import Errors?
1. Verify package names in imports
2. Check workspace dependencies in `package.json`
3. Rebuild packages: `cd packages/shared && bun run build`

## 📚 Architecture Overview

```
lolita-fashion/
├── apps/
│   ├── api/          # Backend (Elysia + PostgreSQL)
│   └── web/          # Frontend (SvelteKit)  
├── packages/
│   ├── db/           # Database schema (@lolita-fashion/db)
│   └── shared/       # Shared utilities (@lolita-fashion/shared)
└── scripts/          # Windows-specific automation
```

## 🎯 Quality Standards

### Code Quality
- **Type Safety**: 100% TypeScript coverage
- **Error Handling**: Proper try/catch everywhere
- **Null Safety**: No undefined/null runtime errors
- **Import Consistency**: Single namespace standard

### Build Quality  
- **Zero Warnings**: Clean production builds
- **Asset Optimization**: All images/patterns exist
- **Bundle Size**: Monitor and optimize
- **Cross-Platform**: Works on Windows + Linux development

## 🏆 Success Metrics

When your PR is ready, it should pass:

✅ **Namespace Check**: No @yuyu imports  
✅ **Type Check**: Zero TypeScript errors  
✅ **Lint Check**: ESLint passes without warnings  
✅ **Build Check**: Production builds successful  
✅ **Format Check**: Code properly formatted  

---

**Remember: Following these guidelines prevents the critical issues we've fixed and ensures a stable, maintainable codebase! 🎉**