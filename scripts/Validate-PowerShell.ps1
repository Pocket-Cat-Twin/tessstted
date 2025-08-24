# PowerShell Script Validation Tool
# Prevents Unicode and encoding issues in PowerShell scripts
# Version: 1.0 - Senior DevOps Quality Assurance
# Author: Senior DevOps Engineer
# Last Modified: 2025-08-24

#Requires -Version 3.0

param(
    [string]$Path = "scripts",
    [switch]$Fix = $false,
    [switch]$Strict = $false,
    [switch]$Report = $false
)

# Import the common PowerShell library - Hybrid Import System (Enterprise-Grade)
# Supports both Module (.psm1) and Legacy Script (.ps1) imports
$moduleImported = $false

# Try to import the PowerShell module first (preferred method)
try {
    $modulePath = Join-Path $PSScriptRoot "PowerShell-Common.psd1"
    if (Test-Path $modulePath) {
        Write-Host "[IMPORT] Loading PowerShell-Common module for validation..." -ForegroundColor Cyan
        Import-Module $modulePath -Force -ErrorAction Stop
        $moduleImported = $true
        Write-Host "[SUCCESS] PowerShell-Common module v2.1 loaded successfully" -ForegroundColor Green
    }
}
catch {
    Write-Host "[WARNING] Module import failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "[INFO] Falling back to legacy script import..." -ForegroundColor Cyan
}

# Fallback to legacy dot-sourcing if module import failed
if (-not $moduleImported) {
    $commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
    if (Test-Path $commonLibPath) {
        Write-Host "[FALLBACK] Using legacy PowerShell-Common.ps1..." -ForegroundColor Yellow
        . $commonLibPath
        Write-Host "[SUCCESS] Legacy PowerShell-Common library loaded" -ForegroundColor Green
    } else {
        Write-Error @"
[ERROR] PowerShell-Common library not found in either format:
  - Module: PowerShell-Common.psd1 (preferred)
  - Legacy: PowerShell-Common.ps1 (fallback)
  
Please ensure one of these files exists in the scripts directory:
  $PSScriptRoot\PowerShell-Common.psd1
  $PSScriptRoot\PowerShell-Common.ps1

If you're using the latest version, the module files should be available.
If you're using an older version, ensure PowerShell-Common.ps1 exists.
"@
        exit 1
    }
}

Write-SafeHeader "PowerShell Script Validation Tool v1.0" "="

# ==============================================================================
# VALIDATION RULES
# ==============================================================================

# Problematic Unicode characters that cause parsing errors
$PROBLEMATIC_UNICODE = @{
    # Emoji and symbols
    "🏥" = "[HOSPITAL]"
    "❌" = "[ERROR]"
    "⚠️" = "[WARNING]"
    "✅" = "[OK]"
    "💡" = "[TIP]"
    "🔍" = "[SCAN]"
    "🌐" = "[NETWORK]"
    "🚀" = "[START]"
    "💻" = "[SYSTEM]"
    "🗃️" = "[DATABASE]"
    "⚙️" = "[CONFIG]"
    "📊" = "[REPORT]"
    "🔧" = "[FIX]"
    "🎉" = "[SUCCESS]"
    "🆘" = "[EMERGENCY]"
    "🧪" = "[TEST]"
    "1️⃣" = "Step 1"
    "2️⃣" = "Step 2"
    "3️⃣" = "Step 3"
    "4️⃣" = "Step 4"
    "5️⃣" = "Step 5"
    "6️⃣" = "Step 6"
    "7️⃣" = "Step 7"
    "8️⃣" = "Step 8"
    "9️⃣" = "Step 9"
    "✓" = "[PASS]"
    "✗" = "[FAIL]"
    # Other problematic characters
    "вњ…" = "[CHECK]"  # Corrupted checkmark
    "█" = "[BLOCK]"
    "▓" = "[SHADE]"
    "▒" = "[LIGHT]"
    "░" = "[DOTS]"
}

