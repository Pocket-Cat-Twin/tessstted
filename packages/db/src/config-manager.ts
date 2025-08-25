/**
 * Enterprise Configuration Manager - Production Ready
 * Centralized configuration management with multiple sources, validation, and fallbacks
 * Designed for Windows environments with PostgreSQL integration
 * 
 * Features:
 * - Multi-source configuration loading (.env, process.env, defaults)
 * - Robust validation and error handling
 * - Windows-specific optimizations
 * - Fallback mechanisms
 * - Runtime configuration updates
 * - Configuration caching and hot-reload
 * 
 * @author Senior Configuration Engineer
 * @version 4.0 - Enterprise Grade
 * @platform Windows 10/11 + PostgreSQL
 */

import { readFileSync, existsSync, watchFile, unwatchFile } from 'fs';
import { join } from 'path';
import { runEnvironmentDiagnostics, EnvironmentDiagnostics } from './environment-diagnostics.js';

export interface AppConfiguration {
  // Database Configuration
  database: {
    url: string;
    host: string;
    port: number;
    name: string;
    username: string;
    password: string;
    ssl: boolean;
    maxConnections: number;
    connectionTimeout: number;
    validated: boolean;
  };

  // Server Configuration
  server: {
    api: {
      port: number;
      host: string;
      timeout: number;
    };
    web: {
      port: number;
      host: string;
    };
    cors: {
      origin: string | string[];
      credentials: boolean;
    };
  };

  // Security Configuration
  security: {
    jwtSecret: string;
    bcryptRounds: number;
    sessionSecret: string;
    rateLimiting: boolean;
  };

  // Application Configuration
  app: {
    environment: 'development' | 'production' | 'test';
    debug: boolean;
    logLevel: 'error' | 'warn' | 'info' | 'debug';
    skipSeed: boolean;
    platform: string;
  };

  // Windows-specific Configuration
  windows: {
    encoding: string;
    service: boolean;
    firewall: boolean;
    diagnostics: boolean;
  };

  // Runtime Configuration
  runtime: {
    loaded: boolean;
    sources: string[];
    errors: string[];
    lastUpdated: Date;
    diagnostics?: EnvironmentDiagnostics;
  };
}

export interface ConfigurationSource {
  name: string;
  priority: number;
  loader: () => Promise<Record<string, string>>;
}

export interface ValidationRule {
  key: string;
  required: boolean;
  type: 'string' | 'number' | 'boolean' | 'url' | 'port';
  validator?: (value: any) => boolean;
  default?: any;
  description: string;
}

class ConfigurationManager {
  private static instance: ConfigurationManager;
  private config: AppConfiguration;
  private sources: ConfigurationSource[] = [];
  private watchers: { [key: string]: () => void } = {};
  private validationRules: ValidationRule[] = [];
  private projectRoot: string;

  constructor() {
    this.projectRoot = this.findProjectRoot();
    this.initializeValidationRules();
    this.initializeConfigurationSources();
    this.config = this.createDefaultConfig();
  }

  static getInstance(): ConfigurationManager {
    if (!ConfigurationManager.instance) {
      ConfigurationManager.instance = new ConfigurationManager();
    }
    return ConfigurationManager.instance;
  }

