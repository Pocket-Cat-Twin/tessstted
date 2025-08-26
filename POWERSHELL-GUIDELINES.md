# PowerShell Development Guidelines - Enterprise Edition
**Lolita Fashion Project - Windows Development Standards**

> **Enterprise-grade PowerShell development standards for Windows-exclusive environments**  
> Version: 2.1+ Module Architecture | Last Updated: 2025-08-24 | Author: Senior DevOps Engineer

## 🎯 CRITICAL REQUIREMENTS

### ✅ MUST-FOLLOW RULES (Zero Exceptions)

1. **NO UNICODE CHARACTERS IN POWERSHELL SCRIPTS**
   ```powershell
   # ❌ NEVER USE THESE
   Write-Host "🚨 Error occurred!"      # BREAKS PARSING
   $status = "✅"                        # CAUSES ENCODING ISSUES
   echo "✓ Success"                      # FAILS IN SOME ENVIRONMENTS
   
   # ✅ ALWAYS USE THESE
   Write-Host "[ERROR] Error occurred!"  # SAFE ASCII
   $status = "[OK]"                      # UNIVERSAL COMPATIBILITY  
   echo "[SUCCESS] Operation completed"  # WORKS EVERYWHERE
   ```

2. **HYBRID MODULE IMPORT SYSTEM**
   ```powershell
   # ✅ ENTERPRISE-GRADE HYBRID IMPORT (v2.1+)
   $moduleImported = $false
   try {
       $modulePath = Join-Path $PSScriptRoot "PowerShell-Common.psd1"
       if (Test-Path $modulePath) {
           Import-Module $modulePath -Force -ErrorAction Stop
           $moduleImported = $true
       }
   }
   catch {
       # Fallback to legacy dot-sourcing for compatibility
   }
   
   if (-not $moduleImported) {
       $commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
       if (Test-Path $commonLibPath) {
           . $commonLibPath
       } else {
           Write-Error "PowerShell-Common library not found in either format."
           exit 1
       }
   }
   ```

3. **SAFE OUTPUT FUNCTIONS ONLY**
   ```powershell
   # ❌ DON'T USE DIRECT Write-Host WITH SYMBOLS
   Write-Host "✅ Task completed" -ForegroundColor Green
   
   # ✅ USE SAFE WRAPPER FUNCTIONS
   Write-SafeOutput "Task completed" -Status Success
   Write-SafeHeader "My Script Title"
   Write-SafeSectionHeader "Configuration Check" 1
   ```

## 🏗️ Architecture Overview - Enterprise Module System (v2.1+)

### Module-First Approach
The project uses a **hybrid module system** that supports both modern PowerShell modules (.psm1/.psd1) and legacy script imports (.ps1) for maximum compatibility.

```powershell
# ✅ PREFERRED - Module Import (Enterprise)
Import-Module ./scripts/PowerShell-Common.psd1 -Force

# ⚠️ FALLBACK - Legacy Dot-Sourcing (Compatibility)  
. ./scripts/PowerShell-Common.ps1
```

### File Structure Standards

#### Module Files (.psm1)
```powershell
# PowerShell-Common.psm1
#Requires -Version 3.0

# Functions here...

# ✅ EXPLICIT EXPORTS (Required in modules)
Export-ModuleMember -Function @(
    'Write-SafeOutput',
    'Initialize-SafeEnvironment'
)
```

#### Module Manifests (.psd1)
```powershell
# PowerShell-Common.psd1  
@{
    RootModule = 'PowerShell-Common.psm1'
    ModuleVersion = '2.1.0'
    FunctionsToExport = @('Write-SafeOutput', 'Initialize-SafeEnvironment')
    # ... other metadata
}
```

### Critical Module Rules

#### ❌ **NEVER DO** - Module Errors

1. **Export-ModuleMember Outside Modules**
   ```powershell
   # ❌ WRONG - Will cause "Export-ModuleMember cannot be called" error
   Export-ModuleMember -Function *  # In .ps1 files
   ```

2. **Direct .psm1 Imports**
   ```powershell
   # ❌ WRONG - Import module file directly
   Import-Module PowerShell-Common.psm1
   
   # ✅ CORRECT - Import via manifest
   Import-Module PowerShell-Common.psd1
   ```

## 🔧 DEVELOPMENT WORKFLOW

### Before Making Changes

1. **Validate Existing Scripts**
   ```bash
   # Basic validation
   bun run validate:powershell          # Validate all PowerShell files
   bun run fix:powershell              # Auto-fix common problems
   
   # Enterprise validation
   bun run validate:powershell:strict   # Strict validation with all checks
   bun run validate:powershell:report   # Generate detailed validation report
   bun run validate:modules             # Module-specific validation
   bun run validate:modules:fix         # Auto-fix module issues
   
   # Testing commands
   bun run test:powershell             # Test module system
   bun run test:db-doctor              # Test database doctor
   
   # Complete enterprise validation
   bun run validate:enterprise         # Full enterprise-grade validation
   bun run validate:all                # Standard validation (PowerShell + linting + type-check)
   ```