# Patterns that indicate potential issues
$PROBLEM_PATTERNS = @(
    @{ Pattern = '[^\x00-\x7F]'; Description = "Non-ASCII characters detected"; Severity = "Warning" }
    @{ Pattern = 'echo\s+"[^"]*[^\x00-\x7F][^"]*"'; Description = "Echo with Unicode characters"; Severity = "Error" }
    @{ Pattern = 'Write-Host\s+"[^"]*[^\x00-\x7F][^"]*"'; Description = "Write-Host with Unicode characters"; Severity = "Warning" }
    @{ Pattern = '\$([A-Za-z0-9_]+)\s*=\s*"[^"]*[^\x00-\x7F][^"]*"'; Description = "Variable assignment with Unicode"; Severity = "Warning" }
    
    # MODULE DEPENDENCY VALIDATION PATTERNS (NEW - Enterprise Grade)
    @{ Pattern = 'Export-ModuleMember\s+-Function\s+\*(?!\s*$)'; Description = "Export-ModuleMember -Function * used outside module context"; Severity = "Error" }
    @{ Pattern = '^\s*\.\s+[^#\r\n]*PowerShell-Common\.ps1'; Description = "Using legacy dot-sourcing instead of module import"; Severity = "Warning" }
    @{ Pattern = 'Import-Module.*PowerShell-Common(?!\.psd1)'; Description = "Import-Module should use .psd1 manifest, not .psm1 directly"; Severity = "Warning" }
)

# Best practices checks
$BEST_PRACTICE_PATTERNS = @(
    @{ Pattern = '#Requires -Version'; Description = "PowerShell version requirement"; Required = $true }
    @{ Pattern = '\[Parameter\(Mandatory\s*=\s*\$true\)\]'; Description = "Proper parameter validation"; Required = $false }
    @{ Pattern = 'ErrorActionPreference'; Description = "Error handling configuration"; Required = $false }
    @{ Pattern = 'try\s*\{.*catch\s*\{'; Description = "Exception handling"; Required = $false }
    
    # MODULE BEST PRACTICES (NEW - Enterprise Grade)
    @{ Pattern = 'Import-Module.*-Force'; Description = "Using -Force parameter for reliable module loading"; Required = $false }
    @{ Pattern = 'Export-ModuleMember\s+-Function\s+@\('; Description = "Explicit function exports in modules"; Required = $false }
    @{ Pattern = '\$moduleImported\s*='; Description = "Module import validation pattern"; Required = $false }
)

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

function Test-PowerShellFile {
    <#
    .SYNOPSIS
    Validates a single PowerShell file for common issues
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )
    
    $results = @{
        FilePath = $FilePath
        Valid = $true
        Issues = @()
        Warnings = @()
        Suggestions = @()
        FixableIssues = @()
    }
    
    if (-not (Test-Path $FilePath)) {
        $results.Valid = $false
        $results.Issues += "File does not exist: $FilePath"
        return $results
    }
    
    try {
        $content = Get-Content $FilePath -Raw -ErrorAction Stop
    }
    catch {
        $results.Valid = $false
        $results.Issues += "Cannot read file: $($_.Exception.Message)"
        return $results
    }
    
    # Check for problematic Unicode characters
    foreach ($char in $PROBLEMATIC_UNICODE.Keys) {
        if ($content.Contains($char)) {
            $replacement = $PROBLEMATIC_UNICODE[$char]
            $results.FixableIssues += @{
                Type = "UnicodeReplacement"
                Character = $char
                Replacement = $replacement
                Description = "Replace '$char' with '$replacement'"
            }
            $results.Issues += "Problematic Unicode character found: '$char' -> suggest '$replacement'"
            $results.Valid = $false
        }
    }
    
    # Check problem patterns
    foreach ($pattern in $PROBLEM_PATTERNS) {
        if ($content -match $pattern.Pattern) {
            $issue = @{
                Type = $pattern.Severity
                Pattern = $pattern.Pattern
                Description = $pattern.Description
            }
            
            if ($pattern.Severity -eq "Error") {
                $results.Issues += $pattern.Description
                $results.Valid = $false
            } else {
                $results.Warnings += $pattern.Description
            }
        }
    }
    
    # Best practices check
    foreach ($practice in $BEST_PRACTICE_PATTERNS) {
        $hasPattern = $content -match $practice.Pattern
        
        if ($practice.Required -and -not $hasPattern) {
            $results.Issues += "Missing required: $($practice.Description)"
            $results.Valid = $false
        } elseif (-not $hasPattern) {
            $results.Suggestions += "Consider adding: $($practice.Description)"
        }
    }
    
    # PowerShell syntax check
    try {
        $null = [System.Management.Automation.PSParser]::Tokenize($content, [ref]$null)
    }
    catch {
        $results.Valid = $false
        $results.Issues += "PowerShell syntax error: $($_.Exception.Message)"
    }
    
    # MODULE DEPENDENCY VALIDATION (NEW - Enterprise Grade)
    $results = Test-ModuleDependencies -FilePath $FilePath -FileContent $content -Results $results
    
    return $results
}