  /**
   * Load and validate configuration from all sources
   */
  async loadConfiguration(): Promise<AppConfiguration> {
    console.log('🔄 Loading configuration from all sources...');

    const startTime = Date.now();
    const loadedSources: string[] = [];
    const errors: string[] = [];

    try {
      // Run environment diagnostics first
      console.log('🔍 Running environment diagnostics...');
      const diagnostics = await runEnvironmentDiagnostics();
      this.config.runtime.diagnostics = diagnostics;

      if (!diagnostics.success) {
        console.warn('⚠️  Environment diagnostics detected issues, proceeding with fallbacks');
      }

      // Load from all sources in priority order
      const allVariables: Record<string, string> = {};

      for (const source of this.sources.sort((a, b) => a.priority - b.priority)) {
        try {
          console.log(`   Loading from: ${source.name}`);
          const variables = await source.loader();
          
          // Merge variables (lower priority doesn't override higher priority)
          for (const [key, value] of Object.entries(variables)) {
            if (allVariables[key] === undefined) {
              allVariables[key] = value;
            }
          }
          
          loadedSources.push(source.name);
        } catch (error) {
          const errorMsg = `Failed to load from ${source.name}: ${error instanceof Error ? error.message : String(error)}`;
          errors.push(errorMsg);
          console.warn(`⚠️  ${errorMsg}`);
        }
      }

      // Apply loaded variables to configuration
      this.applyVariablesToConfig(allVariables);

      // Validate configuration
      const validationResult = this.validateConfiguration();
      if (!validationResult.valid) {
        console.warn('⚠️  Configuration validation issues detected:');
        validationResult.errors.forEach(error => console.warn(`   - ${error}`));
        errors.push(...validationResult.errors);
      }

      // Update runtime info
      this.config.runtime = {
        loaded: true,
        sources: loadedSources,
        errors,
        lastUpdated: new Date(),
        diagnostics
      };

      const loadTime = Date.now() - startTime;
      console.log(`✅ Configuration loaded in ${loadTime}ms from ${loadedSources.length} sources`);
      
      if (errors.length > 0) {
        console.warn(`⚠️  ${errors.length} non-critical errors during configuration loading`);
      }

    } catch (error) {
      const errorMsg = `Critical configuration loading error: ${error instanceof Error ? error.message : String(error)}`;
      console.error(`❌ ${errorMsg}`);
      errors.push(errorMsg);
      
      // Still update runtime info even on critical error
      this.config.runtime = {
        loaded: false,
        sources: loadedSources,
        errors,
        lastUpdated: new Date()
      };
      if (this.config.runtime.diagnostics) {
        this.config.runtime.diagnostics = this.config.runtime.diagnostics;
      }
    }

    return this.config;
  }

  /**
   * Get current configuration
   */
  getConfig(): AppConfiguration {
    return { ...this.config };
  }

  /**
   * Get specific configuration section
   */
  getSection<K extends keyof AppConfiguration>(section: K): AppConfiguration[K] {
    return { ...this.config[section] };
  }

  /**
   * Update configuration value at runtime
   */
  updateConfig<K extends keyof AppConfiguration>(
    section: K, 
    updates: Partial<AppConfiguration[K]>
  ): void {
    this.config[section] = { ...this.config[section], ...updates };
    this.config.runtime.lastUpdated = new Date();
  }

