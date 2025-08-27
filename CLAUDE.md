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