2. **Test Your Script**
   ```powershell
   # Test syntax before committing
   powershell -NoProfile -Command "& './your-script.ps1' -WhatIf"
   
   # Verify encoding compatibility
   [System.IO.File]::ReadAllBytes("./your-script.ps1") | ForEach-Object { if ($_ -gt 127) { Write-Warning "Non-ASCII byte: $_" } }
   ```

### After Making Changes

1. **Automatic Validation**
   ```bash
   # These commands will automatically run on commit
   bun run validate:powershell
   bun run lint:check
   ```

2. **Manual Testing**
   ```powershell
   # Test in clean PowerShell session
   powershell -NoProfile -ExecutionPolicy Bypass -File "your-script.ps1"
   ```

## 📚 CODE STANDARDS

### File Structure Template

```powershell
# Script Purpose - Brief Description
# Enterprise-grade tool for [specific purpose]
# Version: X.X - [Brief description of version]
# Author: [Your Name]
# Last Modified: YYYY-MM-DD

#Requires -Version 3.0

param(
    [switch]$Help,
    [string]$Action = "help"
)

# Import the common PowerShell library - Hybrid Import System (Enterprise-Grade)
# Supports both Module (.psm1) and Legacy Script (.ps1) imports
$moduleImported = $false

# Try to import the PowerShell module first (preferred method)
try {
    $modulePath = Join-Path $PSScriptRoot "PowerShell-Common.psd1"
    if (Test-Path $modulePath) {
        Import-Module $modulePath -Force -ErrorAction Stop
        $moduleImported = $true
    }
}
catch {
    # Fallback to legacy dot-sourcing if module import failed
}

# Fallback to legacy dot-sourcing if module import failed
if (-not $moduleImported) {
    $commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
    if (Test-Path $commonLibPath) {
        . $commonLibPath
    } else {
        Write-Error "PowerShell-Common library not found in either format."
        exit 1
    }
}

Write-SafeHeader "Your Script Name v1.0" "="
Write-SafeOutput "Brief description of what this script does" -Status Info

# ==============================================================================
# FUNCTIONS
# ==============================================================================

function Your-Function {
    <#
    .SYNOPSIS
    Brief description of function purpose
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequiredParam
    )
    
    Write-SafeOutput "Processing: $RequiredParam" -Status Processing
    
    try {
        # Your logic here
        Write-SafeOutput "Operation successful" -Status Success
        return $true
    }
    catch {
        Write-SafeOutput "Operation failed: $($_.Exception.Message)" -Status Error
        return $false
    }
}

# ==============================================================================
# MAIN LOGIC
# ==============================================================================

switch ($Action) {
    "help" { Show-Help }
    default { Your-Function -RequiredParam $Action }
}

Write-SafeOutput "Script completed" -Status Complete
```

### Error Handling Standards

```powershell
# ✅ PROPER ERROR HANDLING
try {
    $result = Invoke-SafeCommand -Command "bun" -Arguments @("run", "build") -Description "Building application"
    if ($result.Success) {
        Write-SafeOutput "Build completed successfully" -Status Success
    } else {
        Write-SafeOutput "Build failed" -Status Error
        exit 1
    }
}
catch {
    Write-SafeOutput "Unexpected error: $($_.Exception.Message)" -Status Error
    exit 1
}

# ❌ AVOID BASIC ERROR HANDLING
try {
    bun run build
    Write-Host "✅ Build successful"  # Unicode + basic output
}
catch {
    Write-Host "❌ Build failed"      # Unicode + poor error handling
}
```

## 🛡️ VALIDATION SYSTEM

### Automatic Checks

Our validation system automatically checks for:

- **Unicode Characters**: Detects and suggests ASCII replacements
- **Encoding Issues**: Identifies problematic byte sequences
- **PowerShell Syntax**: Validates script parsing
- **Best Practices**: Ensures proper error handling patterns

### Manual Validation Commands

```powershell
# Validate specific file
powershell -File scripts/Validate-PowerShell.ps1 -Path "scripts/my-script.ps1"

# Validate and fix issues
powershell -File scripts/Validate-PowerShell.ps1 -Path "scripts" -Fix

# Generate detailed report
powershell -File scripts/Validate-PowerShell.ps1 -Path "scripts" -Report -Strict
```

## 🚫 FORBIDDEN PATTERNS

### Problematic Unicode Characters
```powershell
# ❌ NEVER USE THESE CHARACTERS
🏥 ❌ ⚠️ ✅ 💡 🔍 🌐 🚀 💻 🗃️ ⚙️ 📊 🔧 🎉 🆘 🧪 ✓ ✗
1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 8️⃣ 9️⃣ █ ▓ ▒ ░

# ✅ USE ASCII ALTERNATIVES INSTEAD
[HOSPITAL] [ERROR] [WARNING] [OK] [TIP] [SCAN] [NETWORK] [START] 
[SYSTEM] [DATABASE] [CONFIG] [REPORT] [FIX] [SUCCESS] [EMERGENCY] 
[TEST] [PASS] [FAIL] Step1 Step2 Step3 [BLOCK] [SHADE]
```