function Repair-PowerShellFile {
    <#
    .SYNOPSIS
    Automatically repairs fixable issues in a PowerShell file
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        
        [Parameter(Mandatory = $true)]
        [array]$FixableIssues
    )
    
    if ($FixableIssues.Count -eq 0) {
        return @{ Success = $true; Message = "No issues to fix" }
    }
    
    try {
        $content = Get-Content $FilePath -Raw -ErrorAction Stop
        $originalContent = $content
        $changesMade = @()
        
        foreach ($issue in $FixableIssues) {
            if ($issue.Type -eq "UnicodeReplacement") {
                $oldChar = $issue.Character
                $newChar = $issue.Replacement
                
                if ($content.Contains($oldChar)) {
                    $content = $content.Replace($oldChar, $newChar)
                    $changesMade += "Replaced '$oldChar' with '$newChar'"
                }
            }
        }
        
        if ($changesMade.Count -gt 0) {
            # Create backup
            $backupPath = "$FilePath.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Set-Content $backupPath -Value $originalContent -ErrorAction Stop
            
            # Save fixed file
            Set-Content $FilePath -Value $content -ErrorAction Stop
            
            return @{
                Success = $true
                ChangesMade = $changesMade
                BackupPath = $backupPath
                Message = "File repaired successfully. Backup created: $backupPath"
            }
        } else {
            return @{ Success = $true; Message = "No changes were needed" }
        }
    }
    catch {
        return @{
            Success = $false
            Message = "Failed to repair file: $($_.Exception.Message)"
        }
    }
}

