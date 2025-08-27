1. First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md.
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. Please every step of the way just give me a high level explanation of what changes you made.
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. For each project you need to create their own [todo.md] in main direcrity of project.
8. Finally, add a review section to the [todo.md](http://todo.md/) file with a summary of the changes you made and any other relevant information.


When working with my code:

1. **Think deeply** before making any edits
2. **Understand the full context** of the code and requirements
3. **Ask clarifying questions** when requirements are ambiguous
4. **Think from first principles** - don't make assumptions
5. **Assess refactoring after every green** - Look for opportunities to improve code structure, but only refactor if it adds value
6. **Keep project docs current** - update them whenever you introduce meaningful changes
   **At the end of every change, update CLAUDE.md with anything useful you wished you'd known at the start**.
   This is CRITICAL - Claude should capture learnings, gotchas, patterns discovered, or any context that would have made the task easier if known upfront. This continuous documentation ensures future work benefits from accumulated knowledge


### Communication

- Be explicit about trade-offs in different approaches
- Explain the reasoning behind significant design decisions
- Flag any deviations from these guidelines with justification
- Suggest improvements that align with these principles
- When unsure, ask for clarification rather than assuming



## Resources and References

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Testing Library Principles](https://testing-library.com/docs/guiding-principles)
- [Kent C. Dodds Testing JavaScript](https://testingjavascript.com/)
- [Functional Programming in TypeScript](https://gcanti.github.io/fp-ts/)

## Summary

The key is to write clean, testable, functional code that evolves through small, safe increments. Every change should be driven by a test that describes the desired behavior, and the implementation should be the simplest thing that makes that test pass. When in doubt, favor simplicity and readability over cleverness.

## PowerShell Script Learnings & Gotchas

### PowerShell Automatic Variables Conflicts (Aug 2025)

**Issue**: PowerShell scripts in `scripts/` folder had two critical variable naming conflicts:

1. **`[CmdletBinding()]` + Explicit `[switch]$Verbose`**: Causes "Parameter named 'Verbose' has already been defined" error
2. **Using `$host` as Variable Name**: Causes "Cannot overwrite variable Host because it is constant" error

**Solutions Applied**:
- **Verbose Parameter**: Remove explicit `[switch]$Verbose = $false` - `[CmdletBinding()]` provides it automatically
- **Host Variable**: Replace all `$host` variables with `$hostName` throughout the codebase

**Files Affected**:
- `scripts/db-environment-check-windows.ps1` - Both issues fixed
- `scripts/PowerShell-Common.ps1` - Host variable issue fixed

**Key Learnings**:
- PowerShell automatic variables (`$host`, `$error`, `$input`, etc.) are read-only and cannot be assigned
- `[CmdletBinding()]` automatically provides common parameters (`-Verbose`, `-Debug`, `-ErrorAction`, etc.)
- Always use descriptive variable names like `$hostName`, `$serverName` instead of PowerShell reserved words
- Test PowerShell scripts incrementally to catch variable conflicts early

**Future Prevention**:
- Avoid these PowerShell reserved variable names: `$host`, `$home`, `$input`, `$output`, `$error`, `$matches`
- When using `[CmdletBinding()]`, don't explicitly define automatic parameters
- Use PowerShell validators like `Test-PowerShellScripts.ps1` before deployment

### Critical MySQL Client Requirements (Aug 2025)

**Issue**: PowerShell database validation scripts were skipping MySQL connection tests with WARN status when mysql.exe was not found, allowing incomplete environment validation.

**Requirement Change**: MySQL client availability is now MANDATORY - tests must never skip with warnings.

**Critical Updates Applied**:
- **Connection Test**: `Test-MySQLConnectionSecure` now returns `$false` (failure) instead of `$true` (skip) when mysql.exe not found
- **Database Check**: `Test-DatabaseExists` now returns `$false` (failure) instead of `$true` (skip) when mysql.exe not found
- **Error Level**: Changed from Warning to Error status for missing MySQL client
- **Detailed Logging**: Added comprehensive search and validation logging

**Files Modified**:
- `scripts/db-environment-check-windows.ps1` - Both critical functions updated
- `scripts/PowerShell-Common.ps1` - `Test-MySQLConnectionSecure` function updated

**Enhanced Validation Logic**:
1. **Comprehensive Search**: Checks PATH + common installation directories
2. **Automatic PATH Addition**: Temporarily adds found MySQL installation to PATH
3. **Detailed Error Reporting**: Lists all searched locations when mysql.exe not found
4. **Critical Failure**: Returns `$false` to fail environment validation completely

**Common MySQL Installation Paths Searched**:
- `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe` (explicit hardcoded path)
- `${env:ProgramFiles}\MySQL\MySQL Server 8.0\bin\mysql.exe` (environment variable path)
- `${env:ProgramFiles}\MySQL\MySQL Server 5.7\bin\mysql.exe`
- `${env:ProgramFiles(x86)}\MySQL\MySQL Server 8.0\bin\mysql.exe`
- `${env:ProgramFiles(x86)}\MySQL\MySQL Server 5.7\bin\mysql.exe`

**Key Principle**: Database connectivity validation is MANDATORY - no skipping allowed. Environment setup cannot proceed without verified MySQL client availability.

### Comprehensive Database Configuration System (Aug 2025)

**Major Enhancement**: Implemented complete database configuration management system to resolve environment variable loading issues and improve security.

**Root Issue Solved**: Database scripts were failing with "Access denied (using password: NO)" because environment variables weren't being loaded properly. The `process.env.DB_PASSWORD` was returning `undefined` due to missing dotenv configuration.

**New Architecture Implemented**:

**1. Centralized Configuration (`packages/db/src/config.ts`)**:
- Automatic `.env` file detection and loading
- Comprehensive environment variable validation
- Type-safe configuration objects
- Enhanced error messages with troubleshooting guidance
- Connection testing with detailed diagnostics

**2. Enhanced Connection Layer (`packages/db/src/connection.ts`)**:
- Auto-initialization from environment configuration
- Improved error handling with specific solutions
- Connection retry logic and validation
- Better logging and diagnostic information
- Security-focused connection options

**3. Standardized Database Scripts**:
- **`seed-users.ts`**: Now uses centralized config, improved error handling
- **`migrate.ts`**: Streamlined with auto-configuration
- **`health-check.ts`**: Enhanced validation and reporting

**4. Security Improvements**:
- **`scripts/setup-mysql-user.sql`**: Complete MySQL user creation script
- **`scripts/setup-mysql-user-windows.ps1`**: Automated PowerShell user setup
- Password complexity validation
- Dedicated application users instead of root access

**5. Enhanced PowerShell Validation**:
- **`db-environment-check-windows.ps1`**: Comprehensive .env validation
- Password strength checking
- Security warnings for weak configurations
- Detailed troubleshooting guidance

**Key Configuration Pattern**:
```typescript
// OLD PATTERN (problematic)
const config = {
  host: process.env.DB_HOST || "localhost",
  password: process.env.DB_PASSWORD || ""  // Empty string when undefined!
};

// NEW PATTERN (robust)
import { getDatabaseConfig, initializeConnection } from "./config.js";

// Automatically loads .env, validates all variables, provides detailed errors
const config = getDatabaseConfig();
initializeConnection(); // Then use getPool()
```

**Critical Environment Variable Loading**:
```typescript
// config.ts handles this automatically:
dotenv.config({ path: '.env' });           // Loads environment variables
validateDatabaseConfig();                  // Validates all required vars
```

**Security Enhancements Applied**:
- Minimum password length validation (8+ characters)
- Password complexity checking (uppercase, lowercase, numbers, symbols)
- Common weak password detection ("password", "123456", etc.)
- Root user usage warnings
- Dedicated application user creation scripts

**Files Created/Modified**:
- NEW: `packages/db/src/config.ts` - Centralized configuration system
- NEW: `scripts/setup-mysql-user.sql` - MySQL user creation
- NEW: `scripts/setup-mysql-user-windows.ps1` - PowerShell automation
- NEW: `DATABASE_SETUP.md` - Comprehensive setup guide
- ENHANCED: `packages/db/src/connection.ts` - Better error handling
- ENHANCED: `packages/db/src/seed-users.ts` - Auto-configuration
- ENHANCED: `packages/db/src/migrate.ts` - Streamlined setup
- ENHANCED: `scripts/db-environment-check-windows.ps1` - Security validation

**TypeScript Build Process**:
- Fixed compilation errors related to invalid MySQL pool options
- Removed unused variables and imports
- Ensured type safety across all database modules

**Usage Examples**:
```bash
# Complete database setup (new enhanced process)
npm run db:setup:full:windows

# Environment validation with security checks
npm run db:check:windows

# Create secure MySQL user
powershell -File scripts/setup-mysql-user-windows.ps1

# Test configuration
npm run db:health:mysql
```

**Impact**:
- ✅ Eliminates "Access denied (using password: NO)" errors
- ✅ Provides clear error messages with solutions
- ✅ Implements security best practices
- ✅ Automates complex database setup processes
- ✅ Creates comprehensive documentation
- ✅ Prevents similar configuration issues in future

**This comprehensive solution addresses the immediate password issue while creating a robust, secure, and maintainable database configuration system that prevents similar issues and enhances overall system security.**

### PowerShell Regex and Parsing Critical Fixes (Aug 2025)

**Issue**: PowerShell script `db-environment-check-windows.ps1` had critical syntax errors causing complete script failure:
- Line 213: Unescaped colon `:` in regex character class caused "Unexpected token ':' in expression" error
- Line 265: Unescaped `+` symbol in string caused "You must provide a value expression following the '+' operator" error

**Root Cause**: PowerShell parser interprets certain characters as operators even within strings and regex patterns when not properly escaped.

**Critical Fixes Applied**:

1. **Regex Escaping Fix (Line 213)**:
```powershell
# BEFORE (BROKEN):
$hasSymbol = $value -match "[!@#$%^&*(),.?\":{}|<>]"

# AFTER (FIXED):  
$hasSymbol = $value -match "[!@#$%^&*(),.?\\":{}|<>]"
```

2. **String Parsing Fix (Line 265)**:
```powershell
# BEFORE (BROKEN):
Write-SafeOutput "  2. Use strong passwords (12+ chars, mixed case, numbers, symbols)" -Status Info

# AFTER (FIXED):
Write-SafeOutput "  2. Use strong passwords (12 or more chars, mixed case, numbers, symbols)" -Status Info  
```

**PowerShell Escaping Rules (CRITICAL for future development)**:
- **Colon in Regex**: Always escape `:` as `\\:` in character classes `[...]`
- **Plus in Strings**: Avoid `12+` patterns, use `12 or more` or `12+` with proper context
- **Regex Special Characters**: Always escape `[]{}()*+?\\^$|` when used literally
- **Double Escaping**: PowerShell often requires double backslashes `\\` for single backslash

**Files Fixed**:
- `scripts/db-environment-check-windows.ps1` - Lines 213, 265

**Impact**:
- ✅ Eliminates PowerShell syntax parsing errors  
- ✅ Enables database environment validation to function
- ✅ Fixes all dependent npm scripts: `db:check:windows`, `db:setup:full:windows`
- ✅ Prevents similar regex/parsing issues in future PowerShell development

**Prevention Strategy**: Always test PowerShell regex patterns and string interpolation in isolated contexts before integrating into production scripts.