### Unsafe Patterns
```powershell
# ❌ DANGEROUS PATTERNS
echo "✅ Task done"                          # Unicode in echo
Write-Host "Processing 🔄 please wait..."   # Unicode in output
$result = "Success ✓"                       # Unicode in variables

# ✅ SAFE ALTERNATIVES
echo "[OK] Task done"                       # ASCII in echo
Write-SafeOutput "Processing, please wait..." -Status Processing
$result = "Success [PASS]"                  # ASCII in variables
```

## 🔄 PRE-COMMIT VALIDATION

### Automatic Checks (Runs on every commit)

1. **PowerShell Validation**: All .ps1 files checked for Unicode issues
2. **Syntax Validation**: PowerShell parser validation
3. **Encoding Check**: File encoding verification
4. **Best Practice Validation**: Error handling and structure checks

### Setup Pre-Commit Hooks

```bash
# Install pre-commit hooks (run once)
npm install husky --save-dev
npx husky install
npx husky add .husky/pre-commit "bun run validate:powershell"
```

## 📋 TROUBLESHOOTING

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|-----------|
| Unicode Parse Error | `TerminatorExpectedAtEndOfString` | Replace Unicode chars with ASCII |
| Encoding Problems | `В строке отсутствует завершающий символ` | Use `Write-SafeOutput` functions |
| Missing Functions | `CommandNotFoundException` | Use hybrid import system |
| Permission Errors | `ExecutionPolicy` errors | Run with `-ExecutionPolicy Bypass` |
| Export-ModuleMember Error | `Export-ModuleMember cannot be called` | Only use in .psm1 files, not .ps1 |
| Module Import Failed | Module not found errors | Check .psd1 path, use hybrid fallback |

### Emergency Fix Process

1. **Immediate Fix**
   ```powershell
   # Auto-fix all PowerShell files
   bun run fix:powershell
   ```

2. **Manual Review**
   ```powershell
   # Check specific problematic file
   powershell -File scripts/Validate-PowerShell.ps1 -Path "problematic-file.ps1" -Fix -Strict
   ```

3. **Verification**
   ```powershell
   # Verify all fixes worked
   bun run validate:all
   ```

## ✅ COMPLIANCE CHECKLIST

Before submitting any PowerShell script changes:

- [ ] No Unicode characters used (emoji, special symbols)
- [ ] Hybrid import system implemented (module first, fallback to dot-sourcing)
- [ ] `Write-SafeOutput` functions used for all output
- [ ] Proper error handling with try/catch
- [ ] `#Requires -Version 3.0` directive included
- [ ] Export-ModuleMember only used in .psm1 files (not .ps1)
- [ ] Module imports use .psd1 manifests (not direct .psm1 imports)
- [ ] Enterprise validation passes: `bun run validate:enterprise`
- [ ] Module system tests pass: `bun run test:powershell`
- [ ] Manual testing completed in clean PowerShell session
- [ ] No encoding issues detected

## 🎓 TRAINING RESOURCES

### Quick Reference Card

```powershell
# SAFE OUTPUT PATTERNS
Write-SafeOutput "Message" -Status Success|Error|Warning|Info|Processing|Complete
Write-SafeHeader "Title"
Write-SafeSectionHeader "Section Name" 1
Invoke-SafeCommand -Command "cmd" -Arguments @("param1", "param2") -Description "What it does"
Test-ServiceSafely -ServiceName "MySQL*" -PreferredVersions @("80")
Test-NetworkPortSafely -HostName "localhost" -Port 3306
```

### Common Library Functions

- `Write-SafeOutput`: Unicode-safe colored output
- `Write-SafeHeader`: Consistent header formatting
- `Invoke-SafeCommand`: Command execution with error handling
- `Test-ServiceSafely`: Windows service status checking
- `Test-NetworkPortSafely`: Network connectivity testing
- `Initialize-SafeEnvironment`: Environment setup
- `Get-ProjectRoot`: Project root directory detection

## 📞 SUPPORT

For questions about PowerShell scripting standards:
1. Check this document first
2. Run `bun run validate:powershell` to identify specific issues
3. Review `PowerShell-Common.ps1` for available functions
4. Test changes in isolated PowerShell session

---

**Remember: These standards exist to prevent production failures and ensure cross-environment compatibility. The v2.1+ module architecture provides enterprise-grade reliability with backward compatibility. Following these standards is not optional.**

---

## 📊 Architecture Migration Timeline

- **v2.0**: Legacy dot-sourcing support with Unicode fixes
- **v2.1**: Hybrid module system introduced ← **Current**  
- **v3.0**: Full module-only architecture (planned)

**Last Updated**: 2025-08-24  
**Version**: 2.1+ Enterprise Module Architecture