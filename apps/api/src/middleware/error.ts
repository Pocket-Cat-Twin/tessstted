import { Elysia } from 'elysia';
import { ErrorCode } from '@yuyu/shared';
import { logError } from '../services/logger';

export const errorHandler = new Elysia({ name: 'errorHandler' })
  .onError(({ code, error, set, request }) => {
    // Safely get error message and stack
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    // Use structured logging instead of console.error
    if (error instanceof Error) {
      const url = new URL(request.url);
      logError(error, `API Error [${code}]`, {
        code,
        path: url.pathname,
        method: request.method,
      });
    }

    // Handle different error types
    switch (code) {
      case 'VALIDATION':
        set.status = 400;
        return {
          success: false,
          error: ErrorCode.VALIDATION_ERROR,
          message: 'Validation failed',
          details: errorMessage,
        };

      case 'NOT_FOUND':
        set.status = 404;
        return {
          success: false,
          error: ErrorCode.NOT_FOUND_ERROR,
          message: 'Resource not found',
        };

      case 'PARSE':
        set.status = 400;
        return {
          success: false,
          error: ErrorCode.VALIDATION_ERROR,
          message: 'Invalid request format',
        };

      case 'INTERNAL_SERVER_ERROR':
      default:
        // Don't expose internal errors in production
        const isProduction = process.env.NODE_ENV === 'production';
        
        set.status = 500;
        return {
          success: false,
          error: ErrorCode.INTERNAL_ERROR,
          message: isProduction 
            ? 'Internal server error' 
            : errorMessage,
          ...(isProduction ? {} : { stack: errorStack }),
        };
    }
  });

// Custom error classes
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends Error {
  constructor(message: string = 'Resource not found') {
    super(message);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends Error {
  constructor(message: string = 'Unauthorized') {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends Error {
  constructor(message: string = 'Forbidden') {
    super(message);
    this.name = 'ForbiddenError';
  }
}

export class DuplicateError extends Error {
  constructor(message: string = 'Resource already exists') {
    super(message);
    this.name = 'DuplicateError';
  }
}