/**
 * Startup Validator - Enterprise Grade
 * Pre-startup system validation and health checks
 * Ensures system readiness before application launch
 * 
 * Features:
 * - Pre-startup validation checks
 * - Critical dependency verification
 * - Configuration validation
 * - Database readiness assessment
 * - Environment compatibility checks
 * - Automatic issue resolution suggestions
 * 
 * @author Senior System Reliability Engineer
 * @version 2.0 - Production Ready
 * @platform Windows 10/11 + PostgreSQL
 */

import { runEnvironmentDiagnostics } from './environment-diagnostics.js';
import { loadConfiguration, validateConfiguration } from './config-manager.js';
import { handleDatabaseError } from './database-error-handler.js';
import { db, users } from './index.js';

export interface StartupValidationResult {
  overall: {
    passed: boolean;
    score: number;
    maxScore: number;
    readyForStartup: boolean;
    criticalIssues: number;
    warnings: number;
  };
  checks: {
    environment: StartupCheckResult;
    configuration: StartupCheckResult;
    database: StartupCheckResult;
    dependencies: StartupCheckResult;
    ports: StartupCheckResult;
    system: StartupCheckResult;
  };
  issues: StartupIssue[];
  recommendations: string[];
  autoFixAvailable: boolean;
  estimatedFixTime: number;
}

export interface StartupCheckResult {
  name: string;
  passed: boolean;
  score: number;
  maxScore: number;
  duration: number;
  details: string;
  issues: string[];
  warnings: string[];
}

export interface StartupIssue {
  category: 'critical' | 'warning' | 'info';
  component: string;
  message: string;
  solution: string;
  autoFixable: boolean;
  estimatedFixTime: number;
}

class StartupValidator {
  private issues: StartupIssue[] = [];
  private recommendations: string[] = [];

  /**
   * Run comprehensive startup validation
   */
  async validateStartup(): Promise<StartupValidationResult> {
    console.log('🚀 Running Pre-Startup Validation System');
    console.log('=' .repeat(60));

    const startTime = Date.now();
    this.issues = [];
    this.recommendations = [];

    const result: StartupValidationResult = {
      overall: {
        passed: false,
        score: 0,
        maxScore: 0,
        readyForStartup: false,
        criticalIssues: 0,
        warnings: 0
      },
      checks: {
        environment: await this.checkEnvironment(),
        configuration: await this.checkConfiguration(),
        database: await this.checkDatabase(),
        dependencies: await this.checkDependencies(),
        ports: await this.checkPorts(),
        system: await this.checkSystemRequirements()
      },
      issues: this.issues,
      recommendations: this.recommendations,
      autoFixAvailable: false,
      estimatedFixTime: 0
    };

    // Calculate overall results
    const checks = Object.values(result.checks);
    result.overall.score = checks.reduce((sum, check) => sum + check.score, 0);
    result.overall.maxScore = checks.reduce((sum, check) => sum + check.maxScore, 0);
    result.overall.criticalIssues = this.issues.filter(i => i.category === 'critical').length;
    result.overall.warnings = this.issues.filter(i => i.category === 'warning').length;
    result.overall.passed = result.overall.criticalIssues === 0;
    result.overall.readyForStartup = result.overall.passed && (result.overall.score / result.overall.maxScore) >= 0.8;

    // Auto-fix assessment
    const autoFixableIssues = this.issues.filter(i => i.autoFixable);
    result.autoFixAvailable = autoFixableIssues.length > 0;
    result.estimatedFixTime = autoFixableIssues.reduce((sum, issue) => sum + issue.estimatedFixTime, 0);

    const totalTime = Date.now() - startTime;
    
    // Display results
    this.displayValidationResults(result, totalTime);

    return result;
  }

