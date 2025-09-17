1. First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md.
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. Please every step of the way just give me a high level explanation of what changes you made.
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. For each project you need to create their own [todo.md] in main direcrity of project.
8. Finally, add a review section to the [todo.md](http://todo.md/) file with a summary of the changes you made and any other relevant information.
9. NEVER USE EMOJI IN CODE OR COMMENTS OR LOGS. NO EMOJI. NEVER EVER.

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

## Project Learnings - Market Monitoring System (September 2025)

### Critical Implementation Insights

**Python Import Structure for Complex Projects:**
- Relative imports (`from ..module`) break when running scripts directly
- Solution: Use absolute imports (`from module`) with proper PYTHONPATH setup
- Create launcher scripts (run.py) to handle path setup before importing main modules
- Always add __init__.py files to make directories proper Python packages

**Enterprise-Grade Python Architecture Patterns:**
- Use dataclasses for structured data with built-in serialization
- Implement thread-safe operations with proper locking mechanisms  
- Context managers (__enter__/__exit__) are essential for resource cleanup
- Configuration validation should fail fast with clear error messages
- Dependency injection pattern makes testing and modularity much easier

**Database Design for Monitoring Systems:**
- Status tables (NEW/CHECKED/UNCHECKED) need proper indexing for performance
- Use UNIQUE constraints to prevent duplicate monitoring entries
- Implement proper transaction boundaries for data consistency
- Connection pooling and timeout handling are critical for reliability
- Always use parameterized queries to prevent SQL injection

**External API Integration Best Practices:**
- Implement exponential backoff retry logic for transient failures
- Rate limiting detection and handling prevents API abuse penalties
- Proper timeout settings prevent hanging operations
- Always validate API responses before processing
- Clean up resources (images, temporary files) immediately after processing

**Logging Architecture for Production Systems:**
- Multi-format logging (text + JSON) serves different use cases
- Structured logging with extra fields enables better monitoring
- Log rotation with size limits prevents disk space issues
- Performance logging helps identify bottlenecks
- Never log sensitive information (API keys, personal data)

**Configuration Management Patterns:**
- JSON schema validation catches configuration errors early
- Environment-specific configs should override base configuration
- Hot-reload capability improves development experience
- Configuration summaries help with debugging and monitoring
- Default values should be production-safe

### Technical Gotchas Discovered

**Scheduler Integration Issues:**
- APScheduler jobs need unique IDs to prevent conflicts
- Job coalescing prevents overlapping executions
- Background schedulers need proper shutdown handling
- Thread-local storage is needed for database connections in scheduled jobs

**Image Processing Pipeline:**
- PIL/Pillow image objects must be closed explicitly to prevent memory leaks
- OCR preprocessing (grayscale, contrast) significantly improves accuracy
- Image size limits are critical for API compatibility
- Temporary file cleanup must happen even if processing fails

**Error Handling Strategies:**
- Separate validation errors from runtime errors with different exception types
- Error statistics help identify systemic problems
- Graceful degradation (screenshot capture failure shouldn't stop OCR processing)
- Health checks should validate all critical system dependencies

**Performance Optimization Insights:**
- Connection reuse (database, HTTP) reduces overhead significantly  
- Lazy loading of expensive resources improves startup time
- Proper indexing strategy based on actual query patterns
- Memory management in long-running processes requires active cleanup

### Architecture Decisions That Worked Well

**Modular Component Design:**
- Each module has single responsibility with clear interfaces
- Components can be tested independently
- Configuration injection enables flexible deployment scenarios
- Error boundaries prevent cascade failures between components

**Event-Driven Processing:**
- Hotkey triggers with timer-based processing handles bursty workloads
- Status lifecycle management provides auditability
- Change detection patterns scale well with data volume
- Asynchronous processing improves user experience

**Production-Ready Features:**
- Signal handling for graceful shutdown prevents data corruption
- Health monitoring enables proactive issue detection
- Statistics collection helps with performance tuning
- Comprehensive error reporting aids troubleshooting

### What Would Be Done Differently Next Time

**Testing Strategy:**
- Unit tests should be written alongside implementation, not after
- Integration tests for database schema migrations are essential
- Mock external APIs to enable reliable automated testing
- Performance benchmarks help catch regressions early

**Documentation Approach:**
- API documentation should be generated from code annotations
- Configuration examples should cover common deployment scenarios
- Troubleshooting guide should be based on actual production issues
- Architecture diagrams help new developers understand system flow

**Development Workflow:**
- Feature flags would enable safer gradual rollouts
- Database migrations should be versioned and reversible
- Configuration changes should be validated in staging environment
- Monitoring and alerting should be implemented from the start

These learnings would have significantly accelerated development if known upfront, particularly the Python import structure issues and the need for proper resource cleanup patterns in long-running processes.

## Critical Timer Logic Fix (September 2025)

**CRITICAL GOTCHA - Status Update Timer Logic:**
When implementing timer-based status transitions in monitoring systems, always consider whether timer resets are needed during re-processing:

- **Problem**: SQL CASE statement `status_changed_at = CASE WHEN status != ? THEN CURRENT_TIMESTAMP ELSE status_changed_at END` only updates timestamp when status actually changes
- **Issue**: Re-processing CHECKED items preserved old timers instead of resetting to full duration
- **Solution**: Always update `status_changed_at = CURRENT_TIMESTAMP` when item is re-processed to reset timer to full duration

**Business Logic Impact:**
- Timer resets ensure consistent behavior when items are continuously monitored
- Prevents premature status transitions due to accumulated time from previous processing
- Critical for systems where "freshness" of data detection should restart countdown timers

**Implementation Pattern:**
```sql
-- Wrong: Preserves old timer when status doesn't change
UPDATE table SET status_changed_at = CASE WHEN status != ? THEN CURRENT_TIMESTAMP ELSE status_changed_at END

-- Correct: Always reset timer when item is re-processed
UPDATE table SET status_changed_at = CURRENT_TIMESTAMP
```

This timer logic issue could have caused significant operational problems in production if not caught during development testing.

## Database Migration Removal (September 2025)

**CRITICAL SIMPLIFICATION - Complete Migration System Removal:**
Successfully removed entire database migration system from Market Monitoring System, creating a finalized database schema approach:

**Key Changes Implemented:**
- **Removed Migration Constants:** Deleted `CURRENT_DB_VERSION` and `MIGRATIONS` dictionary (~35 lines)
- **Removed Migration Methods:** Deleted `_get_database_version()`, `_set_database_version()`, `_run_migrations()` (~85 lines) 
- **Removed Version Table:** Eliminated `db_version` table from schema
- **Simplified Initialization:** Database now uses only `_initialize_database()` method

**Final Database Schema Consolidation:**
All previous migration changes consolidated into base SCHEMA_SQL:
- `items` table: includes `processing_type` field (from migration 4)
- `sellers_current` table: includes `processing_type` + `last_updated` fields (from migrations 3,4)
- `monitoring_queue` table: includes `processing_type` field (from migration 4)  
- `sales_log` table: created directly in base schema (from migration 4)
- `changes_log`, `ocr_sessions`: unchanged (already final)

**Architecture Benefits:**
- **Code Reduction:** Eliminated ~100 lines of complex migration logic
- **Performance Improvement:** No version checking overhead during initialization
- **Maintenance Simplification:** Single schema definition, no version management complexity
- **Deployment Simplicity:** New databases created with complete schema immediately

**Implementation Pattern for Future Projects:**
```python
# Before: Complex migration system
CURRENT_DB_VERSION = 4
MIGRATIONS = {1: [...], 2: [...], 3: [...], 4: [...]}
self._run_migrations()

# After: Direct final schema
SCHEMA_SQL = {...}  # Contains all final fields
self._initialize_database()
```

**Testing Validation:**
- Created comprehensive test verifying all expected tables created
- Confirmed all fields from previous migrations included in base schema
- Verified `db_version` table properly excluded
- All database operations function correctly without migration system

**Important Considerations:**
- Approach works best when migration history can be consolidated into final schema
- Existing databases with complete schema continue working without changes  
- Very old databases (missing fields from removed migrations) would need manual schema updates
- Future schema changes will require careful planning without automated migration support

This approach should be considered for mature projects where migration history can be safely consolidated into a final schema definition, significantly reducing codebase complexity and improving system reliability.

## YANDEX_OCR.py Integration - Zero Breaking Changes Pattern (September 2025)

**CRITICAL INTEGRATION STRATEGY - Dual API Architecture for Backward Compatibility:**
Successfully integrated standalone YANDEX_OCR.py functionality into enterprise system with ZERO breaking changes using dual API pattern:

**Key Integration Insights:**

**Backward Compatibility Preservation:**
- **Additive Configuration:** Add new config fields with defaults, never replace existing ones
- **Method Renaming Strategy:** Rename internal methods for clarity while keeping public interfaces unchanged  
- **Dual Format Support:** Support both new format (OCR API) and legacy format (Vision API) simultaneously
- **Fallback Architecture:** Primary API (new working key) with fallback to existing system ensures zero downtime

**API Integration Best Practices:**
- **Authentication Flexibility:** Support multiple auth methods (Api-Key + Bearer) with runtime switching
- **Response Format Detection:** Auto-detect API response format rather than assuming structure
- **Statistics Enhancement:** Track dual API usage, success rates, fallback frequency for operational visibility
- **Configuration Validation:** Validate new configuration options while maintaining backward compatibility

**Working API Key Integration:**
- **Replace Placeholder Keys:** The system had placeholder "your_api_key_here" - real working key dramatically improves success rate
- **API Endpoint Differences:** OCR API vs Vision API have different endpoints, request formats, and response structures
- **Authentication Method Differences:** Api-Key authentication (OCR API) vs Bearer authentication (Vision API) require different header formats
- **Response Structure Differences:** OCR API uses simple fullText field vs Vision API complex blocks/lines/words hierarchy

**Enterprise Integration Patterns:**
- **Dual API with Fallback:** Try primary API with working key, fallback to existing API if needed
- **Format Auto-Detection:** Detect response format and use appropriate extraction method
- **Statistics Tracking:** Monitor both APIs independently for operational insight
- **Configuration Management:** Extend configuration without breaking existing setups

**Testing Strategy for Zero Breaking Changes:**
- **Comprehensive Integration Tests:** Test all new functionality without breaking existing code
- **API Key Validation:** Verify working API key functionality with real API calls
- **Backward Compatibility Tests:** Ensure existing method signatures and behavior unchanged
- **Statistics Validation:** Test enhanced statistics tracking includes all dual API metrics

**Configuration Management Insights:**
- **Gradual Enhancement:** Add new configuration sections alongside existing ones
- **Default Value Strategy:** All new configuration options must have production-safe defaults
- **Validation Enhancement:** Extend configuration validation without breaking existing validation
- **Documentation Critical:** Clear documentation of new options prevents configuration errors

**Performance and Reliability Improvements:**
- **Working API Key Impact:** Functional API key reduced authentication failures from 100% to 0%
- **Dual API Redundancy:** Primary + fallback APIs provide system resilience  
- **Enhanced Monitoring:** Detailed statistics enable proactive issue detection and optimization
- **Response Time Tracking:** Monitor performance differences between API endpoints for optimization

**Critical Implementation Details:**
- **MIME Type Detection:** Proper MIME type mapping critical for image processing APIs
- **Error Categorization:** Distinguish between retryable and non-retryable errors for different APIs
- **Session Management:** Reuse HTTP sessions and manage authentication headers dynamically
- **Statistics Atomicity:** Update statistics consistently across both API paths

**What Would Have Accelerated Development:**
- **API Documentation Analysis:** Understanding API differences upfront would have streamlined implementation
- **Authentication Method Research:** Knowing about Api-Key vs Bearer differences would have guided initial design  
- **Response Format Mapping:** Pre-analyzing response structure differences would have simplified parsing logic
- **Configuration Schema Design:** Planning dual configuration schema upfront would have reduced refactoring

**Production Readiness Validation:**
- **API Connection Testing:** Test actual API connectivity before deployment (not just configuration validation)
- **Load Testing:** Verify both APIs handle expected load and fail gracefully
- **Fallback Testing:** Ensure fallback mechanisms work under various failure scenarios
- **Statistics Accuracy:** Validate statistics tracking accuracy across all dual API scenarios

This integration pattern should be the template for all future API integrations where backward compatibility is critical - it enables significant system improvements without operational risk.

