import { Elysia, t } from "elysia";
import { authMiddleware } from "../middleware/auth";
import {
  createFullBackup,
  createSchemaBackup,
  createDataBackup,
  createCustomBackup,
  listBackups,
  cleanupOldBackups,
  restoreFromBackup,
  getBackupStatus,
} from "../services/backup";

export const backupRoutes = new Elysia({ prefix: "/backup" })
  .use(authMiddleware)
  .guard(
    {
      beforeHandle: ({ store, set }) => {
        if (!store.user || store.user.role !== "admin") {
          set.status = 403;
          return {
            success: false,
            error: "INSUFFICIENT_PERMISSIONS",
            message: "Admin access required",
          };
        }
      },
    },
    (app) =>
      app
        // Get backup status and configuration
        .get(
          "/status",
          async () => {
            try {
              const status = await getBackupStatus();

              return {
                success: true,
                data: status,
              };
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_STATUS_ERROR",
                message: "Failed to get backup status",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            detail: {
              tags: ["Backup"],
              summary: "Get backup status",
              description:
                "Returns backup configuration, status, and recent backups",
            },
          },
        )

        // List all backups
        .get(
          "/list",
          async () => {
            try {
              const backups = await listBackups();

              return {
                success: true,
                data: {
                  backups,
                  total: backups.length,
                  totalSize: backups.reduce(
                    (sum, backup) => sum + backup.fileSize,
                    0,
                  ),
                },
              };
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_LIST_ERROR",
                message: "Failed to list backups",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            detail: {
              tags: ["Backup"],
              summary: "List all backups",
              description: "Returns a list of all available backup files",
            },
          },
        )

        // Create full backup
        .post(
          "/create/full",
          async ({ query }) => {
            try {
              const compress = query.compress !== "false";
              const result = await createFullBackup(compress);

              if (result.success) {
                return {
                  success: true,
                  message: "Full backup created successfully",
                  data: result,
                };
              } else {
                return {
                  success: false,
                  error: "BACKUP_CREATE_ERROR",
                  message: "Failed to create full backup",
                  details: result.error,
                };
              }
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_CREATE_ERROR",
                message: "Failed to create full backup",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            query: t.Object({
              compress: t.Optional(t.String()),
            }),
            detail: {
              tags: ["Backup"],
              summary: "Create full backup",
              description:
                "Creates a full database backup including schema and data",
            },
          },
        )

        // Create schema-only backup
        .post(
          "/create/schema",
          async ({ query }) => {
            try {
              const compress = query.compress !== "false";
              const result = await createSchemaBackup(compress);

              if (result.success) {
                return {
                  success: true,
                  message: "Schema backup created successfully",
                  data: result,
                };
              } else {
                return {
                  success: false,
                  error: "BACKUP_CREATE_ERROR",
                  message: "Failed to create schema backup",
                  details: result.error,
                };
              }
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_CREATE_ERROR",
                message: "Failed to create schema backup",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            query: t.Object({
              compress: t.Optional(t.String()),
            }),
            detail: {
              tags: ["Backup"],
              summary: "Create schema backup",
              description:
                "Creates a schema-only backup (table structures, no data)",
            },
          },
        )

        // Create data-only backup
        .post(
          "/create/data",
          async ({ query }) => {
            try {
              const compress = query.compress !== "false";
              const result = await createDataBackup(compress);

              if (result.success) {
                return {
                  success: true,
                  message: "Data backup created successfully",
                  data: result,
                };
              } else {
                return {
                  success: false,
                  error: "BACKUP_CREATE_ERROR",
                  message: "Failed to create data backup",
                  details: result.error,
                };
              }
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_CREATE_ERROR",
                message: "Failed to create data backup",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            query: t.Object({
              compress: t.Optional(t.String()),
            }),
            detail: {
              tags: ["Backup"],
              summary: "Create data backup",
              description: "Creates a data-only backup (table data, no schema)",
            },
          },
        )

        // Create custom format backup
        .post(
          "/create/custom",
          async () => {
            try {
              const result = await createCustomBackup();

              if (result.success) {
                return {
                  success: true,
                  message: "Custom backup created successfully",
                  data: result,
                };
              } else {
                return {
                  success: false,
                  error: "BACKUP_CREATE_ERROR",
                  message: "Failed to create custom backup",
                  details: result.error,
                };
              }
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_CREATE_ERROR",
                message: "Failed to create custom backup",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            detail: {
              tags: ["Backup"],
              summary: "Create custom backup",
              description:
                "Creates a PostgreSQL custom format backup (best for large databases)",
            },
          },
        )

        // Cleanup old backups
        .post(
          "/cleanup",
          async () => {
            try {
              const result = await cleanupOldBackups();

              return {
                success: true,
                message: `Cleanup completed. Deleted ${result.deleted.length} backups, kept ${result.kept.length} backups`,
                data: result,
              };
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_CLEANUP_ERROR",
                message: "Failed to cleanup old backups",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            detail: {
              tags: ["Backup"],
              summary: "Cleanup old backups",
              description:
                "Removes old backup files according to retention policy",
            },
          },
        )

        // Restore from backup (DANGEROUS!)
        .post(
          "/restore/:fileName",
          async ({ params, body }) => {
            try {
              // Additional safety check
              if (
                !body ||
                typeof body !== "object" ||
                !("confirm" in body) ||
                body.confirm !== "YES_I_WANT_TO_RESTORE"
              ) {
                return {
                  success: false,
                  error: "RESTORE_CONFIRMATION_REQUIRED",
                  message:
                    'This operation will overwrite the current database. Send { "confirm": "YES_I_WANT_TO_RESTORE" } to proceed.',
                };
              }

              const result = await restoreFromBackup(params.fileName);

              if (result) {
                return {
                  success: true,
                  message: "Database restore completed successfully",
                  data: {
                    fileName: params.fileName,
                    restoredAt: new Date().toISOString(),
                  },
                };
              } else {
                return {
                  success: false,
                  error: "BACKUP_RESTORE_ERROR",
                  message: "Failed to restore from backup",
                };
              }
            } catch (error) {
              return {
                success: false,
                error: "BACKUP_RESTORE_ERROR",
                message: "Failed to restore from backup",
                details:
                  error instanceof Error ? error.message : "Unknown error",
              };
            }
          },
          {
            params: t.Object({
              fileName: t.String(),
            }),
            body: t.Object({
              confirm: t.String(),
            }),
            detail: {
              tags: ["Backup"],
              summary: "Restore from backup (DANGEROUS)",
              description:
                "Restores database from a backup file. This will overwrite the current database!",
            },
          },
        ),
  );

export default backupRoutes;