  /**
   * Check environment configuration
   */
  private async checkEnvironment(): Promise<StartupCheckResult> {
    const startTime = Date.now();
    const result: StartupCheckResult = {
      name: 'Environment Configuration',
      passed: false,
      score: 0,
      maxScore: 25,
      duration: 0,
      details: '',
      issues: [],
      warnings: []
    };

    try {
      console.log('🔍 Checking environment configuration...');
      
      const diagnostics = await runEnvironmentDiagnostics();
      
      if (diagnostics.success) {
        result.score = 25;
        result.passed = true;
        result.details = `Environment validation passed with ${diagnostics.issues.length} total issues`;
      } else {
        const criticalIssues = diagnostics.issues.filter(i => i.type === 'critical');
        if (criticalIssues.length === 0) {
          result.score = 15;
          result.passed = true;
          result.details = `Environment validation passed with warnings`;
          result.warnings.push(...diagnostics.issues.map(i => i.message));
        } else {
          result.score = 5;
          result.passed = false;
          result.details = `Environment validation failed: ${criticalIssues.length} critical issues`;
          result.issues.push(...criticalIssues.map(i => i.message));
          
          // Add to main issues list
          criticalIssues.forEach(issue => {
            this.issues.push({
              category: 'critical',
              component: 'Environment',
              message: issue.message,
              solution: issue.solution,
              autoFixable: issue.autoFixable,
              estimatedFixTime: 2
            });
          });
        }
      }

      if (!diagnostics.databaseConfig.validated) {
        this.issues.push({
          category: 'critical',
          component: 'Environment',
          message: 'DATABASE_URL configuration is invalid',
          solution: 'Fix DATABASE_URL format in .env file',
          autoFixable: false,
          estimatedFixTime: 3
        });
      }

    } catch (error) {
      result.passed = false;
      result.score = 0;
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.details = `Environment check failed: ${errorMessage}`;
      result.issues.push(errorMessage);
      
      this.issues.push({
        category: 'critical',
        component: 'Environment',
        message: `Environment diagnostics failed: ${error instanceof Error ? error.message : String(error)}`,
        solution: 'Check environment diagnostics system',
        autoFixable: false,
        estimatedFixTime: 5
      });
    }

    result.duration = Date.now() - startTime;
    console.log(`   ${result.passed ? '✅' : '❌'} ${result.name}: ${result.details} (${result.duration}ms)`);
    return result;
  }

  /**
   * Check configuration management
   */
  private async checkConfiguration(): Promise<StartupCheckResult> {
    const startTime = Date.now();
    const result: StartupCheckResult = {
      name: 'Configuration Management',
      passed: false,
      score: 0,
      maxScore: 20,
      duration: 0,
      details: '',
      issues: [],
      warnings: []
    };

    try {
      console.log('⚙️  Checking configuration management...');
      
      const config = await loadConfiguration();
      const validation = validateConfiguration();
      
      if (config.runtime.loaded && validation.valid) {
        result.score = 20;
        result.passed = true;
        result.details = `Configuration loaded from ${config.runtime.sources.length} sources, validation passed`;
      } else if (config.runtime.loaded) {
        result.score = 12;
        result.passed = true;
        result.details = `Configuration loaded with ${validation.errors.length} validation issues`;
        result.warnings.push(...validation.errors);
        result.warnings.push(...validation.warnings);
      } else {
        result.score = 0;
        result.passed = false;
        result.details = 'Configuration loading failed';
        result.issues.push(...config.runtime.errors);
        
        this.issues.push({
          category: 'critical',
          component: 'Configuration',
          message: 'Configuration system failed to load',
          solution: 'Check .env files and configuration sources',
          autoFixable: false,
          estimatedFixTime: 5
        });
      }

      if (validation.errors.length > 0) {
        validation.errors.forEach(error => {
          this.issues.push({
            category: 'warning',
            component: 'Configuration',
            message: error,
            solution: 'Fix configuration validation errors',
            autoFixable: false,
            estimatedFixTime: 2
          });
        });
      }

    } catch (error) {
      result.passed = false;
      result.score = 0;
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.details = `Configuration check failed: ${errorMessage}`;
      result.issues.push(errorMessage);
      
      this.issues.push({
        category: 'critical',
        component: 'Configuration',
        message: `Configuration system error: ${errorMessage}`,
        solution: 'Check configuration management system',
        autoFixable: false,
        estimatedFixTime: 5
      });
    }

    result.duration = Date.now() - startTime;
    console.log(`   ${result.passed ? '✅' : '❌'} ${result.name}: ${result.details} (${result.duration}ms)`);
    return result;
  }

