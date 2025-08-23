import { spawn } from "child_process";
import { createWriteStream, createReadStream } from "fs";
import { mkdir, readdir, stat, unlink } from "fs/promises";
import { join } from "path";
import { createGzip, createGunzip } from "zlib";
import { createJobLogger, logBusinessEvent } from "./logger";
import type { ReadableStream } from "stream/web";

const backupLogger = createJobLogger("backup-service");

// Backup configuration
const BACKUP_CONFIG = {
  // Directory to store backups
  backupDir: process.env.BACKUP_DIR || "/tmp/yuyu-backups",

  // Database connection info
  database: {
    host: process.env.DB_HOST || "localhost",
    port: process.env.DB_PORT || "5432",
    database: process.env.DB_NAME || "yuyu_lolita",
    username: process.env.DB_USER || "postgres",
    password: process.env.DB_PASSWORD || "password",
  },

  // Backup retention policy
  retention: {
    daily: 7, // Keep 7 daily backups
    weekly: 4, // Keep 4 weekly backups
    monthly: 12, // Keep 12 monthly backups
  },

  // Compression settings
  compression: {
    enabled: true,
    level: 6, // gzip compression level (1-9)
  },

  // Backup types
  types: {
    full: true, // Full database dump
    schema: true, // Schema only
    data: true, // Data only
    custom: true, // Custom format (PostgreSQL)
  },
};

interface BackupOptions {
  type: "full" | "schema" | "data" | "custom";
  compress?: boolean;
  fileName?: string;
}

interface BackupResult {
  success: boolean;
  fileName: string;
  filePath: string;
  fileSize: number;
  duration: number;
  error?: string;
}

// Ensure backup directory exists
const ensureBackupDirectory = async (): Promise<void> => {
  try {
    await mkdir(BACKUP_CONFIG.backupDir, { recursive: true });
  } catch (error) {
    backupLogger.error("Failed to create backup directory", {
      error,
      backupDir: BACKUP_CONFIG.backupDir,
    });
    throw error;
  }
};

// Generate backup filename
const generateBackupFileName = (
  type: string,
  compress: boolean = true,
): string => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const extension = type === "custom" ? "dump" : "sql";
  const compressedExt = compress ? ".gz" : "";

  return `yuyu-backup-${type}-${timestamp}.${extension}${compressedExt}`;
};

// Execute pg_dump command
const executePgDump = async (options: BackupOptions): Promise<BackupResult> => {
  const startTime = Date.now();
  const fileName =
    options.fileName || generateBackupFileName(options.type, options.compress);
  const filePath = join(BACKUP_CONFIG.backupDir, fileName);

  return new Promise((resolve, _reject) => {
    // Build pg_dump arguments
    const args = [
      "--host",
      BACKUP_CONFIG.database.host,
      "--port",
      BACKUP_CONFIG.database.port,
      "--username",
      BACKUP_CONFIG.database.username,
      "--no-password", // Use PGPASSWORD environment variable
      "--verbose",
    ];

    // Add type-specific arguments
    switch (options.type) {
      case "schema":
        args.push("--schema-only");
        break;
      case "data":
        args.push("--data-only");
        break;
      case "custom":
        args.push("--format=custom");
        args.push("--compress=6");
        break;
      case "full":
      default:
        // Full backup includes both schema and data
        break;
    }

    args.push(BACKUP_CONFIG.database.database);

    backupLogger.info("Starting backup", {
      type: options.type,
      fileName,
      args: args.filter((arg) => arg !== BACKUP_CONFIG.database.password),
    });

    // Set environment variables
    const env = {
      ...process.env,
      PGPASSWORD: BACKUP_CONFIG.database.password,
    };

    // Spawn pg_dump process
    const pgDump = spawn("pg_dump", args, { env });

    let errorOutput = "";

    // Handle stderr (pg_dump outputs progress to stderr)
    pgDump.stderr.on("data", (data) => {
      const message = data.toString();
      if (message.includes("ERROR") || message.includes("FATAL")) {
        errorOutput += message;
      }
      backupLogger.debug("pg_dump output", { message: message.trim() });
    });

    // Handle process completion
    pgDump.on("close", async (code) => {
      const duration = Date.now() - startTime;

      if (code !== 0) {
        backupLogger.error("pg_dump failed", { code, error: errorOutput });
        resolve({
          success: false,
          fileName,
          filePath,
          fileSize: 0,
          duration,
          error: `pg_dump exited with code ${code}: ${errorOutput}`,
        });
        return;
      }

      try {
        // Get file size
        const stats = await stat(filePath);
        const fileSize = stats.size;

        backupLogger.info("Backup completed successfully", {
          fileName,
          fileSize,
          duration,
        });

        logBusinessEvent(
          "database_backup_completed",
          "system",
          "backup-service",
          { fileName, fileSize, duration, type: options.type },
        );

        resolve({
          success: true,
          fileName,
          filePath,
          fileSize,
          duration,
        });
      } catch (error) {
        backupLogger.error("Failed to get backup file stats", { error });
        resolve({
          success: false,
          fileName,
          filePath,
          fileSize: 0,
          duration,
          error: "Failed to verify backup file",
        });
      }
    });

    pgDump.on("error", (error) => {
      backupLogger.error("pg_dump process error", { error });
      resolve({
        success: false,
        fileName,
        filePath,
        fileSize: 0,
        duration: Date.now() - startTime,
        error: error.message,
      });
    });

    // Create output stream
    if (options.compress !== false && BACKUP_CONFIG.compression.enabled) {
      // Compressed backup
      const fileStream = createWriteStream(filePath);
      const gzipStream = createGzip({ level: BACKUP_CONFIG.compression.level });

      pgDump.stdout.pipe(gzipStream).pipe(fileStream);
    } else {
      // Uncompressed backup
      const fileStream = createWriteStream(filePath);
      pgDump.stdout.pipe(fileStream);
    }
  });
};

