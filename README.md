# YuYu Lolita Shopping 🪟

Modern e-commerce platform designed **exclusively for Windows environments**.

## 🎯 Platform Support

**⚠️ Windows Only**: This project is designed and optimized exclusively for Windows 10/11. Other platforms are not supported.

## 🚀 Quick Start!

### Prerequisites (Windows)
- **Bun** runtime (latest version)
- **PostgreSQL** (Windows installation) 
- **PowerShell** 5.1+ (included with Windows)

### Installation

```powershell
# 1. Clone repository
git clone <your-repository-url>
cd yuyu-lolita-shopping

# 2. Install dependencies
bun install

# 3. Setup Windows environment (run as Administrator)
bun run setup

# 4. Start development
bun run dev
```

## 📁 Project Structure

```
├── apps/
│   ├── api/          # Backend API (Elysia + PostgreSQL)
│   └── web/          # Frontend (SvelteKit)
├── packages/
│   ├── db/           # Database schema and migrations
│   └── shared/       # Shared utilities
└── scripts/          # Windows PowerShell automation
```

## 🛠️ Available Commands

```powershell
# Development
bun run dev          # Start development servers
bun run build        # Build for production
bun run start        # Start production servers

# Database
bun run db:migrate   # Apply database migrations
bun run db:seed      # Seed database with test data
bun run db:setup     # Complete database setup

# Code Quality
bun run lint         # Lint code
bun run format       # Format code
bun run type-check   # TypeScript type checking
```

## 🌐 Access URLs

- **Web App**: http://localhost:5173
- **API Server**: http://localhost:3001
- **API Documentation**: http://localhost:3001/swagger

## 🔧 Tech Stack

- **Runtime**: Bun (Windows builds)
- **Backend**: Elysia.js + PostgreSQL + Drizzle ORM
- **Frontend**: SvelteKit + TailwindCSS
- **Database**: Native PostgreSQL on Windows (port 5432)
- **Scripts**: PowerShell automation

## 📖 Documentation

- [Windows Setup Guide](SETUP_WINDOWS.md) - Detailed Windows installation
- [Development Guide](CLAUDE.md) - Development instructions

## 🐛 Troubleshooting

Common Windows issues and solutions:

- **Database connection**: Ensure PostgreSQL service is running (`net start postgresql-x64-15`)
- **Port conflicts**: Check Windows Firewall for ports 3001, 5173, 5432
- **PowerShell errors**: Run as Administrator or set execution policy
- **Service issues**: Use `sc query postgresql*` to check PostgreSQL status

## 🤝 Support

This project is optimized for Windows development environments. For issues or questions, refer to the documentation or create an issue.

---

**Windows-Exclusive Version** | Built with ❤️ for Windows developers