  /**
   * Check database connectivity
   */
  private async checkDatabase(): Promise<StartupCheckResult> {
    const startTime = Date.now();
    const result: StartupCheckResult = {
      name: 'Database Connectivity',
      passed: false,
      score: 0,
      maxScore: 30,
      duration: 0,
      details: '',
      issues: [],
      warnings: []
    };

    try {
      console.log('🗄️  Checking database connectivity...');
      
      // Test database connection with timeout
      await Promise.race([
        db.select().from(users).limit(0),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Connection timeout after 10 seconds')), 10000))
      ]);

      result.score = 30;
      result.passed = true;
      result.details = 'Database connection successful';
      
    } catch (error) {
      result.passed = false;
      result.score = 0;
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.details = `Database connection failed: ${errorMessage}`;
      result.issues.push(errorMessage);
      
      try {
        // Use error handler for detailed analysis
        const dbError = await handleDatabaseError(error instanceof Error ? error : new Error(String(error)), 'startup-validation');
        
        this.issues.push({
          category: 'critical',
          component: 'Database',
          message: `Database connection failed: ${dbError.analysis.rootCause}`,
          solution: dbError.solutions.length > 0 ? dbError.solutions[0]?.title || 'Check database configuration' : 'Check database configuration',
          autoFixable: dbError.recovery.autoRecoverable,
          estimatedFixTime: dbError.recovery.estimatedRecoveryTime
        });

        if (dbError.recovery.autoRecoverable) {
          result.details += ` (auto-recovery available)`;
        }
        
      } catch (handlerError) {
        this.issues.push({
          category: 'critical',
          component: 'Database',
          message: `Database connection failed: ${error instanceof Error ? error.message : String(error)}`,
          solution: 'Check PostgreSQL service and DATABASE_URL configuration',
          autoFixable: false,
          estimatedFixTime: 10
        });
      }
    }

    result.duration = Date.now() - startTime;
    console.log(`   ${result.passed ? '✅' : '❌'} ${result.name}: ${result.details} (${result.duration}ms)`);
    return result;
  }

  /**
   * Check system dependencies
   */
  private async checkDependencies(): Promise<StartupCheckResult> {
    const startTime = Date.now();
    const result: StartupCheckResult = {
      name: 'System Dependencies',
      passed: false,
      score: 0,
      maxScore: 15,
      duration: 0,
      details: '',
      issues: [],
      warnings: []
    };

    try {
      console.log('📦 Checking system dependencies...');
      
      // Check Node.js/Bun
      const nodeVersion = process.version;
      const isNodeVersionValid = parseInt(nodeVersion.slice(1)) >= 18;

      if (isNodeVersionValid) {
        result.score = 15;
        result.passed = true;
        result.details = `Node.js ${nodeVersion} (compatible)`;
      } else {
        result.score = 0;
        result.passed = false;
        result.details = `Node.js ${nodeVersion} (requires >= 18.0.0)`;
        result.issues.push(`Node.js version ${nodeVersion} is below minimum required version 18.0.0`);
        
        this.issues.push({
          category: 'critical',
          component: 'Dependencies',
          message: `Node.js version ${nodeVersion} is too old`,
          solution: 'Upgrade Node.js to version 18.0.0 or higher',
          autoFixable: false,
          estimatedFixTime: 10
        });
      }

      // Check if we're running in Bun
      if (typeof Bun !== 'undefined') {
        result.details += ` + Bun runtime`;
        result.score = Math.min(result.score + 5, result.maxScore);
      }

    } catch (error) {
      result.passed = false;
      result.score = 0;
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.details = `Dependency check failed: ${errorMessage}`;
      result.issues.push(errorMessage);
    }

    result.duration = Date.now() - startTime;
    console.log(`   ${result.passed ? '✅' : '❌'} ${result.name}: ${result.details} (${result.duration}ms)`);
    return result;
  }