function Test-ModuleDependencies {
    <#
    .SYNOPSIS
    Enterprise-grade validation of PowerShell module dependencies and import patterns
    .DESCRIPTION
    Validates proper use of modules vs dot-sourcing, checks for Export-ModuleMember issues,
    and ensures proper module import patterns are followed.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        
        [Parameter(Mandatory = $true)]
        [string]$FileContent,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$Results
    )
    
    # Check if this is a module file (.psm1)
    $isModuleFile = $FilePath -like "*.psm1"
    
    # Check for Export-ModuleMember usage
    if ($FileContent -match 'Export-ModuleMember') {
        if (-not $isModuleFile) {
            $Results.Issues += "Export-ModuleMember found in non-module file. Only use in .psm1 files"
            $Results.Valid = $false
        } elseif ($FileContent -match 'Export-ModuleMember\s+-Function\s+\*\s*$') {
            $Results.Warnings += "Using Export-ModuleMember -Function * - consider explicit function exports for better control"
        }
    }
    
    # Check for proper module import patterns
    if ($FileContent -match '\.\s+.*PowerShell-Common\.ps1' -and 
        $FileContent -notmatch 'moduleImported.*=.*false|Import-Module.*PowerShell-Common') {
        $Results.Warnings += "Using legacy dot-sourcing without hybrid import system. Consider upgrading to module-based import"
        
        # Add fixable suggestion for upgrading to hybrid import
        $Results.Suggestions += "Upgrade to hybrid import system: Check for .psd1 module first, fallback to .ps1"
    }
    
    # Check for Import-Module best practices
    if ($FileContent -match 'Import-Module.*PowerShell-Common\.psm1') {
        $Results.Warnings += "Import-Module should reference .psd1 manifest, not .psm1 directly"
        $Results.Suggestions += "Use: Import-Module PowerShell-Common.psd1 instead of .psm1"
    }
    
    # Check for missing -Force parameter in Import-Module (in scripts that import modules)
    if ($FileContent -match 'Import-Module.*PowerShell-Common' -and 
        $FileContent -notmatch 'Import-Module.*-Force') {
        $Results.Suggestions += "Consider using -Force parameter with Import-Module for reliable loading"
    }
    
    # Validate module structure if this is a module manifest (.psd1)
    if ($FilePath -like "*.psd1") {
        if ($FileContent -notmatch 'FunctionsToExport\s*=') {
            $Results.Issues += "Module manifest missing explicit FunctionsToExport declaration"
            $Results.Valid = $false
        }
        
        if ($FileContent -notmatch 'ModuleVersion\s*=') {
            $Results.Issues += "Module manifest missing ModuleVersion"
            $Results.Valid = $false
        }
        
        if ($FileContent -notmatch 'RootModule\s*=') {
            $Results.Issues += "Module manifest missing RootModule declaration"
            $Results.Valid = $false
        }
    }
    
    # Check for hybrid import system implementation
    if ($FileContent -match 'Import-Module.*PowerShell-Common' -and 
        $FileContent -notmatch '\$moduleImported\s*=') {
        $Results.Suggestions += "Consider implementing hybrid import system for backward compatibility"
    }
    
    # Advanced: Check for proper error handling in module imports
    if ($FileContent -match 'Import-Module' -and 
        $FileContent -notmatch 'try\s*\{.*Import-Module.*\}.*catch') {
        $Results.Suggestions += "Consider wrapping Import-Module in try-catch for robust error handling"
    }
    
    return $Results
}

# ==============================================================================
# MAIN VALIDATION LOGIC
# ==============================================================================

