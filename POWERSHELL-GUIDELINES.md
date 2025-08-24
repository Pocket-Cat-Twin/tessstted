# PowerShell Scripting Guidelines for Lolita Fashion Project

> **Enterprise-Grade Standards for Windows Development**  
> Version: 2.0 | Last Updated: 2025-08-24 | Author: Senior DevOps Engineer

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

2. **USE THE COMMON LIBRARY**
   ```powershell
   # ✅ REQUIRED AT TOP OF EVERY SCRIPT
   $commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
   if (Test-Path $commonLibPath) {
       . $commonLibPath
   } else {
       Write-Error "PowerShell-Common.ps1 library not found."
       exit 1
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

## 🔧 DEVELOPMENT WORKFLOW

### Before Making Changes

1. **Validate Existing Scripts**
   ```powershell
   # Check all PowerShell files for issues
   bun run validate:powershell
   
   # Auto-fix common problems
   bun run fix:powershell
   
   # Full validation (includes linting & type-check)
   bun run validate:all
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

# Import common library
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (Test-Path $commonLibPath) {
    . $commonLibPath
} else {
    Write-Error "PowerShell-Common.ps1 library not found."
    exit 1
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
| Missing Functions | `CommandNotFoundException` | Import `PowerShell-Common.ps1` |
| Permission Errors | `ExecutionPolicy` errors | Run with `-ExecutionPolicy Bypass` |

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
- [ ] `PowerShell-Common.ps1` imported and used
- [ ] `Write-SafeOutput` functions used for all output
- [ ] Proper error handling with try/catch
- [ ] `#Requires -Version 3.0` directive included
- [ ] Validation passes: `bun run validate:powershell`
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
Test-ServiceSafely -ServiceName "postgresql*" -PreferredVersions @("16", "15")
Test-NetworkPortSafely -HostName "localhost" -Port 5432
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

**Remember: These standards exist to prevent production failures and ensure cross-environment compatibility. Following them is not optional.**