  /**
   * Check port availability
   */
  private async checkPorts(): Promise<StartupCheckResult> {
    const startTime = Date.now();
    const result: StartupCheckResult = {
      name: 'Port Availability',
      passed: false,
      score: 0,
      maxScore: 10,
      duration: 0,
      details: '',
      issues: [],
      warnings: []
    };

    try {
      console.log('🔌 Checking port availability...');
      
      const requiredPorts = [3001, 5173]; // API and Web ports
      const portChecks: string[] = [];
      let availablePorts = 0;

      for (const port of requiredPorts) {
        try {
          // Create a test server to check if port is available
          const { createServer } = await import('net');
          const server = createServer();
          
          await new Promise<void>((resolve, reject) => {
            server.listen(port, () => {
              server.close(() => resolve());
            }).on('error', reject);
          });
          
          portChecks.push(`${port}: available`);
          availablePorts++;
        } catch {
          portChecks.push(`${port}: in use`);
          result.warnings.push(`Port ${port} is already in use`);
          
          this.issues.push({
            category: 'warning',
            component: 'Ports',
            message: `Port ${port} is already in use`,
            solution: `Stop the service using port ${port} or configure a different port`,
            autoFixable: false,
            estimatedFixTime: 3
          });
        }
      }

      result.score = Math.round((availablePorts / requiredPorts.length) * result.maxScore);
      result.passed = availablePorts >= requiredPorts.length * 0.5; // Pass if at least 50% of ports are available
      result.details = `${availablePorts}/${requiredPorts.length} ports available: ${portChecks.join(', ')}`;

    } catch (error) {
      result.passed = false;
      result.score = 0;
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.details = `Port check failed: ${errorMessage}`;
      result.issues.push(errorMessage);
    }

    result.duration = Date.now() - startTime;
    console.log(`   ${result.passed ? '✅' : '❌'} ${result.name}: ${result.details} (${result.duration}ms)`);
    return result;
  }

  /**
   * Check system requirements
   */
  private async checkSystemRequirements(): Promise<StartupCheckResult> {
    const startTime = Date.now();
    const result: StartupCheckResult = {
      name: 'System Requirements',
      passed: false,
      score: 0,
      maxScore: 10,
      duration: 0,
      details: '',
      issues: [],
      warnings: []
    };

    try {
      console.log('💻 Checking system requirements...');
      
      const platform = process.platform;
      const arch = process.arch;
      
      if (platform === 'win32') {
        result.score = 10;
        result.passed = true;
        result.details = `Windows ${arch} (optimized platform)`;
        
        this.recommendations.push('System is running on the optimized Windows platform');
      } else {
        result.score = 5;
        result.passed = true;
        result.details = `${platform} ${arch} (compatibility mode)`;
        result.warnings.push(`Running on ${platform}, some Windows-specific features may not be available`);
        
        this.issues.push({
          category: 'warning',
          component: 'System',
          message: `Running on ${platform} instead of optimized Windows platform`,
          solution: 'Some Windows-specific features may not work correctly',
          autoFixable: false,
          estimatedFixTime: 0
        });
      }

    } catch (error) {
      result.passed = false;
      result.score = 0;
      const errorMessage = error instanceof Error ? error.message : String(error);
      result.details = `System requirements check failed: ${errorMessage}`;
      result.issues.push(errorMessage);
    }

    result.duration = Date.now() - startTime;
    console.log(`   ${result.passed ? '✅' : '❌'} ${result.name}: ${result.details} (${result.duration}ms)`);
    return result;
  }