// Create full backup
export const createFullBackup = async (
  compress: boolean = true,
): Promise<BackupResult> => {
  await ensureBackupDirectory();
  return executePgDump({ type: "full", compress });
};

// Create schema-only backup
export const createSchemaBackup = async (
  compress: boolean = true,
): Promise<BackupResult> => {
  await ensureBackupDirectory();
  return executePgDump({ type: "schema", compress });
};

// Create data-only backup
export const createDataBackup = async (
  compress: boolean = true,
): Promise<BackupResult> => {
  await ensureBackupDirectory();
  return executePgDump({ type: "data", compress });
};

// Create custom format backup (PostgreSQL specific)
export const createCustomBackup = async (): Promise<BackupResult> => {
  await ensureBackupDirectory();
  return executePgDump({ type: "custom", compress: false }); // Custom format has built-in compression
};

// List existing backups
export const listBackups = async () => {
  try {
    await ensureBackupDirectory();
    const files = await readdir(BACKUP_CONFIG.backupDir);

    const backups = await Promise.all(
      files
        .filter((file) => file.startsWith("yuyu-backup-"))
        .map(async (file) => {
          const filePath = join(BACKUP_CONFIG.backupDir, file);
          const stats = await stat(filePath);

          return {
            fileName: file,
            filePath,
            fileSize: stats.size,
            createdAt: stats.birthtime,
            modifiedAt: stats.mtime,
            type: file.includes("-schema-")
              ? "schema"
              : file.includes("-data-")
                ? "data"
                : file.includes("-custom-")
                  ? "custom"
                  : "full",
            compressed: file.endsWith(".gz"),
          };
        }),
    );

    // Sort by creation date (newest first)
    return backups.sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime(),
    );
  } catch (error) {
    backupLogger.error("Failed to list backups", { error });
    throw error;
  }
};

// Delete old backups based on retention policy
export const cleanupOldBackups = async (): Promise<{
  deleted: string[];
  kept: string[];
}> => {
  const deleted: string[] = [];
  const kept: string[] = [];

  try {
    const backups = await listBackups();
    const now = new Date();

    for (const backup of backups) {
      const age = now.getTime() - backup.createdAt.getTime();
      const daysDiff = age / (1000 * 60 * 60 * 24);

      let shouldDelete = false;

      // Apply retention policy
      if (daysDiff > BACKUP_CONFIG.retention.monthly * 30) {
        // Older than monthly retention
        shouldDelete = true;
      } else if (daysDiff > BACKUP_CONFIG.retention.weekly * 7) {
        // Older than weekly retention, keep only monthly backups (1st of month)
        const isFirstOfMonth = backup.createdAt.getDate() === 1;
        shouldDelete = !isFirstOfMonth;
      } else if (daysDiff > BACKUP_CONFIG.retention.daily) {
        // Older than daily retention, keep only weekly backups (Sundays)
        const isSunday = backup.createdAt.getDay() === 0;
        shouldDelete = !isSunday;
      }

      if (shouldDelete) {
        try {
          await unlink(backup.filePath);
          deleted.push(backup.fileName);
          backupLogger.info("Deleted old backup", {
            fileName: backup.fileName,
            age: Math.round(daysDiff),
          });
        } catch (error) {
          backupLogger.error("Failed to delete backup", {
            fileName: backup.fileName,
            error,
          });
        }
      } else {
        kept.push(backup.fileName);
      }
    }

    if (deleted.length > 0) {
      logBusinessEvent("backup_cleanup_completed", "system", "backup-service", {
        deletedCount: deleted.length,
        keptCount: kept.length,
      });
    }

    return { deleted, kept };
  } catch (error) {
    backupLogger.error("Failed to cleanup old backups", { error });
    throw error;
  }
};

