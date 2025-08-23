// Optional Windows service wrapper for production deployment
// Provides utilities for running YuYu Lolita API as a Windows service

import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export interface WindowsServiceConfig {
  serviceName: string;
  displayName: string;
  description: string;
  executablePath: string;
  arguments: string[];
  workingDirectory: string;
  logPath: string;
}

export class WindowsService {
  private config: WindowsServiceConfig;

  constructor(config: WindowsServiceConfig) {
    this.config = config;
  }

  /**
   * Check if the service is installed
   */
  async isInstalled(): Promise<boolean> {
    try {
      const { stdout } = await execAsync(`sc query "${this.config.serviceName}"`);
      return stdout.includes("SERVICE_NAME");
    } catch (_error) {
      return false;
    }
  }

  /**
   * Check if the service is running
   */
  async isRunning(): Promise<boolean> {
    try {
      const { stdout } = await execAsync(`sc query "${this.config.serviceName}"`);
      return stdout.includes("RUNNING");
    } catch (_error) {
      return false;
    }
  }

  /**
   * Install the service (requires administrator privileges)
   */
  async install(): Promise<void> {
    const command = [
      "sc create",
      `"${this.config.serviceName}"`,
      `binPath= "${this.config.executablePath} ${this.config.arguments.join(" ")}"`,
      `DisplayName= "${this.config.displayName}"`,
      `Description= "${this.config.description}"`,
      "start= auto"
    ].join(" ");

    try {
      await execAsync(command);
      console.log(`✅ Service "${this.config.serviceName}" installed successfully`);
    } catch (error) {
      console.error(`❌ Failed to install service:`, error);
      throw error;
    }
  }

  /**
   * Start the service
   */
  async start(): Promise<void> {
    try {
      await execAsync(`sc start "${this.config.serviceName}"`);
      console.log(`✅ Service "${this.config.serviceName}" started successfully`);
    } catch (error) {
      console.error(`❌ Failed to start service:`, error);
      throw error;
    }
  }

  /**
   * Stop the service
   */
  async stop(): Promise<void> {
    try {
      await execAsync(`sc stop "${this.config.serviceName}"`);
      console.log(`✅ Service "${this.config.serviceName}" stopped successfully`);
    } catch (error) {
      console.error(`❌ Failed to stop service:`, error);
      throw error;
    }
  }

  /**
   * Uninstall the service
   */
  async uninstall(): Promise<void> {
    try {
      // Stop the service first if it's running
      if (await this.isRunning()) {
        await this.stop();
      }

      await execAsync(`sc delete "${this.config.serviceName}"`);
      console.log(`✅ Service "${this.config.serviceName}" uninstalled successfully`);
    } catch (error) {
      console.error(`❌ Failed to uninstall service:`, error);
      throw error;
    }
  }

  /**
   * Get service status
   */
  async getStatus(): Promise<string> {
    try {
      const { stdout } = await execAsync(`sc query "${this.config.serviceName}"`);
      
      if (stdout.includes("RUNNING")) return "RUNNING";
      if (stdout.includes("STOPPED")) return "STOPPED";
      if (stdout.includes("PENDING")) return "PENDING";
      
      return "UNKNOWN";
    } catch (_error) {
      return "NOT_INSTALLED";
    }
  }

  /**
   * Get service logs (basic implementation)
   */
  async getLogs(lines: number = 50): Promise<string[]> {
    try {
      // Basic log reading from Windows Event Log
      const command = `wevtutil qe System /q:"*[System[Provider[@Name='${this.config.serviceName}']]]" /f:text /c:${lines}`;
      const { stdout } = await execAsync(command);
      return stdout.split('\n').filter(line => line.trim());
    } catch (error) {
      console.warn("Could not retrieve service logs:", error);
      return [];
    }
  }
}

// Default configuration for YuYu Lolita API service
export function createDefaultServiceConfig(): WindowsServiceConfig {
  const executablePath = process.execPath; // Bun executable path
  const workingDirectory = process.cwd();
  
  return {
    serviceName: "YuYuLolitaAPI",
    displayName: "YuYu Lolita Shopping API",
    description: "YuYu Lolita Shopping backend API service",
    executablePath,
    arguments: ["run", "start:windows"],
    workingDirectory,
    logPath: `${workingDirectory}\\logs\\service.log`
  };
}

// Utility functions for easy service management
export async function installService(config?: WindowsServiceConfig): Promise<void> {
  const serviceConfig = config || createDefaultServiceConfig();
  const service = new WindowsService(serviceConfig);
  
  if (await service.isInstalled()) {
    console.log("⚠️  Service is already installed");
    return;
  }
  
  await service.install();
}

export async function uninstallService(config?: WindowsServiceConfig): Promise<void> {
  const serviceConfig = config || createDefaultServiceConfig();
  const service = new WindowsService(serviceConfig);
  
  if (!(await service.isInstalled())) {
    console.log("⚠️  Service is not installed");
    return;
  }
  
  await service.uninstall();
}

export async function startService(config?: WindowsServiceConfig): Promise<void> {
  const serviceConfig = config || createDefaultServiceConfig();
  const service = new WindowsService(serviceConfig);
  
  if (!(await service.isInstalled())) {
    throw new Error("Service is not installed. Install it first.");
  }
  
  await service.start();
}

export async function stopService(config?: WindowsServiceConfig): Promise<void> {
  const serviceConfig = config || createDefaultServiceConfig();
  const service = new WindowsService(serviceConfig);
  
  if (!(await service.isInstalled())) {
    throw new Error("Service is not installed.");
  }
  
  await service.stop();
}

export async function getServiceStatus(config?: WindowsServiceConfig): Promise<string> {
  const serviceConfig = config || createDefaultServiceConfig();
  const service = new WindowsService(serviceConfig);
  
  return await service.getStatus();
}

// Example usage in a CLI script:
/*
import { installService, startService, getServiceStatus } from './windows-service';

async function main() {
  try {
    console.log("Installing YuYu Lolita API as Windows service...");
    await installService();
    
    console.log("Starting service...");
    await startService();
    
    console.log("Service status:", await getServiceStatus());
  } catch (error) {
    console.error("Service operation failed:", error);
  }
}

if (import.meta.main) {
  main();
}
*/