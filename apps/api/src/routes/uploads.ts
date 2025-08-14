import { Elysia, t } from 'elysia';
import { join } from 'path';
import { mkdir, writeFile, unlink, stat } from 'fs/promises';
import { db, uploads, eq } from '@yuyu/db';
import { requireAuth } from '../middleware/auth';
import { ValidationError, NotFoundError } from '../middleware/error';
import { generateRandomString, validateFileType, validateFileSize } from '@yuyu/shared';

// File upload configuration
const UPLOAD_DIR = process.env.UPLOAD_DIR || 'uploads';
const MAX_FILE_SIZE = parseInt(process.env.MAX_FILE_SIZE || '10485760'); // 10MB
const ALLOWED_FILE_TYPES = (process.env.ALLOWED_FILE_TYPES || 'image/jpeg,image/jpg,image/png,image/gif,image/webp').split(',');

// Ensure upload directory exists
async function ensureUploadDir() {
  try {
    await stat(UPLOAD_DIR);
  } catch {
    await mkdir(UPLOAD_DIR, { recursive: true });
  }
}

// Generate unique filename
function generateFilename(originalName: string): string {
  const extension = originalName.split('.').pop() || '';
  const timestamp = Date.now();
  const random = generateRandomString(8);
  return `${timestamp}_${random}.${extension}`;
}

// Get file URL
function getFileUrl(filename: string): string {
  const baseUrl = process.env.PUBLIC_API_URL || 'http://localhost:3001';
  return `${baseUrl}/static/${filename}`;
}

