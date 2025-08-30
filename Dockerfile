# Game Monitor System - Production Docker Image
# Multi-stage build for optimized production deployment

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    GAME_MONITOR_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Tesseract OCR with language packs
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # System utilities
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . /app/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/validation && \
    chown -R appuser:appuser /app

# Verify Tesseract installation
RUN tesseract --version && \
    tesseract --list-langs

# Install the application
RUN pip install -e .

# Initialize the application
RUN python setup_database.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "
import sys
import os
sys.path.insert(0, '/app')
try:
    from game_monitor.database_manager import DatabaseManager
    db = DatabaseManager()
    db.get_total_trades_count()
    print('Health check passed')
    exit(0)
except Exception as e:
    print(f'Health check failed: {e}')
    exit(1)
"

# Switch to non-root user
USER appuser

# Expose port (if needed for future web interface)
EXPOSE 8080

# Volume mounts for persistent data
VOLUME ["/app/data", "/app/logs", "/app/config"]

# Default command
CMD ["python", "main.py"]

# Additional build arguments and labels
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="game-monitor" \
      org.label-schema.description="High-performance game item monitoring system" \
      org.label-schema.url="https://github.com/game-monitor/game-monitor" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/game-monitor/game-monitor" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0" \
      maintainer="Game Monitor Development Team"

# Multi-architecture support metadata
LABEL org.opencontainers.image.title="Game Monitor System" \
      org.opencontainers.image.description="High-performance game item monitoring with OCR and database integration" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/game-monitor/game-monitor"