  /**
   * Display validation results
   */
  private displayValidationResults(result: StartupValidationResult, duration: number): void {
    console.log('\n' + '=' .repeat(60));
    console.log('📊 STARTUP VALIDATION RESULTS');
    console.log('=' .repeat(60));

    const percentage = Math.round((result.overall.score / result.overall.maxScore) * 100);
    
    console.log(`\n🎯 Overall Score: ${result.overall.score}/${result.overall.maxScore} (${percentage}%)`);
    console.log(`⏱️  Validation Time: ${duration}ms`);
    console.log(`🚦 System Status: ${result.overall.readyForStartup ? '✅ READY FOR STARTUP' : '❌ NOT READY'}`);

    if (result.overall.criticalIssues > 0) {
      console.log(`🚨 Critical Issues: ${result.overall.criticalIssues}`);
    }
    if (result.overall.warnings > 0) {
      console.log(`⚠️  Warnings: ${result.overall.warnings}`);
    }

    console.log('\n📋 Component Status:');
    Object.entries(result.checks).forEach(([, check]) => {
      const status = check.passed ? '✅' : '❌';
      const score = `${check.score}/${check.maxScore}`;
      console.log(`   ${status} ${check.name}: ${score} - ${check.details}`);
    });

    if (result.issues.length > 0) {
      console.log('\n🔧 Issues Found:');
      const criticalIssues = result.issues.filter(i => i.category === 'critical');
      const warnings = result.issues.filter(i => i.category === 'warning');

      if (criticalIssues.length > 0) {
        console.log('\n   🚨 Critical Issues:');
        criticalIssues.forEach((issue, i) => {
          console.log(`   ${i + 1}. [${issue.component}] ${issue.message}`);
          console.log(`      Solution: ${issue.solution}`);
          if (issue.autoFixable) {
            console.log(`      Auto-fixable: Yes (${issue.estimatedFixTime} min)`);
          }
        });
      }

      if (warnings.length > 0) {
        console.log('\n   ⚠️  Warnings:');
        warnings.forEach((warning, i) => {
          console.log(`   ${i + 1}. [${warning.component}] ${warning.message}`);
        });
      }
    }

    if (result.recommendations.length > 0) {
      console.log('\n💡 Recommendations:');
      result.recommendations.forEach((rec, i) => {
        console.log(`   ${i + 1}. ${rec}`);
      });
    }

    if (result.autoFixAvailable) {
      console.log(`\n🔧 Auto-fix Available: ${result.estimatedFixTime} minutes estimated`);
      console.log('   Run with auto-fix: .\\scripts\\db-doctor.ps1 -Enterprise');
    }

    console.log('\n' + '=' .repeat(60));
    
    if (result.overall.readyForStartup) {
      console.log('🚀 SYSTEM IS READY FOR STARTUP!');
      console.log('   You can now start the application safely.');
    } else {
      console.log('🚨 SYSTEM NOT READY FOR STARTUP');
      console.log('   Please resolve the issues above before starting the application.');
      console.log('\n📋 Next Steps:');
      console.log('   1. Fix critical issues listed above');
      console.log('   2. Re-run startup validation: bun run validate:startup');
      console.log('   3. Or try auto-fix: .\\scripts\\db-doctor.ps1 -Enterprise');
    }
    
    console.log('=' .repeat(60));
  }
}

/**
 * Public API
 */
export async function validateStartup(): Promise<StartupValidationResult> {
  const validator = new StartupValidator();
  return await validator.validateStartup();
}

export async function runStartupValidation(): Promise<void> {
  const result = await validateStartup();
  
  if (!result.overall.readyForStartup) {
    process.exit(1);
  }
}

// Run validation if this file is executed directly
if (import.meta.main) {
  runStartupValidation().catch(error => {
    console.error('❌ Startup validation failed:', error.message);
    process.exit(1);
  });
}