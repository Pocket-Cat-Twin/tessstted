# 🪟 Windows Setup Guide for YuYu Lolita Shopping

Complete guide for setting up and running YuYu Lolita Shopping on Windows 10/11 with native MySQL8.

## 📋 Prerequisites

### Required Software
- **Windows 10/11** (64-bit)
- **PowerShell 5.1+** (Built into Windows)
- **Internet Connection** (for downloads)

### Automatic Installation
The setup script will automatically install missing dependencies, but you can install them manually:

#### 1. Bun Runtime
```powershell
# Run in PowerShell as Administrator
irm bun.sh/install.ps1 | iex
```

#### 2. MySQL8
Download from [mysql.com](https://dev.mysql.com/downloads/mysql/) or use package managers:

**Using Chocolatey:**
```powershell
choco install mysql
```

**Using Scoop:**
```powershell
scoop install mysql
```

**Using winget:**
```powershell
winget install Oracle.MySQL
```

---

## 🚀 Quick Start (Recommended)

### One-Command Setup
```powershell
# Clone the repository first
git clone <your-repository-url> yuyu-lolita-shopping
cd yuyu-lolita-shopping

# Run the automated setup
bun run setup:windows
```

This command will:
- ✅ Check and install Bun if needed
- ✅ Verify MySQL8 installation
- ✅ Create and configure database
- ✅ Install all dependencies
- ✅ Run database migrations
- ✅ Build all packages
- ✅ Set up environment configuration

---

## 🛠️ Manual Setup (Advanced)

### Step 1: Project Setup
```powershell
# Clone repository
git clone <your-repository-url> yuyu-lolita-shopping
cd yuyu-lolita-shopping

# Install dependencies
bun install
```

### Step 2: Environment Configuration
```powershell
# Copy Windows environment template
copy .env.windows .env

# Edit configuration (optional)
notepad .env
```

### Step 3: Database Setup
```powershell
# Setup MySQL8 database
bun run db:setup:windows

# Or manually:
bun run db:migrate:windows
```

### Step 4: Build Packages
```powershell
# Build all packages
bun run build:windows
```

---

## 🚀 Running the Application

### Development Mode

**Option 1: Automated (Recommended)**
```powershell
# Start both API and Web app in separate windows
.\scripts\start-dev.ps1

# Or using bun script
bun run dev:windows
```

**Option 2: Manual**
```powershell
# Terminal 1 - API Server
cd apps\api
bun run dev:windows

# Terminal 2 - Web App  
cd apps\web
bun run dev:windows
```

### Production Mode
```powershell
# Build and start production servers
.\scripts\start-prod.ps1

# Or using bun script
bun run start:windows
```

---

## 🔗 Access URLs

Once running, access the application at:

- **📱 Web Application**: http://localhost:5173
- **🔌 API Server**: http://localhost:3001  
- **📚 API Documentation**: http://localhost:3001/swagger

---

## 🗄️ Database Management

### Basic Commands
```powershell
# Generate new migrations
bun run db:generate

# Run migrations
bun run db:migrate:windows

# Seed database with test data
bun run db:seed:windows

# Connect to MySQL directly
mysql -u root -p yuyu_lolita
```

### MySQL Service Management
```powershell
# Start MySQL service
net start MySQL80

# Stop MySQL service  
net stop MySQL80

# Check service status
sc query MySQL80
```

### Database Connection
- **Host**: localhost
- **Port**: 3306
- **Database**: yuyu_lolita
- **Username**: root
- **Password**: (empty by default)

---

## 📦 Available Scripts

### Root Level Scripts
```powershell
# Setup and deployment
bun run setup:windows          # Complete Windows setup
bun run dev:windows            # Start development servers
bun run start:windows          # Start production servers
bun run build:windows          # Build all packages

# Database operations
bun run db:setup:windows       # Setup database
bun run db:migrate:windows     # Run migrations
bun run db:seed:windows        # Seed database

# Development
bun run lint                   # Lint code
bun run format                 # Format code
bun run type-check            # Type checking
```

### PowerShell Scripts
```powershell
.\scripts\setup-windows.ps1    # Complete environment setup
.\scripts\start-dev.ps1        # Start development mode
.\scripts\start-prod.ps1       # Start production mode
```

---

## 🔧 Configuration

### Environment Variables (.env)
```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=yuyu_lolita
DB_USER=root
DB_PASSWORD=

# API
API_HOST=localhost
API_PORT=3001

# Web App
PUBLIC_API_URL=http://localhost:3001

# Security (CHANGE IN PRODUCTION)
JWT_SECRET=your-super-secret-jwt-key
SESSION_SECRET=your-session-secret
```

### Windows-Specific Settings
- **Log Directory**: `logs/`
- **Upload Directory**: `uploads/`
- **Temp Directory**: `%TEMP%\yuyu-lolita`
- **Data Directory**: `%APPDATA%\yuyu-lolita`

---

## 🐛 Troubleshooting

### Common Issues

#### "MySQL service not found"
**Solution:**
1. Install MySQL8 from [mysql.com](https://dev.mysql.com/downloads/mysql/)
2. Ensure it's installed as a Windows service
3. Start the service: `net start MySQL80`

#### "Port already in use" (3001 or 5173)
**Solution:**
```powershell
# Find processes using the port
netstat -ano | findstr :3001
netstat -ano | findstr :5173

# Kill the process (replace PID with actual number)
taskkill /PID <process_id> /F
```

#### "Database connection failed"
**Solutions:**
1. Check MySQL service: `sc query MySQL80`
2. Verify password in .env file
3. Test connection manually:
   ```powershell
   mysql -u root -p -h localhost yuyu_lolita
   ```

#### "Bun command not found"
**Solution:**
1. Restart PowerShell
2. Reinstall Bun as Administrator:
   ```powershell
   irm bun.sh/install.ps1 | iex
   ```

#### "PowerShell Execution Policy Error"
**Solution:**
```powershell
# Set execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or bypass for single script
powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
```

### Windows Firewall
If you can't access the application from other devices:

1. Open Windows Defender Firewall
2. Allow ports 3001 and 5173 through firewall
3. Or run as Administrator:
   ```powershell
   netsh advfirewall firewall add rule name="YuYu API" dir=in action=allow protocol=TCP localport=3001
   netsh advfirewall firewall add rule name="YuYu Web" dir=in action=allow protocol=TCP localport=5173
   ```

### Performance Optimization

#### Windows Defender Exclusions
Add these folders to Windows Defender exclusions for better performance:

1. Project root folder
2. `node_modules\`
3. `apps\api\dist\`
4. `apps\web\build\`
5. `.bun\`

**To add exclusions:**
1. Open Windows Security
2. Go to Virus & threat protection
3. Manage settings under "Virus & threat protection settings"
4. Add exclusions → Folder
5. Select the project folders

---

## 🔐 Security Considerations

### Production Deployment
- Change default MySQL root password
- Update JWT_SECRET and SESSION_SECRET in .env
- Configure proper firewall rules
- Use HTTPS in production
- Regular security updates

### Default Credentials (CHANGE IN PRODUCTION)
- MySQL User: `root`
- MySQL Password: (empty by default)
- JWT Secret: `your-super-secret-jwt-key`

---

## 📈 Monitoring and Logs

### Application Logs
Logs are stored in the `logs/` directory:
- `api.log` - API server logs
- `web.log` - Web application logs

### MySQL Logs
Windows MySQL logs are typically in:
```
C:\ProgramData\MySQL\MySQL Server 8.0\Data\
```

### Performance Monitoring
```powershell
# Check running processes
Get-Process bun
Get-Process node

# Check port usage
netstat -ano | findstr :3001
netstat -ano | findstr :5173

# Check MySQL status
sc query MySQL80
```

---

## 🆘 Getting Help

### Log Collection for Support
```powershell
# Collect system information
systeminfo > system-info.txt

# Collect application logs
copy logs\*.log support-logs\

# Check service status
sc query MySQL80 > service-status.txt

# Export environment
set > environment.txt
```

### Useful Commands for Debugging
```powershell
# Check installed software
Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*MySQL*"}

# Check network connections
netstat -an | findstr LISTEN

# Check Windows version
winver

# Check PowerShell version
$PSVersionTable
```

---

## 📞 Support

If you encounter issues:

1. Check this troubleshooting guide first
2. Verify all prerequisites are installed
3. Check Windows Event Viewer for system errors
4. Collect logs and system information
5. Create an issue with detailed error information

---

**Made with ❤️ for YuYu Lolita Shopping on Windows**