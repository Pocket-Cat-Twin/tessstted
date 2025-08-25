/**
 * Environment Diagnostics System - Enterprise Grade
 * Comprehensive environment variable analysis and validation
 * Designed specifically for Windows environments with PostgreSQL
 * 
 * This module provides:
 * - Deep environment variable analysis
 * - Multi-source configuration validation
 * - Windows-specific environment diagnostics
 * - Detailed error reporting with solutions
 * - Auto-recovery mechanisms
 * 
 * @author Senior Database Engineer
 * @version 3.0 - Production Ready
 * @platform Windows 10/11 + PostgreSQL
 */

import { readFileSync, existsSync } from 'fs';
import { join, resolve } from 'path';

export interface EnvironmentDiagnostics {
  success: boolean;
  platform: string;
  environmentSources: EnvironmentSource[];
  databaseConfig: DatabaseConfig;
  validation: ValidationResult;
  issues: DiagnosticIssue[];
  recommendations: string[];
  autoFixAvailable: boolean;
}

export interface EnvironmentSource {
  name: string;
  path?: string;
  exists: boolean;
  readable: boolean;
  variables: Record<string, string>;
  errors: string[];
  priority: number;
}

export interface DatabaseConfig {
  databaseUrl?: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  source: string;
  validated: boolean;
  errors: string[];
}

export interface ValidationResult {
  requiredVariables: VariableValidation[];
  optionalVariables: VariableValidation[];
  conflicts: ConfigConflict[];
  encoding: EncodingInfo;
}

export interface VariableValidation {
  name: string;
  required: boolean;
  present: boolean;
  value?: string;
  source?: string;
  valid: boolean;
  errors: string[];
}

export interface ConfigConflict {
  variable: string;
  sources: string[];
  values: string[];
  severity: 'warning' | 'error';
  resolution: string;
}

export interface DiagnosticIssue {
  type: 'critical' | 'warning' | 'info';
  category: 'environment' | 'database' | 'platform' | 'security';
  message: string;
  details: string;
  solution: string;
  autoFixable: boolean;
}

export interface EncodingInfo {
  console: string;
  system: string;
  node: string;
  utf8Support: boolean;
  issues: string[];
}

class EnvironmentDiagnosticsEngine {
  private projectRoot: string;
  private envSources: EnvironmentSource[] = [];
  private issues: DiagnosticIssue[] = [];
  private recommendations: string[] = [];

  constructor() {
    this.projectRoot = this.findProjectRoot();
  }

  /**
   * Find the project root by looking for package.json
   */
  private findProjectRoot(): string {
    let currentDir = process.cwd();
    const maxDepth = 10;
    let depth = 0;

    while (depth < maxDepth) {
      const packageJsonPath = join(currentDir, 'package.json');
      if (existsSync(packageJsonPath)) {
        return currentDir;
      }
      
      const parentDir = resolve(currentDir, '..');
      if (parentDir === currentDir) break;
      
      currentDir = parentDir;
      depth++;
    }

    return process.cwd();
  }

  /**
   * Comprehensive environment diagnostics
   */
  async runDiagnostics(): Promise<EnvironmentDiagnostics> {
    console.log('🔍 Running comprehensive environment diagnostics...');
    
    // Reset state
    this.envSources = [];
    this.issues = [];
    this.recommendations = [];

    // Collect environment sources
    await this.collectEnvironmentSources();
    
    // Analyze database configuration
    const databaseConfig = this.analyzeDatabaseConfig();
    
    // Validate environment
    const validation = this.validateEnvironment();
    
    // Platform-specific checks
    await this.runPlatformChecks();
    
    // Check for conflicts
    this.checkForConflicts();
    
    const diagnostics: EnvironmentDiagnostics = {
      success: this.issues.filter(i => i.type === 'critical').length === 0,
      platform: this.getPlatformInfo(),
      environmentSources: this.envSources,
      databaseConfig,
      validation,
      issues: this.issues,
      recommendations: this.recommendations,
      autoFixAvailable: this.issues.some(i => i.autoFixable)
    };

    this.logDiagnosticsSummary(diagnostics);
    return diagnostics;
  }