  /**
   * Validate current configuration
   */
  validateConfiguration(): { valid: boolean; errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    for (const rule of this.validationRules) {
      const value = this.getConfigValue(rule.key);
      
      if (rule.required && (value === undefined || value === null || value === '')) {
        errors.push(`Required configuration ${rule.key} is missing`);
        continue;
      }

      if (value !== undefined && value !== null && value !== '') {
        // Type validation
        const isValidType = this.validateType(value, rule.type);
        if (!isValidType) {
          errors.push(`Configuration ${rule.key} has invalid type, expected ${rule.type}`);
          continue;
        }

        // Custom validation
        if (rule.validator && !rule.validator(value)) {
          errors.push(`Configuration ${rule.key} failed custom validation`);
        }
      }
    }

    // Additional specific validations
    if (this.config.server.api.port === this.config.server.web.port) {
      errors.push('API and Web ports cannot be the same');
    }

    if (this.config.database.port < 1 || this.config.database.port > 65535) {
      errors.push('Database port must be between 1 and 65535');
    }

    if (this.config.app.environment === 'production' && this.config.security.jwtSecret === 'your-jwt-secret-key') {
      warnings.push('Using default JWT secret in production is not secure');
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Enable configuration hot-reload
   */
  enableHotReload(): void {
    const envPath = join(this.projectRoot, '.env');
    
    if (existsSync(envPath)) {
      console.log('🔄 Enabling configuration hot-reload...');
      
      this.watchers[envPath] = () => {
        console.log('🔄 Configuration file changed, reloading...');
        this.loadConfiguration().catch(error => {
          console.error('❌ Failed to reload configuration:', error.message);
        });
      };

      watchFile(envPath, { interval: 1000 }, this.watchers[envPath]);
    }
  }

  /**
   * Disable configuration hot-reload
   */
  disableHotReload(): void {
    for (const [path, callback] of Object.entries(this.watchers)) {
      unwatchFile(path, callback);
      delete this.watchers[path];
    }
    console.log('🔄 Configuration hot-reload disabled');
  }

  /**
   * Generate configuration report
   */
  generateReport(): void {
    console.log('\n' + '='.repeat(80));
    console.log('⚙️  CONFIGURATION REPORT');
    console.log('='.repeat(80));

    console.log(`\n📊 Runtime Information:`);
    console.log(`   Loaded: ${this.config.runtime.loaded ? '✅' : '❌'}`);
    console.log(`   Sources: ${this.config.runtime.sources.join(', ')}`);
    console.log(`   Last Updated: ${this.config.runtime.lastUpdated.toISOString()}`);
    console.log(`   Errors: ${this.config.runtime.errors.length}`);

    if (this.config.runtime.errors.length > 0) {
      console.log(`\n❌ Configuration Errors:`);
      this.config.runtime.errors.forEach((error, i) => {
        console.log(`   ${i + 1}. ${error}`);
      });
    }

    console.log(`\n🗄️  Database Configuration:`);
    console.log(`   Host: ${this.config.database.host}:${this.config.database.port}`);
    console.log(`   Database: ${this.config.database.name}`);
    console.log(`   User: ${this.config.database.username}`);
    console.log(`   SSL: ${this.config.database.ssl ? 'Enabled' : 'Disabled'}`);
    console.log(`   Validated: ${this.config.database.validated ? '✅' : '❌'}`);

    console.log(`\n🖥️  Server Configuration:`);
    console.log(`   API: ${this.config.server.api.host}:${this.config.server.api.port}`);
    console.log(`   Web: ${this.config.server.web.host}:${this.config.server.web.port}`);
    console.log(`   CORS Origin: ${this.config.server.cors.origin}`);

    console.log(`\n🚀 Application Configuration:`);
    console.log(`   Environment: ${this.config.app.environment}`);
    console.log(`   Platform: ${this.config.app.platform}`);
    console.log(`   Debug: ${this.config.app.debug ? 'Enabled' : 'Disabled'}`);
    console.log(`   Log Level: ${this.config.app.logLevel}`);

    if (process.platform === 'win32') {
      console.log(`\n🪟 Windows Configuration:`);
      console.log(`   Encoding: ${this.config.windows.encoding}`);
      console.log(`   Service Mode: ${this.config.windows.service ? 'Enabled' : 'Disabled'}`);
      console.log(`   Diagnostics: ${this.config.windows.diagnostics ? 'Enabled' : 'Disabled'}`);
    }

    const validation = this.validateConfiguration();
    console.log(`\n✅ Validation:`);
    console.log(`   Valid: ${validation.valid ? '✅' : '❌'}`);
    console.log(`   Errors: ${validation.errors.length}`);
    console.log(`   Warnings: ${validation.warnings.length}`);

    console.log('\n' + '='.repeat(80) + '\n');
  }

  /**
   * Private helper methods
   */
  private findProjectRoot(): string {
    let currentDir = process.cwd();
    
    while (currentDir !== '/') {
      if (existsSync(join(currentDir, 'package.json'))) {
        return currentDir;
      }
      currentDir = join(currentDir, '..');
    }
    
    return process.cwd();
  }

  private initializeValidationRules(): void {
    this.validationRules = [
      {
        key: 'database.url',
        required: true,
        type: 'url',
        validator: (value: string) => value.startsWith('postgresql://'),
        description: 'PostgreSQL connection URL'
      },
      {
        key: 'database.host',
        required: true,
        type: 'string',
        default: 'localhost',
        description: 'Database host'
      },
      {
        key: 'database.port',
        required: true,
        type: 'port',
        default: 5432,
        description: 'Database port'
      },
      {
        key: 'server.api.port',
        required: true,
        type: 'port',
        default: 3001,
        description: 'API server port'
      },
      {
        key: 'server.web.port',
        required: true,
        type: 'port',
        default: 5173,
        description: 'Web server port'
      },
      {
        key: 'app.environment',
        required: true,
        type: 'string',
        validator: (value: string) => ['development', 'production', 'test'].includes(value),
        default: 'development',
        description: 'Application environment'
      },
      {
        key: 'security.jwtSecret',
        required: true,
        type: 'string',
        validator: (value: string) => value.length >= 32,
        description: 'JWT secret key (minimum 32 characters)'
      }
    ];
  }

  private initializeConfigurationSources(): void {
    this.sources = [
      {
        name: 'Process Environment',
        priority: 1,
        loader: async () => {
          const env: Record<string, string> = {};
          for (const [key, value] of Object.entries(process.env)) {
            if (value !== undefined) {
              env[key] = value;
            }
          }
          return env;
        }
      },
      {
        name: '.env',
        priority: 2,
        loader: async () => this.loadEnvFile(join(this.projectRoot, '.env'))
      },
      {
        name: '.env.windows',
        priority: 3,
        loader: async () => this.loadEnvFile(join(this.projectRoot, '.env.windows'))
      },
      {
        name: '.env.local',
        priority: 4,
        loader: async () => this.loadEnvFile(join(this.projectRoot, '.env.local'))
      }
    ];
  }

  private async loadEnvFile(path: string): Promise<Record<string, string>> {
    if (!existsSync(path)) {
      return {};
    }

    const content = readFileSync(path, 'utf-8');
    const variables: Record<string, string> = {};

    const lines = content.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const equalIndex = trimmed.indexOf('=');
        if (equalIndex > 0) {
          const key = trimmed.substring(0, equalIndex).trim();
          const value = trimmed.substring(equalIndex + 1).trim();
          variables[key] = value;
        }
      }
    }

    return variables;
  }

