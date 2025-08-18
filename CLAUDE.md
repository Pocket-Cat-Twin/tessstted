# YuYu Lolita Shopping - Windows Development Guide 🪟

## Project Overview
This is a YuYu Lolita Shopping website built **exclusively for Windows environments** using Bun, PostgreSQL, Svelte, and TypeScript.

**⚠️ IMPORTANT: This project is designed exclusively for Windows 10/11. Other platforms are not supported.**

## Running the Project

### Windows Development (Only Supported Platform)
```powershell
# One-time setup (Windows only)
bun run setup

# Start development (Windows)
bun run dev

# Or start individually:
# Terminal 1 - API Server
cd apps/api && bun run dev:windows

# Terminal 2 - Web App  
cd apps/web && bun run dev

# Production build
bun run build

# Production start
bun run start
```

**🚀 Windows-Exclusive Features:**
- Native PostgreSQL TCP connection on port 5432
- PowerShell automation scripts
- Windows service integration ready
- Advanced Windows error diagnostics
- Windows Firewall configuration support

### Access URLs (Local Development)
**🔗 Local URLs:**
- **🌐 Web App**: http://localhost:5173
- **🚀 API**: http://localhost:3001  
- **📚 API Documentation**: http://localhost:3001/swagger

**For Windows Network Access:**
- Replace `localhost` with your machine's IP address
- Ensure Windows Firewall allows ports 3001 and 5173

### Database Commands (Windows Only)
```powershell
# Windows database setup (one-time)
bun run db:setup

# Generate new migrations
bun run db:generate

# Run migrations
bun run db:migrate

# Seed database
bun run db:seed
```

### Development Commands (Windows)
```powershell
# Lint code
bun run lint

# Type check
bun run type-check

# Format code
bun run format

# Build project
bun run build
```

## Environment Configuration

### Key Environment Variables (.env)
```bash
# API Configuration (Windows Only)
API_HOST=localhost    # TCP connection for Windows
API_PORT=3001
CORS_ORIGIN=http://localhost:5173

# Web App Configuration
WEB_PORT=5173
HOST=0.0.0.0          # Network access
PUBLIC_API_URL=http://localhost:3001

# Note: Generic PORT removed to prevent conflicts

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yuyu_lolita

# Environment
NODE_ENV=development
SKIP_SEED=false
```

### Environment Setup (Windows)
The project includes a pre-configured Windows environment template:
```powershell
# Copy Windows template
copy .env.windows .env
```

## Known Issues & Solutions

### Port Conflict Issues (COMPLETELY SOLVED!)
**Problem**: API server incorrectly using web port 5173 instead of API port 3001
**Root Cause**: Environment variable conflicts between generic `PORT` and specific `API_PORT`/`WEB_PORT`
**Solution**: Comprehensive port management system implemented!

✅ **API Server Fixes:**
- Explicit port validation with fallback protection
- Automatic rejection of web ports (5173, 3000, 4173, etc.)
- Enhanced logging showing all environment variables
- Failsafe defaults to port 3001 for API

✅ **Web App Improvements:**
- Smart port detection with API port avoidance
- Fallback ports exclude API-reserved ports (3001, 3002, 3003)
- Clear environment variable separation

✅ **Environment Configuration:**
- Removed generic `PORT` variable to prevent conflicts
- API uses `API_PORT` exclusively (3001)
- Web uses `WEB_PORT` exclusively (5173)
- Updated all scripts and configurations

✅ **Development & Production:**
- PowerShell scripts updated with explicit port isolation
- Environment variables properly scoped per application
- Source maps added for better debugging and error traces

✅ **Automatic Protection:**
- API server rejects web ports automatically
- Web app avoids API ports automatically
- Clear error messages with suggested fixes

### Database Connection Issues (Windows)
**Problem**: Cannot connect to PostgreSQL
**Solution**: 
1. Ensure PostgreSQL is installed and running: `net start postgresql-x64-15`
2. Verify connection string in .env uses port 5432
3. Run database setup: `bun run db:setup`
4. Check Windows PostgreSQL service status: `sc query postgresql*`

### Windows Firewall Issues
**Problem**: Cannot access from other devices
**Solution**:
1. Add firewall rules for ports 3001 and 5173
2. Or temporarily disable Windows Defender Firewall for testing
3. Use Windows PowerShell as Administrator:
   ```powershell
   netsh advfirewall firewall add rule name="YuYu API" dir=in action=allow protocol=TCP localport=3001
   netsh advfirewall firewall add rule name="YuYu Web" dir=in action=allow protocol=TCP localport=5173
   ```

### PowerShell Execution Policy
**Problem**: Scripts cannot be executed
**Solution**: Set execution policy for current user:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Database Schema Issues
**Problem**: Migration or seeding failures
**Solution**: 
1. Reset database: Drop and recreate `yuyu_lolita` database
2. Run fresh migrations: `bun run db:migrate:windows`
3. Re-seed: `bun run db:seed:windows`

## Project Structure
```
├── apps/
│   ├── api/          # Backend API (Elysia + PostgreSQL)
│   └── web/          # Frontend (SvelteKit)
├── packages/
│   ├── db/           # Database schema and migrations (Drizzle ORM)
│   └── shared/       # Shared utilities
└── .env              # Environment configuration
```

## Tech Stack (Windows-Optimized)
- **Runtime**: Bun (Windows builds)
- **Backend**: Elysia.js + PostgreSQL + Drizzle ORM
- **Frontend**: SvelteKit + TailwindCSS
- **Database**: Native PostgreSQL on Windows (TCP port 5432)
- **Documentation**: Swagger/OpenAPI
- **Platform**: Windows 10/11 exclusive
- **Scripts**: PowerShell automation
- **Deployment**: Windows-native (no Docker/containers)

## Development Workflow
1. Make changes to code
2. Servers will hot-reload automatically
3. Check API documentation at `/swagger`
4. Test functionality in the web app
5. Run linting and type checking before committing

## Setup & Commands

For detailed Windows setup instructions, see [SETUP_WINDOWS.md](SETUP_WINDOWS.md)

### Essential Commands
```powershell
# Complete Windows setup
.\scripts\setup-windows.ps1

# Development mode
.\scripts\start-dev.ps1

# Production build
.\scripts\build-windows.ps1

# Production mode
.\scripts\start-prod.ps1
```

## Windows Troubleshooting
- **API fails to start**: Check PostgreSQL service status (`sc query postgresql*`)
- **Database connection**: Ensure PostgreSQL runs on port 5432, not Unix socket
- **Web app can't connect**: Verify API_HOST=localhost in .env
- **Port conflicts**: Check Windows Firewall settings for ports 3001, 5173, 5432
- **Database issues**: Run `bun run db:setup` with Administrator privileges
- **PowerShell errors**: Set execution policy (`Set-ExecutionPolicy RemoteSigned`)
- **Service issues**: Use `net start postgresql-x64-15` to start PostgreSQL

**Windows-Exclusive Version**  
Last updated: 2025-08-18