// Restore from backup
export const restoreFromBackup = async (
  backupFileName: string,
): Promise<boolean> => {
  const backupPath = join(BACKUP_CONFIG.backupDir, backupFileName);

  try {
    // Check if backup file exists
    await stat(backupPath);

    backupLogger.warn("Starting database restore", { backupFileName });

    return new Promise((resolve, _reject) => {
      const args = [
        "--host",
        BACKUP_CONFIG.database.host,
        "--port",
        BACKUP_CONFIG.database.port,
        "--username",
        BACKUP_CONFIG.database.username,
        "--no-password",
        "--clean", // Drop existing objects before recreating
        "--if-exists", // Don't error if objects don't exist
        "--verbose",
        "--dbname",
        BACKUP_CONFIG.database.database,
      ];

      const env = {
        ...process.env,
        PGPASSWORD: BACKUP_CONFIG.database.password,
      };

      let restoreCommand: string;
      let inputStream: NodeJS.ReadableStream;

      if (backupFileName.endsWith(".dump")) {
        // Custom format backup - use pg_restore
        restoreCommand = "pg_restore";
        args.push(backupPath);
        inputStream = process.stdin; // Not used for pg_restore
      } else {
        // SQL backup - use psql
        restoreCommand = "psql";

        if (backupFileName.endsWith(".gz")) {
          // Compressed SQL file
          const gzipStream = createReadStream(backupPath).pipe(
            createGunzip(),
          );
          inputStream = gzipStream;
        } else {
          // Uncompressed SQL file
          inputStream = createReadStream(backupPath);
        }
      }

      const restoreProcess = spawn(restoreCommand, args, { env });

      if (restoreCommand === "psql") {
        inputStream.pipe(restoreProcess.stdin);
      }

      let errorOutput = "";

      restoreProcess.stderr.on("data", (data) => {
        const message = data.toString();
        if (message.includes("ERROR") || message.includes("FATAL")) {
          errorOutput += message;
        }
        backupLogger.debug("Restore output", { message: message.trim() });
      });

      restoreProcess.on("close", (code) => {
        if (code === 0) {
          backupLogger.info("Database restore completed successfully", {
            backupFileName,
          });
          logBusinessEvent(
            "database_restore_completed",
            "system",
            "backup-service",
            { backupFileName },
          );
          resolve(true);
        } else {
          backupLogger.error("Database restore failed", {
            code,
            error: errorOutput,
            backupFileName,
          });
          resolve(false);
        }
      });

      restoreProcess.on("error", (error) => {
        backupLogger.error("Restore process error", { error, backupFileName });
        resolve(false);
      });
    });
  } catch (error) {
    backupLogger.error("Failed to restore from backup", {
      error,
      backupFileName,
    });
    return false;
  }
};

// Schedule automatic backups
export const scheduleBackups = () => {
  backupLogger.info("Scheduling automatic backups", {
    schedule: "Daily at 1:00 AM",
    retention: BACKUP_CONFIG.retention,
  });

  const runDailyBackup = () => {
    const now = new Date();
    const targetTime = new Date();
    targetTime.setHours(1, 0, 0, 0); // 1:00 AM

    // If 1:00 AM has passed today, schedule for tomorrow
    if (now > targetTime) {
      targetTime.setDate(targetTime.getDate() + 1);
    }

    const timeUntilBackup = targetTime.getTime() - now.getTime();

    setTimeout(async () => {
      try {
        backupLogger.info("Running scheduled backup");

        // Create full backup
        const result = await createFullBackup();

        if (result.success) {
          // Cleanup old backups
          await cleanupOldBackups();
        }

        // Schedule next backup
        setInterval(
          async () => {
            try {
              backupLogger.info("Running scheduled backup");
              const scheduledResult = await createFullBackup();

              if (scheduledResult.success) {
                await cleanupOldBackups();
              }
            } catch (error) {
              backupLogger.error("Scheduled backup failed", { error });
            }
          },
          24 * 60 * 60 * 1000,
        ); // Every 24 hours
      } catch (error) {
        backupLogger.error("Initial scheduled backup failed", { error });
      }
    }, timeUntilBackup);

    backupLogger.info("Next backup scheduled", {
      scheduledTime: targetTime.toISOString(),
      timeUntilBackup: Math.round(timeUntilBackup / 1000 / 60), // minutes
    });
  };

  runDailyBackup();
};

// Get backup configuration and status
export const getBackupStatus = async () => {
  try {
    const backups = await listBackups();
    const lastBackup = backups[0]; // Newest backup

    return {
      config: {
        backupDir: BACKUP_CONFIG.backupDir,
        retention: BACKUP_CONFIG.retention,
        compression: BACKUP_CONFIG.compression,
      },
      status: {
        totalBackups: backups.length,
        lastBackup: lastBackup
          ? {
              fileName: lastBackup.fileName,
              createdAt: lastBackup.createdAt,
              fileSize: lastBackup.fileSize,
              type: lastBackup.type,
            }
          : null,
        totalSize: backups.reduce((sum, backup) => sum + backup.fileSize, 0),
      },
      backups: backups.slice(0, 10), // Last 10 backups
    };
  } catch (error) {
    backupLogger.error("Failed to get backup status", { error });
    throw error;
  }
};

export default {
  createFullBackup,
  createSchemaBackup,
  createDataBackup,
  createCustomBackup,
  listBackups,
  cleanupOldBackups,
  restoreFromBackup,
  scheduleBackups,
  getBackupStatus,
};