  private applyVariablesToConfig(variables: Record<string, string>): void {
    // Database configuration
    const databaseUrl = variables.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/yuyu_lolita';
    
    try {
      const url = new URL(databaseUrl);
      this.config.database = {
        url: databaseUrl,
        host: url.hostname || 'localhost',
        port: parseInt(url.port) || 5432,
        name: url.pathname.slice(1) || 'yuyu_lolita',
        username: url.username || 'postgres',
        password: url.password || 'postgres',
        ssl: variables.DATABASE_SSL === 'true',
        maxConnections: parseInt(variables.DATABASE_MAX_CONNECTIONS || '10'),
        connectionTimeout: parseInt(variables.DATABASE_CONNECTION_TIMEOUT || '60000'),
        validated: true
      };
    } catch (error) {
      console.warn(`⚠️  Invalid DATABASE_URL format: ${error instanceof Error ? error.message : String(error)}, using defaults`);
      this.config.database.validated = false;
    }

    // Server configuration
    this.config.server = {
      api: {
        port: parseInt(variables.API_PORT || '3001'),
        host: variables.API_HOST || '0.0.0.0',
        timeout: parseInt(variables.API_TIMEOUT || '30000')
      },
      web: {
        port: parseInt(variables.WEB_PORT || '5173'),
        host: variables.HOST || '0.0.0.0'
      },
      cors: {
        origin: variables.CORS_ORIGIN || 'http://localhost:5173',
        credentials: variables.CORS_CREDENTIALS !== 'false'
      }
    };

    // Security configuration
    this.config.security = {
      jwtSecret: variables.JWT_SECRET || 'your-jwt-secret-key',
      bcryptRounds: parseInt(variables.BCRYPT_ROUNDS || '12'),
      sessionSecret: variables.SESSION_SECRET || 'your-session-secret',
      rateLimiting: variables.RATE_LIMITING !== 'false'
    };

    // Application configuration
    const nodeEnv = variables.NODE_ENV || 'development';
    this.config.app = {
      environment: ['development', 'production', 'test'].includes(nodeEnv) 
        ? nodeEnv as any 
        : 'development',
      debug: variables.DEBUG === 'true' || nodeEnv === 'development',
      logLevel: (variables.LOG_LEVEL as any) || 'info',
      skipSeed: variables.SKIP_SEED === 'true',
      platform: process.platform
    };

    // Windows-specific configuration
    this.config.windows = {
      encoding: variables.WINDOWS_ENCODING || 'utf-8',
      service: variables.ENABLE_WINDOWS_SERVICE === 'true',
      firewall: variables.WINDOWS_FIREWALL !== 'false',
      diagnostics: variables.ENABLE_DIAGNOSTICS !== 'false'
    };
  }

