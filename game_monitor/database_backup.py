"""
Database Backup and Recovery System for Game Monitor
Enterprise-grade backup, verification, and recovery capabilities.
"""

import sqlite3
import threading
import time
import json
import shutil
import gzip
import hashlib
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
import tempfile
import os

from .advanced_logger import get_logger
from .error_tracker import ErrorTracker


class BackupType:
    """Backup type constants"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


@dataclass
class BackupMetadata:
    """Backup metadata information"""
    backup_id: str
    backup_type: str
    source_path: str
    backup_path: str
    created_at: datetime
    file_size_bytes: int
    compressed_size_bytes: Optional[int]
    verification_hash: str
    database_version: str
    table_counts: Dict[str, int]
    integrity_verified: bool
    compression_ratio: float
    backup_duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class BackupConfig:
    """Backup configuration"""
    
    def __init__(self):
        self.backup_directory = Path("data/backups")
        self.max_backups = 50  # Keep last 50 backups
        self.compression_enabled = True
        self.verification_enabled = True
        self.incremental_enabled = False  # Future feature
        
        # Backup schedule
        self.auto_backup_enabled = True
        self.backup_interval_hours = 6
        self.cleanup_old_backups = True
        self.cleanup_after_days = 30
        
        # Performance settings
        self.backup_timeout_seconds = 300  # 5 minutes
        self.verification_timeout_seconds = 60
        
        # Create backup directory
        self.backup_directory.mkdir(parents=True, exist_ok=True)


class BackupManager:
    """Comprehensive backup and recovery management"""
    
    def __init__(self, database_path: str, config: Optional[BackupConfig] = None):
        self.database_path = Path(database_path)
        self.config = config or BackupConfig()
        
        # Logging
        self.logger = get_logger('database_backup')
        self.error_tracker = ErrorTracker()
        
        # State management
        self._backup_lock = threading.RLock()
        self._backup_in_progress = False
        self._recovery_in_progress = False
        
        # Backup history
        self._backup_history = deque(maxlen=1000)
        self._backup_registry = {}  # backup_id -> BackupMetadata
        
        # Auto-backup thread
        self._auto_backup_active = True
        if self.config.auto_backup_enabled:
            self._start_auto_backup()
        
        # Load existing backup registry
        self._load_backup_registry()
        
        self.logger.info(
            f"Backup manager initialized for {self.database_path}",
            extra_data={
                'backup_directory': str(self.config.backup_directory),
                'max_backups': self.config.max_backups,
                'auto_backup_enabled': self.config.auto_backup_enabled
            }
        )
    
    def _load_backup_registry(self):
        """Load backup registry from disk"""
        registry_path = self.config.backup_directory / "backup_registry.json"
        
        try:
            if registry_path.exists():
                with open(registry_path, 'r') as f:
                    registry_data = json.load(f)
                    
                self._backup_registry = {
                    backup_id: BackupMetadata.from_dict(data)
                    for backup_id, data in registry_data.items()
                }
                
                self.logger.info(f"Loaded {len(self._backup_registry)} backup records from registry")
        
        except Exception as e:
            self.logger.error(f"Failed to load backup registry: {e}")
            self.error_tracker.record_error('database_backup', 'load_registry', e)
    
    def _save_backup_registry(self):
        """Save backup registry to disk"""
        registry_path = self.config.backup_directory / "backup_registry.json"
        
        try:
            registry_data = {
                backup_id: metadata.to_dict()
                for backup_id, metadata in self._backup_registry.items()
            }
            
            # Atomic write using temporary file
            temp_path = registry_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(registry_data, f, indent=2)
            
            temp_path.replace(registry_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save backup registry: {e}")
            self.error_tracker.record_error('database_backup', 'save_registry', e)
    
    def create_backup(self, backup_type: str = BackupType.FULL,
                     description: Optional[str] = None) -> Optional[str]:
        """Create database backup with comprehensive verification"""
        
        if self._backup_in_progress:
            self.logger.warning("Backup already in progress, skipping")
            return None
        
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self.logger.operation_context('database_backup', 'create_backup'):
            try:
                with self._backup_lock:
                    self._backup_in_progress = True
                
                start_time = time.time()
                
                # Validate source database
                if not self.database_path.exists():
                    raise FileNotFoundError(f"Source database not found: {self.database_path}")
                
                self.logger.info(
                    f"Starting {backup_type} backup: {backup_id}",
                    extra_data={
                        'backup_id': backup_id,
                        'backup_type': backup_type,
                        'source_path': str(self.database_path),
                        'description': description
                    }
                )
                
                # Create backup file path
                backup_filename = f"{backup_id}.db"
                if self.config.compression_enabled:
                    backup_filename += ".gz"
                
                backup_path = self.config.backup_directory / backup_filename
                
                # Perform backup
                original_size, compressed_size = self._perform_backup(
                    self.database_path, backup_path
                )
                
                # Get database metadata
                table_counts = self._get_table_counts()
                database_version = self._get_database_version()
                
                # Calculate verification hash
                verification_hash = self._calculate_file_hash(backup_path)
                
                # Verify backup integrity
                integrity_verified = False
                if self.config.verification_enabled:
                    integrity_verified = self._verify_backup_integrity(backup_path)
                
                backup_duration = time.time() - start_time
                compression_ratio = compressed_size / original_size if compressed_size else 1.0
                
                # Create metadata
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    backup_type=backup_type,
                    source_path=str(self.database_path),
                    backup_path=str(backup_path),
                    created_at=datetime.now(),
                    file_size_bytes=original_size,
                    compressed_size_bytes=compressed_size,
                    verification_hash=verification_hash,
                    database_version=database_version,
                    table_counts=table_counts,
                    integrity_verified=integrity_verified,
                    compression_ratio=compression_ratio,
                    backup_duration_seconds=backup_duration
                )
                
                # Store metadata
                self._backup_registry[backup_id] = metadata
                self._backup_history.append(metadata)
                self._save_backup_registry()
                
                self.logger.info(
                    f"Backup completed successfully: {backup_id}",
                    extra_data={
                        'backup_id': backup_id,
                        'file_size_mb': original_size / (1024 * 1024),
                        'compressed_size_mb': (compressed_size / (1024 * 1024)) if compressed_size else None,
                        'compression_ratio': compression_ratio,
                        'duration_seconds': backup_duration,
                        'integrity_verified': integrity_verified
                    }
                )
                
                # Clean up old backups
                if self.config.cleanup_old_backups:
                    self._cleanup_old_backups()
                
                return backup_id
                
            except Exception as e:
                self.logger.error(f"Backup creation failed: {e}")
                self.error_tracker.record_error(
                    'database_backup', 'create_backup', e,
                    context={'backup_id': backup_id, 'backup_type': backup_type}
                )
                return None
            
            finally:
                with self._backup_lock:
                    self._backup_in_progress = False
    
    def _perform_backup(self, source_path: Path, backup_path: Path) -> tuple[int, Optional[int]]:
        """Perform the actual backup operation"""
        
        # Get original file size
        original_size = source_path.stat().st_size
        
        if self.config.compression_enabled:
            # Compressed backup
            with open(source_path, 'rb') as source_file:
                with gzip.open(backup_path, 'wb') as backup_file:
                    shutil.copyfileobj(source_file, backup_file)
            
            compressed_size = backup_path.stat().st_size
            return original_size, compressed_size
        else:
            # Uncompressed backup
            shutil.copy2(source_path, backup_path)
            return original_size, None
    
    def _get_table_counts(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        try:
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
            
            conn.close()
            return table_counts
            
        except Exception as e:
            self.logger.warning(f"Failed to get table counts: {e}")
            return {}
    
    def _get_database_version(self) -> str:
        """Get database version/schema version"""
        try:
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()
            
            # Try to get user version
            cursor.execute("PRAGMA user_version")
            user_version = cursor.fetchone()[0]
            
            # Get SQLite version
            cursor.execute("SELECT sqlite_version()")
            sqlite_version = cursor.fetchone()[0]
            
            conn.close()
            
            return f"sqlite_{sqlite_version}_user_{user_version}"
            
        except Exception as e:
            self.logger.warning(f"Failed to get database version: {e}")
            return "unknown"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of backup file"""
        try:
            hash_sha256 = hashlib.sha256()
            
            if file_path.suffix == '.gz':
                # For compressed files, hash the compressed content
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
            else:
                # For uncompressed files
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
            
            return hash_sha256.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to calculate file hash: {e}")
            return ""
    
    def _verify_backup_integrity(self, backup_path: Path) -> bool:
        """Verify backup integrity by attempting to open and query"""
        try:
            # Extract to temporary file if compressed
            if backup_path.suffix == '.gz':
                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                
                with gzip.open(backup_path, 'rb') as compressed_file:
                    with open(temp_path, 'wb') as extracted_file:
                        shutil.copyfileobj(compressed_file, extracted_file)
                
                test_db_path = temp_path
            else:
                test_db_path = backup_path
            
            # Test database connection and basic queries
            conn = sqlite3.connect(str(test_db_path))
            cursor = conn.cursor()
            
            # Test basic operations
            cursor.execute("PRAGMA integrity_check(10)")
            integrity_results = cursor.fetchall()
            
            # Check if all results are 'ok'
            integrity_ok = all(row[0] == 'ok' for row in integrity_results)
            
            # Test a simple query
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
            cursor.fetchone()  # Just verify we can fetch
            
            conn.close()
            
            # Clean up temporary file
            if backup_path.suffix == '.gz' and test_db_path.exists():
                test_db_path.unlink()
            
            return integrity_ok
            
        except Exception as e:
            self.logger.error(f"Backup integrity verification failed: {e}")
            return False
    
    def restore_backup(self, backup_id: str, target_path: Optional[str] = None,
                      verify_before_restore: bool = True) -> bool:
        """Restore database from backup"""
        
        if self._recovery_in_progress:
            self.logger.error("Recovery already in progress")
            return False
        
        if backup_id not in self._backup_registry:
            self.logger.error(f"Backup not found: {backup_id}")
            return False
        
        with self.logger.operation_context('database_backup', 'restore_backup'):
            try:
                with self._backup_lock:
                    self._recovery_in_progress = True
                
                metadata = self._backup_registry[backup_id]
                backup_path = Path(metadata.backup_path)
                
                if not backup_path.exists():
                    raise FileNotFoundError(f"Backup file not found: {backup_path}")
                
                target_path = Path(target_path) if target_path else self.database_path
                
                self.logger.info(
                    f"Starting backup restore: {backup_id}",
                    extra_data={
                        'backup_id': backup_id,
                        'backup_path': str(backup_path),
                        'target_path': str(target_path),
                        'backup_created': metadata.created_at.isoformat()
                    }
                )
                
                # Verify backup integrity before restore
                if verify_before_restore:
                    if not self._verify_backup_integrity(backup_path):
                        raise RuntimeError("Backup integrity verification failed")
                
                # Create backup of current database if it exists
                if target_path.exists():
                    backup_current_path = target_path.with_suffix(f".pre_restore_{int(time.time())}")
                    shutil.copy2(target_path, backup_current_path)
                    self.logger.info(f"Current database backed up to: {backup_current_path}")
                
                # Perform restore
                if backup_path.suffix == '.gz':
                    # Decompress and restore
                    with gzip.open(backup_path, 'rb') as compressed_file:
                        with open(target_path, 'wb') as target_file:
                            shutil.copyfileobj(compressed_file, target_file)
                else:
                    # Direct copy
                    shutil.copy2(backup_path, target_path)
                
                # Verify restored database
                restored_conn = sqlite3.connect(str(target_path))
                cursor = restored_conn.cursor()
                
                # Test basic operations
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                if integrity_result != 'ok':
                    restored_conn.close()
                    raise RuntimeError(f"Restored database failed integrity check: {integrity_result}")
                
                # Verify table counts match (if available)
                if metadata.table_counts:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    current_tables = [row[0] for row in cursor.fetchall()]
                    
                    for table in current_tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        current_count = cursor.fetchone()[0]
                        expected_count = metadata.table_counts.get(table)
                        
                        if expected_count is not None and current_count != expected_count:
                            self.logger.warning(
                                f"Table count mismatch for {table}: expected {expected_count}, got {current_count}"
                            )
                
                restored_conn.close()
                
                self.logger.info(
                    f"Backup restore completed successfully: {backup_id}",
                    extra_data={
                        'backup_id': backup_id,
                        'target_path': str(target_path),
                        'restore_verified': True
                    }
                )
                
                return True
                
            except Exception as e:
                self.logger.error(f"Backup restore failed: {e}")
                self.error_tracker.record_error(
                    'database_backup', 'restore_backup', e,
                    context={'backup_id': backup_id, 'target_path': str(target_path) if target_path else None}
                )
                return False
            
            finally:
                with self._backup_lock:
                    self._recovery_in_progress = False
    
    def list_backups(self, limit: Optional[int] = None) -> List[BackupMetadata]:
        """List available backups"""
        backups = sorted(
            self._backup_registry.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        
        if limit:
            backups = backups[:limit]
        
        return backups
    
    def get_backup_info(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get detailed backup information"""
        return self._backup_registry.get(backup_id)
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete backup and its metadata"""
        
        if backup_id not in self._backup_registry:
            self.logger.error(f"Backup not found: {backup_id}")
            return False
        
        try:
            metadata = self._backup_registry[backup_id]
            backup_path = Path(metadata.backup_path)
            
            # Delete backup file
            if backup_path.exists():
                backup_path.unlink()
                self.logger.info(f"Deleted backup file: {backup_path}")
            
            # Remove from registry
            del self._backup_registry[backup_id]
            self._save_backup_registry()
            
            self.logger.info(f"Backup deleted: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            self.error_tracker.record_error(
                'database_backup', 'delete_backup', e,
                context={'backup_id': backup_id}
            )
            return False
    
    def _cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        try:
            # Clean up by count (keep max_backups)
            if len(self._backup_registry) > self.config.max_backups:
                # Get backups sorted by creation time
                sorted_backups = sorted(
                    self._backup_registry.items(),
                    key=lambda x: x[1].created_at
                )
                
                # Delete oldest backups
                excess_count = len(self._backup_registry) - self.config.max_backups
                for backup_id, _ in sorted_backups[:excess_count]:
                    self.delete_backup(backup_id)
                    self.logger.info(f"Cleaned up old backup: {backup_id}")
            
            # Clean up by age (older than cleanup_after_days)
            cutoff_date = datetime.now() - timedelta(days=self.config.cleanup_after_days)
            old_backups = [
                backup_id for backup_id, metadata in self._backup_registry.items()
                if metadata.created_at < cutoff_date
            ]
            
            for backup_id in old_backups:
                self.delete_backup(backup_id)
                self.logger.info(f"Cleaned up aged backup: {backup_id}")
        
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            self.error_tracker.record_error('database_backup', 'cleanup_backups', e)
    
    def _start_auto_backup(self):
        """Start automatic backup thread"""
        
        def auto_backup_loop():
            last_backup_time = time.time()
            
            while self._auto_backup_active:
                try:
                    current_time = time.time()
                    
                    if (current_time - last_backup_time) >= (self.config.backup_interval_hours * 3600):
                        self.logger.info("Starting scheduled automatic backup")
                        
                        backup_id = self.create_backup(
                            backup_type=BackupType.FULL,
                            description="Automatic scheduled backup"
                        )
                        
                        if backup_id:
                            last_backup_time = current_time
                            self.logger.info(f"Automatic backup completed: {backup_id}")
                        else:
                            self.logger.error("Automatic backup failed")
                    
                    time.sleep(300)  # Check every 5 minutes
                    
                except Exception as e:
                    self.logger.error(f"Error in auto-backup loop: {e}")
                    time.sleep(300)
        
        self._auto_backup_thread = threading.Thread(target=auto_backup_loop, daemon=True)
        self._auto_backup_thread.start()
        
        self.logger.info("Automatic backup thread started")
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get comprehensive backup statistics"""
        if not self._backup_registry:
            return {}
        
        backups = list(self._backup_registry.values())
        
        total_backups = len(backups)
        total_size_bytes = sum(b.file_size_bytes for b in backups)
        total_compressed_size_bytes = sum(
            b.compressed_size_bytes for b in backups if b.compressed_size_bytes
        )
        
        avg_compression_ratio = statistics.mean(
            [b.compression_ratio for b in backups if b.compression_ratio < 1.0]
        ) if any(b.compression_ratio < 1.0 for b in backups) else 1.0
        
        verified_backups = sum(1 for b in backups if b.integrity_verified)
        
        return {
            'total_backups': total_backups,
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'total_compressed_size_mb': total_compressed_size_bytes / (1024 * 1024) if total_compressed_size_bytes else 0,
            'average_compression_ratio': avg_compression_ratio,
            'verified_backups': verified_backups,
            'verification_rate': verified_backups / total_backups if total_backups > 0 else 0,
            'oldest_backup': min(b.created_at for b in backups).isoformat(),
            'newest_backup': max(b.created_at for b in backups).isoformat(),
            'auto_backup_enabled': self.config.auto_backup_enabled,
            'backup_interval_hours': self.config.backup_interval_hours
        }
    
    def shutdown(self):
        """Shutdown backup manager"""
        self.logger.info("Shutting down backup manager")
        
        self._auto_backup_active = False
        
        # Wait for auto-backup thread
        if hasattr(self, '_auto_backup_thread') and self._auto_backup_thread.is_alive():
            self._auto_backup_thread.join(timeout=10)
        
        # Save final registry
        self._save_backup_registry()
        
        self.logger.info("Backup manager shutdown complete")