  /**
   * Collect all possible environment sources
   */
  private async collectEnvironmentSources(): Promise<void> {
    // 1. Process environment variables (highest priority)
    const processEnvVars: Record<string, string> = {};
    for (const [key, value] of Object.entries(process.env)) {
      if (value !== undefined) {
        processEnvVars[key] = value;
      }
    }
    
    this.envSources.push({
      name: 'Process Environment',
      exists: true,
      readable: true,
      variables: processEnvVars,
      errors: [],
      priority: 1
    });

    // 2. .env file in project root
    const envPath = join(this.projectRoot, '.env');
    this.envSources.push(await this.loadEnvFile('.env', envPath, 2));

    // 3. .env.windows file
    const envWindowsPath = join(this.projectRoot, '.env.windows');
    this.envSources.push(await this.loadEnvFile('.env.windows', envWindowsPath, 3));

    // 4. .env.local file
    const envLocalPath = join(this.projectRoot, '.env.local');
    this.envSources.push(await this.loadEnvFile('.env.local', envLocalPath, 4));

    // 5. Windows system environment
    if (process.platform === 'win32') {
      this.envSources.push(await this.loadWindowsSystemEnv());
    }
  }

  /**
   * Load environment file
   */
  private async loadEnvFile(name: string, path: string, priority: number): Promise<EnvironmentSource> {
    const source: EnvironmentSource = {
      name,
      path,
      exists: existsSync(path),
      readable: false,
      variables: {},
      errors: [],
      priority
    };

    if (!source.exists) {
      source.errors.push(`File not found: ${path}`);
      return source;
    }

    try {
      const content = readFileSync(path, 'utf-8');
      source.readable = true;
      
      // Parse .env format
      const lines = content.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#')) {
          const equalIndex = trimmed.indexOf('=');
          if (equalIndex > 0) {
            const key = trimmed.substring(0, equalIndex).trim();
            const value = trimmed.substring(equalIndex + 1).trim();
            source.variables[key] = value;
          }
        }
      }
    } catch (error) {
      source.errors.push(`Failed to read file: ${error instanceof Error ? error.message : String(error)}`);
    }

    return source;
  }

  /**
   * Load Windows system environment variables
   */
  private async loadWindowsSystemEnv(): Promise<EnvironmentSource> {
    const source: EnvironmentSource = {
      name: 'Windows System Environment',
      exists: true,
      readable: true,
      variables: {},
      errors: [],
      priority: 5
    };

    try {
      // Get Windows-specific environment variables
      const relevantVars = [
        'PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD',
        'DATABASE_URL', 'NODE_ENV', 'API_PORT', 'WEB_PORT'
      ];

      for (const varName of relevantVars) {
        const value = process.env[varName];
        if (value !== undefined) {
          source.variables[varName] = value;
        }
      }
    } catch (error) {
      source.errors.push(`Failed to read Windows environment: ${error instanceof Error ? error.message : String(error)}`);
    }

    return source;
  }

  /**
   * Analyze database configuration from all sources
   */
  private analyzeDatabaseConfig(): DatabaseConfig {
    const config: DatabaseConfig = {
      source: 'none',
      validated: false,
      errors: []
    };

    // Priority order: Process env > .env > .env.windows > .env.local
    for (const source of this.envSources.sort((a, b) => a.priority - b.priority)) {
      const databaseUrl = source.variables.DATABASE_URL;
      if (databaseUrl && !config.databaseUrl) {
        config.databaseUrl = databaseUrl;
        config.source = source.name;
        
        // Parse URL components
        try {
          const url = new URL(databaseUrl);
          config.host = url.hostname || 'localhost';
          config.port = parseInt(url.port) || 5432;
          config.database = url.pathname.slice(1) || 'yuyu_lolita';
          config.username = url.username || 'postgres';
          config.password = url.password || '';
          
          // Basic validation
          if (!config.host || !config.port || !config.database) {
            config.errors.push('Invalid DATABASE_URL format');
          } else {
            config.validated = true;
          }
        } catch (error) {
          config.errors.push(`Invalid DATABASE_URL format: ${error instanceof Error ? error.message : String(error)}`);
        }
        
        break;
      }
    }

    if (!config.databaseUrl) {
      config.errors.push('DATABASE_URL not found in any environment source');
      this.addIssue({
        type: 'critical',
        category: 'database',
        message: 'DATABASE_URL not configured',
        details: 'No DATABASE_URL found in any environment source (.env, process.env, etc.)',
        solution: 'Create .env file with DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yuyu_lolita',
        autoFixable: true
      });
    } else if (!config.validated) {
      this.addIssue({
        type: 'critical',
        category: 'database',
        message: 'Invalid DATABASE_URL format',
        details: config.errors.join('; '),
        solution: 'Fix DATABASE_URL format: postgresql://username:password@host:port/database',
        autoFixable: false
      });
    }

    return config;
  }

  /**
   * Validate all environment variables
   */
  private validateEnvironment(): ValidationResult {
    const required = [
      'DATABASE_URL', 'NODE_ENV'
    ];

    const optional = [
      'API_PORT', 'WEB_PORT', 'API_HOST', 'JWT_SECRET',
      'CORS_ORIGIN', 'PUBLIC_API_URL'
    ];

    const requiredVariables: VariableValidation[] = required.map(name => {
      return this.validateVariable(name, true);
    });

    const optionalVariables: VariableValidation[] = optional.map(name => {
      return this.validateVariable(name, false);
    });

    return {
      requiredVariables,
      optionalVariables,
      conflicts: this.findConfigConflicts(),
      encoding: this.analyzeEncoding()
    };
  }

  /**
   * Validate individual variable
   */
  private validateVariable(name: string, required: boolean): VariableValidation {
    let value: string | undefined;
    let source: string | undefined;

    // Find variable in sources (by priority)
    for (const envSource of this.envSources.sort((a, b) => a.priority - b.priority)) {
      if (envSource.variables[name]) {
        value = envSource.variables[name];
        source = envSource.name;
        break;
      }
    }

    const validation: VariableValidation = {
      name,
      required,
      present: value !== undefined,
      valid: true,
      errors: []
    };
    
    if (value) {
      validation.value = this.maskSensitiveValue(name, value);
    }
    
    if (source) {
      validation.source = source;
    }

    if (required && !validation.present) {
      validation.valid = false;
      validation.errors.push('Required variable is missing');
      
      this.addIssue({
        type: 'critical',
        category: 'environment',
        message: `Required environment variable ${name} is missing`,
        details: `Variable ${name} is required but not found in any environment source`,
        solution: `Add ${name} to .env file or set as environment variable`,
        autoFixable: name === 'NODE_ENV'
      });
    }

    // Specific validation rules
    if (validation.present && value) {
      switch (name) {
        case 'DATABASE_URL':
          if (!value.startsWith('postgresql://')) {
            validation.valid = false;
            validation.errors.push('Must start with postgresql://');
          }
          break;
        case 'API_PORT':
        case 'WEB_PORT':
          const port = parseInt(value);
          if (isNaN(port) || port < 1 || port > 65535) {
            validation.valid = false;
            validation.errors.push('Must be a valid port number (1-65535)');
          }
          break;
        case 'NODE_ENV':
          if (!['development', 'production', 'test'].includes(value)) {
            validation.errors.push('Should be development, production, or test');
          }
          break;
      }
    }

    return validation;
  }

  /**
   * Find configuration conflicts between sources
   */
  private findConfigConflicts(): ConfigConflict[] {
    const conflicts: ConfigConflict[] = [];
    const variables = new Map<string, { sources: string[], values: string[] }>();

    // Collect all variables from all sources
    for (const source of this.envSources) {
      for (const [key, value] of Object.entries(source.variables)) {
        if (!variables.has(key)) {
          variables.set(key, { sources: [], values: [] });
        }
        const varInfo = variables.get(key)!;
        varInfo.sources.push(source.name);
        if (!varInfo.values.includes(value)) {
          varInfo.values.push(value);
        }
      }
    }

    // Find conflicts
    for (const [variable, info] of variables) {
      if (info.values.length > 1) {
        const severity = this.isImportantVariable(variable) ? 'error' : 'warning';
        conflicts.push({
          variable,
          sources: info.sources,
          values: info.values.map(v => this.maskSensitiveValue(variable, v)),
          severity,
          resolution: `Variable has different values in different sources. Using value from ${info.sources[0]}`
        });

        this.addIssue({
          type: severity === 'error' ? 'critical' : 'warning',
          category: 'environment',
          message: `Conflicting values for ${variable}`,
          details: `Variable ${variable} has different values in: ${info.sources.join(', ')}`,
          solution: `Remove conflicting definitions or ensure they have the same value`,
          autoFixable: false
        });
      }
    }

    return conflicts;
  }

  /**
   * Analyze text encoding setup
   */
  private analyzeEncoding(): EncodingInfo {
    const encoding: EncodingInfo = {
      console: typeof process.stdout.getColorDepth === 'function' ? 'Color supported' : 'Basic',
      system: process.platform,
      node: process.version,
      utf8Support: true,
      issues: []
    };

    // Check Windows-specific encoding issues
    if (process.platform === 'win32') {
      try {
        // Check console code page
        const consoleCp = process.env.CHCP || 'unknown';
        encoding.console = `Code page: ${consoleCp}`;
        
        if (consoleCp !== '65001') {
          encoding.utf8Support = false;
          encoding.issues.push('Console not set to UTF-8 (65001)');
          this.addIssue({
            type: 'warning',
            category: 'platform',
            message: 'Console encoding not set to UTF-8',
            details: `Current code page: ${consoleCp}, should be 65001`,
            solution: 'Run: chcp 65001',
            autoFixable: true
          });
        }
      } catch (error) {
        encoding.issues.push(`Could not determine console encoding: ${error instanceof Error ? error.message : String(error)}`);
      }
    }

    return encoding;
  }

  /**
   * Run platform-specific checks
   */
  private async runPlatformChecks(): Promise<void> {
    if (process.platform === 'win32') {
      await this.runWindowsChecks();
    } else {
      this.addIssue({
        type: 'warning',
        category: 'platform',
        message: 'Non-Windows platform detected',
        details: `This application is optimized for Windows. Current platform: ${process.platform}`,
        solution: 'Some Windows-specific features may not work correctly',
        autoFixable: false
      });
    }
  }

  /**
   * Windows-specific diagnostics
   */
  private async runWindowsChecks(): Promise<void> {
    // Check PostgreSQL installation
    try {
      const { exec } = await import('child_process');
      const { promisify } = await import('util');
      const execAsync = promisify(exec);

      // Check PostgreSQL services
      try {
        const { stdout } = await execAsync('sc query postgresql*');
        if (!stdout.includes('postgresql')) {
          this.addIssue({
            type: 'critical',
            category: 'platform',
            message: 'PostgreSQL service not found',
            details: 'No PostgreSQL services detected on Windows',
            solution: 'Install PostgreSQL from https://www.postgresql.org/download/windows/',
            autoFixable: false
          });
        } else if (!stdout.includes('RUNNING')) {
          this.addIssue({
            type: 'warning',
            category: 'platform',
            message: 'PostgreSQL service not running',
            details: 'PostgreSQL service is installed but not running',
            solution: 'Start PostgreSQL service: net start postgresql-x64-*',
            autoFixable: true
          });
        }
      } catch (error) {
        this.addIssue({
          type: 'warning',
          category: 'platform',
          message: 'Could not check PostgreSQL service',
          details: `Service check failed: ${error instanceof Error ? error.message : String(error)}`,
          solution: 'Manually verify PostgreSQL installation',
          autoFixable: false
        });
      }
    } catch (error) {
      console.warn('Could not run Windows checks:', error instanceof Error ? error.message : String(error));
    }
  }

  /**
   * Check for configuration conflicts
   */
  private checkForConflicts(): void {
    // Check for port conflicts
    const apiPort = this.getVariableValue('API_PORT');
    const webPort = this.getVariableValue('WEB_PORT');

    if (apiPort && webPort && apiPort === webPort) {
      this.addIssue({
        type: 'critical',
        category: 'environment',
        message: 'Port conflict between API and Web',
        details: `Both API_PORT and WEB_PORT are set to ${apiPort}`,
        solution: 'Set different ports: API_PORT=3001, WEB_PORT=5173',
        autoFixable: true
      });
    }

    // Check for generic PORT variable conflict
    const genericPort = this.getVariableValue('PORT');
    if (genericPort) {
      this.addIssue({
        type: 'warning',
        category: 'environment',
        message: 'Generic PORT variable detected',
        details: 'Generic PORT variable can cause conflicts between API and Web',
        solution: 'Remove PORT variable, use API_PORT and WEB_PORT instead',
        autoFixable: true
      });
    }
  }

  /**
   * Helper methods
   */
  private addIssue(issue: DiagnosticIssue): void {
    this.issues.push(issue);
  }

  private getVariableValue(name: string): string | undefined {
    for (const source of this.envSources.sort((a, b) => a.priority - b.priority)) {
      if (source.variables[name]) {
        return source.variables[name];
      }
    }
    return undefined;
  }

  private maskSensitiveValue(name: string, value: string): string {
    if (name.toLowerCase().includes('password') || name.toLowerCase().includes('secret')) {
      return '***';
    }
    if (name === 'DATABASE_URL') {
      return value.replace(/:\/\/[^@]*@/, '://***:***@');
    }
    return value;
  }

  private isImportantVariable(name: string): boolean {
    return ['DATABASE_URL', 'API_PORT', 'WEB_PORT', 'NODE_ENV', 'JWT_SECRET'].includes(name);
  }

  private getPlatformInfo(): string {
    return `${process.platform} ${process.arch} - Node.js ${process.version}`;
  }

  private logDiagnosticsSummary(diagnostics: EnvironmentDiagnostics): void {
    console.log('\n📊 Environment Diagnostics Summary:');
    console.log(`   Platform: ${diagnostics.platform}`);
    console.log(`   Sources: ${diagnostics.environmentSources.length} detected`);
    console.log(`   Database Config: ${diagnostics.databaseConfig.validated ? '✅ Valid' : '❌ Invalid'}`);
    console.log(`   Issues: ${diagnostics.issues.length} found`);
    
    const critical = diagnostics.issues.filter(i => i.type === 'critical').length;
    const warnings = diagnostics.issues.filter(i => i.type === 'warning').length;
    
    if (critical > 0) {
      console.log(`   🚨 Critical: ${critical}`);
    }
    if (warnings > 0) {
      console.log(`   ⚠️  Warnings: ${warnings}`);
    }
    
    if (diagnostics.autoFixAvailable) {
      console.log('   🔧 Auto-fix available');
    }
    
    console.log(`   Overall: ${diagnostics.success ? '✅ Healthy' : '❌ Issues found'}\n`);
  }
}

