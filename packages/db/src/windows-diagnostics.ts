// Windows-specific PostgreSQL diagnostics and recovery utilities
// Helps resolve common PostgreSQL issues on Windows systems

import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export interface PostgreSQLServiceInfo {
  name: string;
  state: 'RUNNING' | 'STOPPED' | 'NOT_FOUND';
  displayName?: string;
}

export interface WindowsDiagnostics {
  services: PostgreSQLServiceInfo[];
  port5432Open: boolean;
  localhostResolvable: boolean;
  postgresExecutable: string | undefined;
  osInfo: string;
  encoding: string;
}

// Detect all PostgreSQL services on Windows
export async function detectPostgreSQLServices(): Promise<PostgreSQLServiceInfo[]> {
  try {
    const { stdout } = await execAsync('sc query type= service state= all | findstr /i postgres');
    const services: PostgreSQLServiceInfo[] = [];
    
    const serviceNames = stdout
      .split('\n')
      .filter(line => line.includes('SERVICE_NAME'))
      .map(line => line.split(':')[1]?.trim())
      .filter(Boolean);
    
    for (const serviceName of serviceNames) {
      if (!serviceName) continue;
      try {
        const { stdout: serviceInfo } = await execAsync(`sc query "${serviceName}"`);
        const isRunning = serviceInfo.includes('RUNNING');
        
        services.push({
          name: serviceName,
          state: isRunning ? 'RUNNING' : 'STOPPED',
          displayName: serviceName
        });
      } catch (error) {
        services.push({
          name: serviceName,
          state: 'NOT_FOUND'
        });
      }
    }
    
    // If no services found, check common service names
    if (services.length === 0) {
      const commonNames = [
        'postgresql-x64-16',
        'postgresql-x64-15',
        'postgresql-x64-14',
        'postgresql',
        'PostgreSQL'
      ];
      
      for (const name of commonNames) {
        try {
          const { stdout } = await execAsync(`sc query "${name}"`);
          const isRunning = stdout.includes('RUNNING');
          services.push({
            name,
            state: isRunning ? 'RUNNING' : 'STOPPED'
          });
        } catch (error) {
          // Service doesn't exist, skip
        }
      }
    }
    
    return services;
  } catch (error) {
    console.warn('[DIAGNOSTIC] Could not detect PostgreSQL services:', error);
    return [];
  }
}

// Check if port 5432 is open and in use
export async function checkPort5432(): Promise<boolean> {
  try {
    const { stdout } = await execAsync('netstat -an | findstr :5432');
    return stdout.trim().length > 0;
  } catch (error) {
    return false;
  }
}

// Check if localhost resolves correctly
export async function checkLocalhostResolution(): Promise<boolean> {
  try {
    const { stdout } = await execAsync('nslookup localhost');
    return stdout.includes('127.0.0.1');
  } catch (error) {
    return false;
  }
}

// Find PostgreSQL executable path
export async function findPostgreSQLExecutable(): Promise<string | undefined> {
  const commonPaths = [
    'C:\\Program Files\\PostgreSQL\\16\\bin\\psql.exe',
    'C:\\Program Files\\PostgreSQL\\15\\bin\\psql.exe',
    'C:\\Program Files\\PostgreSQL\\14\\bin\\psql.exe',
    'C:\\Program Files (x86)\\PostgreSQL\\16\\bin\\psql.exe',
    'C:\\Program Files (x86)\\PostgreSQL\\15\\bin\\psql.exe',
  ];
  
  for (const path of commonPaths) {
    try {
      const { stdout } = await execAsync(`"${path}" --version`);
      if (stdout.includes('psql')) {
        return path;
      }
    } catch (error) {
      // Path doesn't exist, continue
    }
  }
  
  // Try to find via PATH
  try {
    const { stdout } = await execAsync('where psql');
    return stdout.trim().split('\n')[0];
  } catch (error) {
    return undefined;
  }
}

// Get Windows OS and encoding information
export async function getWindowsInfo(): Promise<{ osInfo: string; encoding: string }> {
  try {
    const [osResult, encodingResult] = await Promise.all([
      execAsync('systeminfo | findstr /B /C:"OS Name"'),
      execAsync('chcp')
    ]);
    
    const osInfo = osResult.stdout.trim();
    const encoding = encodingResult.stdout.match(/\d+/)?.[0] || 'unknown';
    
    return {
      osInfo: osInfo.split(':')[1]?.trim() || 'Windows',
      encoding: encoding === '65001' ? 'UTF-8' : `CP${encoding}`
    };
  } catch (error) {
    return {
      osInfo: 'Windows (unknown version)',
      encoding: 'unknown'
    };
  }
}

// Run comprehensive Windows diagnostics
export async function runWindowsDiagnostics(): Promise<WindowsDiagnostics> {
  console.log('🔍 Running Windows PostgreSQL diagnostics...');
  
  const [services, port5432Open, localhostResolvable, postgresExecutable, windowsInfo] = 
    await Promise.all([
      detectPostgreSQLServices(),
      checkPort5432(),
      checkLocalhostResolution(),
      findPostgreSQLExecutable(),
      getWindowsInfo()
    ]);
  
  return {
    services,
    port5432Open,
    localhostResolvable,
    postgresExecutable,
    ...windowsInfo
  };
}