export const uploadRoutes = new Elysia({ prefix: '/uploads' })
  .use(requireAuth)

  // Upload single file
  .post('/', async ({ body, user, set }) => {
    await ensureUploadDir();

    const file = (body as any).file as File;
    
    if (!file) {
      throw new ValidationError('No file provided');
    }

    // Validate file type
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      throw new ValidationError(`File type ${file.type} is not allowed`);
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      throw new ValidationError(`File size exceeds limit of ${MAX_FILE_SIZE} bytes`);
    }

    // Generate filename and path
    const filename = generateFilename(file.name);
    const filePath = join(UPLOAD_DIR, filename);
    const fileUrl = getFileUrl(filename);

    try {
      // Save file
      const arrayBuffer = await file.arrayBuffer();
      await writeFile(filePath, new Uint8Array(arrayBuffer));

      // Save upload record
      const [uploadRecord] = await db.insert(uploads).values({
        originalName: file.name,
        filename,
        mimetype: file.type,
        size: file.size,
        path: filePath,
        url: fileUrl,
        uploadedBy: user.id,
      }).returning();

      set.status = 201;
      return {
        success: true,
        message: 'File uploaded successfully',
        data: { upload: uploadRecord },
      };
    } catch (error) {
      // Clean up file if database save fails
      try {
        await unlink(filePath);
      } catch {}
      
      throw new Error('Failed to save file');
    }
  }, {
    body: t.Object({
      file: t.File(),
    }),
    detail: {
      summary: 'Upload file',
      tags: ['Uploads'],
    },
  })

  // Upload multiple files
  .post('/multiple', async ({ body, user, set }) => {
    await ensureUploadDir();

    const files = (body as any).files as File[];
    
    if (!files || !Array.isArray(files) || files.length === 0) {
      throw new ValidationError('No files provided');
    }

    if (files.length > 10) {
      throw new ValidationError('Maximum 10 files allowed per upload');
    }

    const uploadResults = [];
    const failedUploads = [];

    for (const file of files) {
      try {
        // Validate file type
        if (!ALLOWED_FILE_TYPES.includes(file.type)) {
          failedUploads.push({
            filename: file.name,
            error: `File type ${file.type} is not allowed`,
          });
          continue;
        }

        // Validate file size
        if (file.size > MAX_FILE_SIZE) {
          failedUploads.push({
            filename: file.name,
            error: `File size exceeds limit of ${MAX_FILE_SIZE} bytes`,
          });
          continue;
        }

        // Generate filename and path
        const filename = generateFilename(file.name);
        const filePath = join(UPLOAD_DIR, filename);
        const fileUrl = getFileUrl(filename);

        // Save file
        const arrayBuffer = await file.arrayBuffer();
        await writeFile(filePath, new Uint8Array(arrayBuffer));

        // Save upload record
        const [uploadRecord] = await db.insert(uploads).values({
          originalName: file.name,
          filename,
          mimetype: file.type,
          size: file.size,
          path: filePath,
          url: fileUrl,
          uploadedBy: user.id,
        }).returning();

        uploadResults.push(uploadRecord);
      } catch (error) {
        failedUploads.push({
          filename: file.name,
          error: 'Failed to save file',
        });
      }
    }

    set.status = 201;
    return {
      success: true,
      message: `${uploadResults.length} files uploaded successfully`,
      data: { 
        uploads: uploadResults,
        failed: failedUploads,
      },
    };
  }, {
    body: t.Object({
      files: t.Array(t.File()),
    }),
    detail: {
      summary: 'Upload multiple files',
      tags: ['Uploads'],
    },
  })

  // Get user uploads
  .get('/', async ({ user, query }) => {
    const page = parseInt(query.page) || 1;
    const limit = parseInt(query.limit) || 20;
    const offset = (page - 1) * limit;

    const userUploads = await db.query.uploads.findMany({
      where: eq(uploads.uploadedBy, user.id),
      orderBy: db.desc(uploads.createdAt),
      limit,
      offset,
    });

    // Get total count
    const [{ count }] = await db
      .select({ count: db.sql<number>`count(*)` })
      .from(uploads)
      .where(eq(uploads.uploadedBy, user.id));

    const totalPages = Math.ceil(count / limit);

    return {
      success: true,
      data: userUploads,
      pagination: {
        page,
        limit,
        total: count,
        totalPages,
        hasNext: page < totalPages,
        hasPrev: page > 1,
      },
    };
  }, {
    query: t.Object({
      page: t.Optional(t.String()),
      limit: t.Optional(t.String()),
    }),
    detail: {
      summary: 'Get user uploads',
      tags: ['Uploads'],
    },
  })

  // Get upload by ID
  .get('/:id', async ({ params: { id }, user }) => {
    const upload = await db.query.uploads.findFirst({
      where: eq(uploads.id, id),
      with: {
        uploadedBy: {
          columns: {
            name: true,
          },
        },
      },
    });

    if (!upload) {
      throw new NotFoundError('Upload not found');
    }

    // Only allow access to own uploads (unless admin)
    if (upload.uploadedBy !== user.id && user.role !== 'admin') {
      throw new NotFoundError('Upload not found');
    }

    return {
      success: true,
      data: { upload },
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Get upload by ID',
      tags: ['Uploads'],
    },
  })

  // Delete upload
  .delete('/:id', async ({ params: { id }, user }) => {
    const upload = await db.query.uploads.findFirst({
      where: eq(uploads.id, id),
    });

    if (!upload) {
      throw new NotFoundError('Upload not found');
    }

    // Only allow deletion of own uploads (unless admin)
    if (upload.uploadedBy !== user.id && user.role !== 'admin') {
      throw new NotFoundError('Upload not found');
    }

    try {
      // Delete file from filesystem
      await unlink(upload.path);
    } catch (error) {
      console.error('Failed to delete file from filesystem:', error);
      // Continue with database deletion even if file deletion fails
    }

    // Delete upload record
    await db.delete(uploads).where(eq(uploads.id, id));

    return {
      success: true,
      message: 'Upload deleted successfully',
    };
  }, {
    params: t.Object({
      id: t.String(),
    }),
    detail: {
      summary: 'Delete upload',
      tags: ['Uploads'],
    },
  })

  // Get upload configuration
  .get('/config', async () => {
    return {
      success: true,
      data: {
        maxFileSize: MAX_FILE_SIZE,
        allowedFileTypes: ALLOWED_FILE_TYPES,
        maxFiles: 10,
      },
    };
  }, {
    detail: {
      summary: 'Get upload configuration',
      tags: ['Uploads'],
    },
  });