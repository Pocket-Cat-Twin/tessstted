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

# Import common library
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (Test-Path $commonLibPath) {
    . $commonLibPath
} else {
    Write-Error "PowerShell-Common.ps1 library not found."
    exit 1
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
)

# Best practices checks
$BEST_PRACTICE_PATTERNS = @(
    @{ Pattern = '#Requires -Version'; Description = "PowerShell version requirement"; Required = $true }
    @{ Pattern = '\[Parameter\(Mandatory\s*=\s*\$true\)\]'; Description = "Proper parameter validation"; Required = $false }
    @{ Pattern = 'ErrorActionPreference'; Description = "Error handling configuration"; Required = $false }
    @{ Pattern = 'try\s*\{.*catch\s*\{'; Description = "Exception handling"; Required = $false }
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
    
    # Find PowerShell files
    $psFiles = @()
    if ($pathCheck.Type -eq "File" -and $targetPath -like "*.ps1") {
        $psFiles = @($targetPath)
    } elseif ($pathCheck.Type -eq "Directory") {
        $psFiles = Get-ChildItem -Path $targetPath -Filter "*.ps1" -Recurse | Select-Object -ExpandProperty FullName
    }
    
    if ($psFiles.Count -eq 0) {
        Write-SafeOutput "No PowerShell files found in: $targetPath" -Status Warning
        return
    }
    
    Write-SafeOutput "Found $($psFiles.Count) PowerShell file(s) to validate" -Status Info
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