// Start PostgreSQL service automatically
export async function startPostgreSQLService(): Promise<boolean> {
  try {
    const services = await detectPostgreSQLServices();
    const stoppedService = services.find(s => s.state === 'STOPPED');
    
    if (stoppedService) {
      console.log(`🚀 Starting PostgreSQL service: ${stoppedService.name}`);
      await execAsync(`net start "${stoppedService.name}"`);
      console.log('✅ PostgreSQL service started successfully');
      return true;
    } else {
      console.log('⚠️  No stopped PostgreSQL service found to start');
      return false;
    }
  } catch (error) {
    console.error('❌ Failed to start PostgreSQL service:', error);
    return false;
  }
}

// Display comprehensive diagnostic report
export function displayDiagnosticReport(diagnostics: WindowsDiagnostics): void {
  console.log('\n📊 Windows PostgreSQL Diagnostic Report');
  console.log('===========================================');
  
  // OS Information
  console.log(`🖥️  OS: ${diagnostics.osInfo}`);
  console.log(`🔤 Encoding: ${diagnostics.encoding}`);
  
  // Services
  console.log('\n🔧 PostgreSQL Services:');
  if (diagnostics.services.length === 0) {
    console.log('   ❌ No PostgreSQL services found');
    console.log('   💡 Install PostgreSQL: https://www.postgresql.org/download/windows/');
  } else {
    diagnostics.services.forEach(service => {
      const statusIcon = service.state === 'RUNNING' ? '✅' : '❌';
      console.log(`   ${statusIcon} ${service.name}: ${service.state}`);
    });
  }
  
  // Network
  console.log('\n🌐 Network Configuration:');
  console.log(`   ${diagnostics.port5432Open ? '✅' : '❌'} Port 5432: ${diagnostics.port5432Open ? 'Open' : 'Closed'}`);
  console.log(`   ${diagnostics.localhostResolvable ? '✅' : '❌'} Localhost: ${diagnostics.localhostResolvable ? 'Resolves' : 'Resolution failed'}`);
  
  // PostgreSQL executable
  console.log('\n💻 PostgreSQL Installation:');
  if (diagnostics.postgresExecutable) {
    console.log(`   ✅ psql found: ${diagnostics.postgresExecutable}`);
  } else {
    console.log('   ❌ psql not found in PATH or common locations');
    console.log('   💡 Add PostgreSQL bin directory to PATH');
  }
  
  // Recommendations
  console.log('\n💡 Recommendations:');
  
  const runningServices = diagnostics.services.filter(s => s.state === 'RUNNING');
  const stoppedServices = diagnostics.services.filter(s => s.state === 'STOPPED');
  
  if (runningServices.length === 0 && diagnostics.services.length > 0) {
    console.log('   🚀 Start PostgreSQL service:');
    stoppedServices.forEach(service => {
      console.log(`      net start "${service.name}"`);
    });
  }
  
  if (!diagnostics.port5432Open && runningServices.length > 0) {
    console.log('   🔧 PostgreSQL may be running on a different port');
    console.log('   🔍 Check configuration: postgresql.conf');
  }
  
  if (!diagnostics.localhostResolvable) {
    console.log('   🌐 Fix localhost resolution or use 127.0.0.1 in DATABASE_URL');
  }
  
  if (diagnostics.encoding !== 'UTF-8') {
    console.log('   🔤 Consider switching to UTF-8 encoding for better character support');
    console.log('      chcp 65001');
  }
  
  console.log('\n🔗 Useful Commands:');
  console.log('   sc query postgresql*           - Check service status');
  console.log('   net start postgresql-x64-*     - Start service');
  console.log('   netstat -an | findstr :5432    - Check port');
  console.log('   psql -h localhost -U postgres  - Test connection');
  console.log('===========================================\n');
}

// Auto-fix common Windows PostgreSQL issues
export async function autoFixWindowsIssues(): Promise<{ fixed: string[]; failed: string[] }> {
  const fixed: string[] = [];
  const failed: string[] = [];
  
  console.log('🔧 Attempting to auto-fix Windows PostgreSQL issues...');
  
  try {
    // Try to start PostgreSQL service if stopped
    const serviceStarted = await startPostgreSQLService();
    if (serviceStarted) {
      fixed.push('Started PostgreSQL service');
    }
  } catch (error) {
    failed.push('Could not start PostgreSQL service');
  }
  
  // Set UTF-8 encoding for current session
  try {
    await execAsync('chcp 65001');
    fixed.push('Set UTF-8 encoding for session');
  } catch (error) {
    failed.push('Could not set UTF-8 encoding');
  }
  
  console.log(`✅ Fixed ${fixed.length} issues`);
  console.log(`❌ Failed to fix ${failed.length} issues`);
  
  return { fixed, failed };
}