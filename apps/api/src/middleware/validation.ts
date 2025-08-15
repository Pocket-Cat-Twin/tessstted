import { Elysia } from "elysia";

// File validation configuration
const FILE_VALIDATION_CONFIG = {
  // Maximum file sizes in bytes
  maxSizes: {
    image: 5 * 1024 * 1024, // 5MB for images
    document: 10 * 1024 * 1024, // 10MB for documents
    avatar: 2 * 1024 * 1024, // 2MB for avatars
    general: 15 * 1024 * 1024, // 15MB for general files
  },

  // Allowed MIME types
  allowedTypes: {
    image: ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"],
    document: [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
      "text/csv",
    ],
    avatar: ["image/jpeg", "image/jpg", "image/png", "image/webp"],
    general: [
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/webp",
      "image/gif",
      "application/pdf",
      "text/plain",
    ],
  },

  // File extensions mapping
  extensions: {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/gif": [".gif"],
    "application/pdf": [".pdf"],
    "text/plain": [".txt"],
    "text/csv": [".csv"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
      ".docx",
    ],
  },
};

// File validation types
export type FileValidationType = "image" | "document" | "avatar" | "general";

// File validation result
export interface FileValidationResult {
  isValid: boolean;
  errors: string[];
  file?: {
    name: string;
    size: number;
    type: string;
    extension: string;
  };
}

// Validate file size
function validateFileSize(file: File, maxSize: number): string | null {
  if (file.size > maxSize) {
    const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(1);
    const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
    return `File size (${fileSizeMB}MB) exceeds maximum allowed size (${maxSizeMB}MB)`;
  }
  return null;
}

// Validate MIME type
function validateMimeType(file: File, allowedTypes: string[]): string | null {
  if (!allowedTypes.includes(file.type)) {
    return `File type '${file.type}' is not allowed. Allowed types: ${allowedTypes.join(", ")}`;
  }
  return null;
}

// Validate file extension
function validateFileExtension(
  fileName: string,
  mimeType: string,
): string | null {
  const extensions = FILE_VALIDATION_CONFIG.extensions[mimeType];
  if (!extensions) {
    return `Unknown MIME type: ${mimeType}`;
  }

  const fileExtension = fileName
    .toLowerCase()
    .substring(fileName.lastIndexOf("."));
  if (!extensions.some((ext) => ext.toLowerCase() === fileExtension)) {
    return `File extension '${fileExtension}' does not match MIME type '${mimeType}'. Expected: ${extensions.join(", ")}`;
  }

  return null;
}

// Check for potentially dangerous file names
function validateFileName(fileName: string): string | null {
  // Check for null bytes, path traversal, and other dangerous patterns
  const dangerousPatterns = [
    /\0/, // null byte
    /\.\.\//, // path traversal
    /^\./, // hidden files
    /[<>:"|?*]/, // Windows forbidden characters
    /^\s/, // leading whitespace
    /\s$/, // trailing whitespace
    /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)/i, // Windows reserved names
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(fileName)) {
      return `File name contains dangerous characters or patterns: ${fileName}`;
    }
  }

  if (fileName.length > 255) {
    return `File name too long (${fileName.length} characters). Maximum 255 characters allowed.`;
  }

  return null;
}

// Main file validation function
export function validateFile(
  file: File,
  validationType: FileValidationType,
): FileValidationResult {
  const errors: string[] = [];

  // Get validation config
  const maxSize = FILE_VALIDATION_CONFIG.maxSizes[validationType];
  const allowedTypes = FILE_VALIDATION_CONFIG.allowedTypes[validationType];

  // Validate file name
  const fileNameError = validateFileName(file.name);
  if (fileNameError) errors.push(fileNameError);

  // Validate file size
  const sizeError = validateFileSize(file, maxSize);
  if (sizeError) errors.push(sizeError);

  // Validate MIME type
  const mimeError = validateMimeType(file, allowedTypes);
  if (mimeError) errors.push(mimeError);

  // Validate file extension matches MIME type
  const extensionError = validateFileExtension(file.name, file.type);
  if (extensionError) errors.push(extensionError);

  return {
    isValid: errors.length === 0,
    errors,
    file: {
      name: file.name,
      size: file.size,
      type: file.type,
      extension: file.name.substring(file.name.lastIndexOf(".")),
    },
  };
}

// Middleware factory for file validation
export function createFileValidationMiddleware(
  validationType: FileValidationType,
) {
  return new Elysia({
    name: `fileValidation-${validationType}`,
  }).onBeforeHandle(({ body, set }) => {
    // Check if request contains files
    if (!body || typeof body !== "object") {
      return;
    }

    // Handle both single file and multiple files
    const files: File[] = [];

    // Extract files from body
    for (const [key, value] of Object.entries(body)) {
      if (value instanceof File) {
        files.push(value);
      } else if (Array.isArray(value)) {
        for (const item of value) {
          if (item instanceof File) {
            files.push(item);
          }
        }
      }
    }

    // Validate each file
    const validationErrors: string[] = [];
    for (const file of files) {
      const result = validateFile(file, validationType);
      if (!result.isValid) {
        validationErrors.push(
          `File '${file.name}': ${result.errors.join(", ")}`,
        );
      }
    }

    // Return error if validation failed
    if (validationErrors.length > 0) {
      set.status = 400;
      return {
        success: false,
        error: "FILE_VALIDATION_ERROR",
        message: "File validation failed",
        details: validationErrors,
      };
    }
  });
}

// Pre-configured middleware instances
export const imageValidation = createFileValidationMiddleware("image");
export const documentValidation = createFileValidationMiddleware("document");
export const avatarValidation = createFileValidationMiddleware("avatar");
export const generalFileValidation = createFileValidationMiddleware("general");

// Additional security middleware for uploads
export const uploadSecurityMiddleware = new Elysia({
  name: "uploadSecurity",
}).onBeforeHandle(({ body, set, headers }) => {
  // Check Content-Type header for multipart/form-data
  const contentType = headers["content-type"];
  if (contentType && contentType.includes("multipart/form-data")) {
    // Verify content length is not too large
    const contentLength = parseInt(headers["content-length"] || "0");
    const maxContentLength = 50 * 1024 * 1024; // 50MB total request size

    if (contentLength > maxContentLength) {
      set.status = 413;
      return {
        success: false,
        error: "PAYLOAD_TOO_LARGE",
        message: "Request payload too large",
        maxSize: maxContentLength,
      };
    }
  }

  // Additional security headers for file uploads
  if (body && typeof body === "object") {
    const hasFiles = Object.values(body).some(
      (value) =>
        value instanceof File ||
        (Array.isArray(value) && value.some((item) => item instanceof File)),
    );

    if (hasFiles) {
      // Add security headers for file upload responses
      set.headers["X-Content-Type-Options"] = "nosniff";
      set.headers["X-Frame-Options"] = "DENY";
      set.headers["Referrer-Policy"] = "strict-origin-when-cross-origin";
    }
  }
});

// Virus scanning placeholder (integrate with external service)
export const virusScanMiddleware = new Elysia({
  name: "virusScan",
}).onBeforeHandle(({ body, set }) => {
  // This is a placeholder for virus scanning integration
  // In production, you would integrate with services like:
  // - ClamAV
  // - VirusTotal API
  // - AWS GuardDuty
  // - Azure Defender

  if (process.env.ENABLE_VIRUS_SCAN === "true") {
    // Implement actual virus scanning here
    console.log("Virus scanning would be performed here");
  }
});

// Export configuration for external use
export { FILE_VALIDATION_CONFIG };