  private createDefaultConfig(): AppConfiguration {
    return {
      database: {
        url: 'postgresql://postgres:postgres@localhost:5432/yuyu_lolita',
        host: 'localhost',
        port: 5432,
        name: 'yuyu_lolita',
        username: 'postgres',
        password: 'postgres',
        ssl: false,
        maxConnections: 10,
        connectionTimeout: 60000,
        validated: false
      },
      server: {
        api: {
          port: 3001,
          host: '0.0.0.0',
          timeout: 30000
        },
        web: {
          port: 5173,
          host: '0.0.0.0'
        },
        cors: {
          origin: 'http://localhost:5173',
          credentials: true
        }
      },
      security: {
        jwtSecret: 'your-jwt-secret-key',
        bcryptRounds: 12,
        sessionSecret: 'your-session-secret',
        rateLimiting: true
      },
      app: {
        environment: 'development',
        debug: true,
        logLevel: 'info',
        skipSeed: false,
        platform: process.platform
      },
      windows: {
        encoding: 'utf-8',
        service: false,
        firewall: true,
        diagnostics: true
      },
      runtime: {
        loaded: false,
        sources: [],
        errors: [],
        lastUpdated: new Date()
      }
    };
  }

  private getConfigValue(path: string): any {
    const parts = path.split('.');
    let current: any = this.config;
    
    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = current[part];
      } else {
        return undefined;
      }
    }
    
    return current;
  }

  private validateType(value: any, type: string): boolean {
    switch (type) {
      case 'string':
        return typeof value === 'string';
      case 'number':
        return typeof value === 'number' && !isNaN(value);
      case 'boolean':
        return typeof value === 'boolean';
      case 'url':
        try {
          new URL(value);
          return true;
        } catch {
          return false;
        }
      case 'port':
        const port = parseInt(value);
        return !isNaN(port) && port >= 1 && port <= 65535;
      default:
        return true;
    }
  }
}

// Export singleton instance
export const configManager = ConfigurationManager.getInstance();

/**
 * Convenience functions for external usage
 */
export async function loadConfiguration(): Promise<AppConfiguration> {
  return await configManager.loadConfiguration();
}

export function getConfig(): AppConfiguration {
  return configManager.getConfig();
}

export function getConfigSection<K extends keyof AppConfiguration>(section: K): AppConfiguration[K] {
  return configManager.getSection(section);
}

export function validateConfiguration() {
  return configManager.validateConfiguration();
}

export function generateConfigurationReport(): void {
  configManager.generateReport();
}

export function enableConfigurationHotReload(): void {
  configManager.enableHotReload();
}

export function disableConfigurationHotReload(): void {
  configManager.disableHotReload();
}