/**
 * Public API
 */
export async function runEnvironmentDiagnostics(): Promise<EnvironmentDiagnostics> {
  const engine = new EnvironmentDiagnosticsEngine();
  return await engine.runDiagnostics();
}

export async function autoFixEnvironmentIssues(diagnostics: EnvironmentDiagnostics): Promise<boolean> {
  console.log('🔧 Auto-fixing environment issues...');
  
  let fixedCount = 0;
  
  for (const issue of diagnostics.issues.filter(i => i.autoFixable)) {
    console.log(`   Fixing: ${issue.message}`);
    
    try {
      switch (issue.category) {
        case 'environment':
          if (issue.message.includes('NODE_ENV')) {
            process.env.NODE_ENV = 'development';
            fixedCount++;
          }
          // Add more auto-fixes here
          break;
        case 'platform':
          if (issue.message.includes('UTF-8')) {
            // Set console to UTF-8
            if (process.platform === 'win32') {
              const { exec } = await import('child_process');
              exec('chcp 65001', () => {
                console.log('   ✅ Console encoding set to UTF-8');
              });
              fixedCount++;
            }
          }
          break;
      }
    } catch (error) {
      console.log(`   ❌ Failed to fix: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  
  console.log(`\n🔧 Auto-fix completed: ${fixedCount} issues fixed\n`);
  return fixedCount > 0;
}

/**
 * Display comprehensive environment report
 */
export function displayEnvironmentReport(diagnostics: EnvironmentDiagnostics): void {
  console.log('\n' + '='.repeat(80));
  console.log('🔍 COMPREHENSIVE ENVIRONMENT DIAGNOSTICS REPORT');
  console.log('='.repeat(80));
  
  console.log(`\n📋 System Information:`);
  console.log(`   Platform: ${diagnostics.platform}`);
  
  console.log(`\n📁 Environment Sources (${diagnostics.environmentSources.length}):`);
  for (const source of diagnostics.environmentSources) {
    const status = source.exists ? (source.readable ? '✅' : '⚠️') : '❌';
    console.log(`   ${status} ${source.name} ${source.path ? `(${source.path})` : ''}`);
    if (source.errors.length > 0) {
      source.errors.forEach(error => console.log(`      Error: ${error}`));
    }
  }
  
  console.log(`\n🗄️  Database Configuration:`);
  console.log(`   Source: ${diagnostics.databaseConfig.source}`);
  console.log(`   Valid: ${diagnostics.databaseConfig.validated ? '✅' : '❌'}`);
  if (diagnostics.databaseConfig.host) {
    console.log(`   Host: ${diagnostics.databaseConfig.host}:${diagnostics.databaseConfig.port}`);
    console.log(`   Database: ${diagnostics.databaseConfig.database}`);
    console.log(`   User: ${diagnostics.databaseConfig.username}`);
  }
  
  if (diagnostics.issues.length > 0) {
    console.log(`\n🚨 Issues Found (${diagnostics.issues.length}):`);
    const critical = diagnostics.issues.filter(i => i.type === 'critical');
    const warnings = diagnostics.issues.filter(i => i.type === 'warning');
    
    if (critical.length > 0) {
      console.log(`\n   🔴 Critical Issues (${critical.length}):`);
      critical.forEach((issue, i) => {
        console.log(`   ${i + 1}. ${issue.message}`);
        console.log(`      Category: ${issue.category}`);
        console.log(`      Details: ${issue.details}`);
        console.log(`      Solution: ${issue.solution}`);
        if (issue.autoFixable) console.log(`      Auto-fixable: Yes`);
        console.log();
      });
    }
    
    if (warnings.length > 0) {
      console.log(`   🟡 Warnings (${warnings.length}):`);
      warnings.forEach((issue, i) => {
        console.log(`   ${i + 1}. ${issue.message}`);
        console.log(`      Solution: ${issue.solution}`);
        console.log();
      });
    }
  } else {
    console.log(`\n✅ No issues found - Environment is healthy!`);
  }
  
  if (diagnostics.recommendations.length > 0) {
    console.log(`\n💡 Recommendations:`);
    diagnostics.recommendations.forEach((rec, i) => {
      console.log(`   ${i + 1}. ${rec}`);
    });
  }
  
  console.log('\n' + '='.repeat(80));
  console.log(`📊 Overall Status: ${diagnostics.success ? '✅ HEALTHY' : '❌ ISSUES DETECTED'}`);
  console.log('='.repeat(80) + '\n');
}