function Invoke-PowerShellValidation {
    <#
    .SYNOPSIS
    Main validation function
    #>
    
    $targetPath = if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path (Get-ProjectRoot) $Path }
    $pathCheck = Test-PathSafely -Path $targetPath
    
    if (-not $pathCheck.Exists) {
        Write-SafeOutput "Path not found: $targetPath" -Status Error
        return
    }
    
    # Find PowerShell files (including modules - .ps1, .psm1, .psd1)
    $psFiles = @()
    $powerShellExtensions = @("*.ps1", "*.psm1", "*.psd1")
    
    if ($pathCheck.Type -eq "File") {
        $extension = [System.IO.Path]::GetExtension($targetPath).ToLower()
        if ($extension -in @(".ps1", ".psm1", ".psd1")) {
            $psFiles = @($targetPath)
        }
    } elseif ($pathCheck.Type -eq "Directory") {
        foreach ($ext in $powerShellExtensions) {
            $filesWithExt = Get-ChildItem -Path $targetPath -Filter $ext -Recurse | Select-Object -ExpandProperty FullName
            $psFiles += $filesWithExt
        }
    }
    
    if ($psFiles.Count -eq 0) {
        Write-SafeOutput "No PowerShell files (.ps1, .psm1, .psd1) found in: $targetPath" -Status Warning
        return
    }
    
    Write-SafeOutput "Found $($psFiles.Count) PowerShell file(s) to validate (.ps1, .psm1, .psd1)" -Status Info
    Write-Host ""
    
    $validationResults = @()
    $totalIssues = 0
    $totalWarnings = 0
    $fixedFiles = 0
    
    foreach ($file in $psFiles) {
        $relativePath = $file.Replace((Get-ProjectRoot), ".")
        Write-SafeOutput "Validating: $relativePath" -Status Processing
        
        $result = Test-PowerShellFile -FilePath $file
        $validationResults += $result
        
        if ($result.Issues.Count -gt 0) {
            $totalIssues += $result.Issues.Count
            Write-SafeOutput "$($result.Issues.Count) issues found" -Status Error
            
            foreach ($issue in $result.Issues) {
                Write-SafeOutput "  - $issue" -Status Error
            }
        }
        
        if ($result.Warnings.Count -gt 0) {
            $totalWarnings += $result.Warnings.Count
            Write-SafeOutput "$($result.Warnings.Count) warnings found" -Status Warning
            
            foreach ($warning in $result.Warnings) {
                Write-SafeOutput "  - $warning" -Status Warning
            }
        }
        
        if ($result.Suggestions.Count -gt 0) {
            Write-SafeOutput "$($result.Suggestions.Count) suggestions" -Status Info
            
            if ($Strict) {
                foreach ($suggestion in $result.Suggestions) {
                    Write-SafeOutput "  - $suggestion" -Status Info
                }
            }
        }
        
        # Auto-fix if requested and possible
        if ($Fix -and $result.FixableIssues.Count -gt 0) {
            Write-SafeOutput "Attempting to fix $($result.FixableIssues.Count) issues..." -Status Processing
            
            $repairResult = Repair-PowerShellFile -FilePath $file -FixableIssues $result.FixableIssues
            
            if ($repairResult.Success) {
                Write-SafeOutput "File repaired: $($repairResult.Message)" -Status Success
                if ($repairResult.ChangesMade) {
                    foreach ($change in $repairResult.ChangesMade) {
                        Write-SafeOutput "  - $change" -Status Success
                    }
                }
                $fixedFiles++
            } else {
                Write-SafeOutput "Repair failed: $($repairResult.Message)" -Status Error
            }
        } elseif ($result.FixableIssues.Count -gt 0) {
            Write-SafeOutput "$($result.FixableIssues.Count) issues can be auto-fixed with -Fix parameter" -Status Info
        }
        
        if ($result.Valid) {
            Write-SafeOutput "File is valid" -Status Success
        } else {
            Write-SafeOutput "File has issues" -Status Warning
        }
        
        Write-Host ""
    }
    
    # Summary
    Write-SafeHeader "VALIDATION SUMMARY"
    
    Write-SafeOutput "Files processed: $($psFiles.Count)" -Status Info
    Write-SafeOutput "Total issues: $totalIssues" -Status $(if ($totalIssues -eq 0) { "Success" } else { "Error" })
    Write-SafeOutput "Total warnings: $totalWarnings" -Status $(if ($totalWarnings -eq 0) { "Success" } else { "Warning" })
    
    if ($Fix) {
        Write-SafeOutput "Files repaired: $fixedFiles" -Status $(if ($fixedFiles -gt 0) { "Success" } else { "Info" })
    }
    
    $validFiles = ($validationResults | Where-Object { $_.Valid }).Count
    $invalidFiles = $psFiles.Count - $validFiles
    
    Write-SafeOutput "Valid files: $validFiles" -Status Success
    if ($invalidFiles -gt 0) {
        Write-SafeOutput "Invalid files: $invalidFiles" -Status Error
    }
    
    if ($Report) {
        # Generate detailed report
        $reportPath = Join-Path (Get-ProjectRoot) "validation-report.json"
        $reportData = @{
            Timestamp = Get-Date -Format "o"
            Summary = @{
                FilesProcessed = $psFiles.Count
                ValidFiles = $validFiles
                InvalidFiles = $invalidFiles
                TotalIssues = $totalIssues
                TotalWarnings = $totalWarnings
                FilesRepaired = $fixedFiles
            }
            Results = $validationResults
        }
        
        $reportData | ConvertTo-Json -Depth 10 | Set-Content $reportPath
        Write-SafeOutput "Detailed report saved to: validation-report.json" -Status Info
    }
    
    if ($totalIssues -eq 0) {
        Write-SafeOutput "All PowerShell files are valid!" -Status Complete
    } else {
        Write-SafeOutput "Found issues that need attention" -Status Warning
        if (-not $Fix) {
            Write-SafeOutput "Run with -Fix parameter to automatically repair fixable issues" -Status Info
        }
    }
}

# ==============================================================================
# EXECUTION
# ==============================================================================

Invoke-PowerShellValidation