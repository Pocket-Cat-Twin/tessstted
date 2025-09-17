"""
File utilities for market monitoring system.
Provides file management, backup, and utility functions.
"""

import logging
import shutil
import os
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
import tempfile
import zipfile


class FileUtilsError(Exception):
    """Exception raised for file utility errors."""
    pass


class FileUtils:
    """
    Utility class for file operations in the market monitoring system.
    Provides backup, cleanup, and file management functionality.
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize file utilities.
        
        Args:
            base_path: Base path for relative operations (optional)
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.logger = logging.getLogger(__name__)
    
    def ensure_directory_exists(self, directory_path: Path, create_parents: bool = True) -> bool:
        """
        Ensure directory exists, create if it doesn't.
        
        Args:
            directory_path: Path to directory
            create_parents: Whether to create parent directories
            
        Returns:
            True if directory exists or was created successfully
        """
        try:
            directory_path.mkdir(parents=create_parents, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {directory_path}: {e}")
            return False
    
    def safe_delete_file(self, file_path: Path, backup_before_delete: bool = False) -> bool:
        """
        Safely delete a file with optional backup.
        
        Args:
            file_path: Path to file to delete
            backup_before_delete: Whether to create backup before deletion
            
        Returns:
            True if deletion was successful
        """
        try:
            if not file_path.exists():
                self.logger.debug(f"File does not exist: {file_path}")
                return True
            
            # Create backup if requested
            if backup_before_delete:
                backup_path = self.create_backup_file(file_path)
                if not backup_path:
                    self.logger.warning(f"Failed to create backup for {file_path}")
            
            # Delete the file
            file_path.unlink()
            self.logger.debug(f"Deleted file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def create_backup_file(self, source_path: Path, 
                          backup_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Create backup of a file.
        
        Args:
            source_path: Path to source file
            backup_dir: Directory for backup (optional, uses source dir by default)
            
        Returns:
            Path to backup file or None if failed
        """
        try:
            if not source_path.exists():
                self.logger.error(f"Source file does not exist: {source_path}")
                return None
            
            # Determine backup directory
            if backup_dir is None:
                backup_dir = source_path.parent
            
            self.ensure_directory_exists(backup_dir)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{source_path.stem}_{timestamp}_backup{source_path.suffix}"
            backup_path = backup_dir / backup_filename
            
            # Copy file
            shutil.copy2(source_path, backup_path)
            
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {source_path}: {e}")
            return None
    
    def cleanup_old_backups(self, backup_dir: Path, 
                           pattern: str = "*_backup.*",
                           max_age_days: int = 7,
                           keep_minimum: int = 3) -> int:
        """
        Clean up old backup files.
        
        Args:
            backup_dir: Directory containing backups
            pattern: File pattern to match
            max_age_days: Maximum age of backups to keep
            keep_minimum: Minimum number of backups to keep
            
        Returns:
            Number of files deleted
        """
        try:
            if not backup_dir.exists():
                return 0
            
            # Find backup files
            backup_files = list(backup_dir.glob(pattern))
            if len(backup_files) <= keep_minimum:
                return 0
            
            # Sort by modification time (oldest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Calculate cutoff time
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            cutoff_timestamp = cutoff_time.timestamp()
            
            deleted_count = 0
            files_to_keep = backup_files[-keep_minimum:]  # Keep newest files
            
            for backup_file in backup_files:
                if backup_file in files_to_keep:
                    continue
                
                if backup_file.stat().st_mtime < cutoff_timestamp:
                    try:
                        backup_file.unlink()
                        deleted_count += 1
                        self.logger.debug(f"Deleted old backup: {backup_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to delete backup {backup_file}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old backup files")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
            return 0
    
    def get_directory_size(self, directory_path: Path, 
                          include_subdirs: bool = True) -> int:
        """
        Get total size of directory in bytes.
        
        Args:
            directory_path: Path to directory
            include_subdirs: Whether to include subdirectories
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        
        try:
            if not directory_path.exists():
                return 0
            
            if include_subdirs:
                for file_path in directory_path.rglob('*'):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except (OSError, FileNotFoundError):
                            continue
            else:
                for file_path in directory_path.iterdir():
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except (OSError, FileNotFoundError):
                            continue
            
            return total_size
            
        except Exception as e:
            self.logger.error(f"Failed to get directory size for {directory_path}: {e}")
            return 0
    
    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive file information.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information or None if failed
        """
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            
            file_info = {
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'size_mb': stat.st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'is_file': file_path.is_file(),
                'is_directory': file_path.is_dir(),
                'permissions': oct(stat.st_mode)[-3:],
                'extension': file_path.suffix.lower()
            }
            
            # Add MD5 hash for files
            if file_path.is_file() and stat.st_size < 100 * 1024 * 1024:  # Only for files < 100MB
                file_info['md5_hash'] = self.calculate_file_hash(file_path)
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"Failed to get file info for {file_path}: {e}")
            return None
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = 'md5') -> Optional[str]:
        """
        Calculate hash of a file.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
            
        Returns:
            Hash string or None if failed
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            
            hash_obj = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to calculate {algorithm} hash for {file_path}: {e}")
            return None
    
    def find_duplicate_files(self, directory_path: Path) -> Dict[str, List[Path]]:
        """
        Find duplicate files in directory based on content hash.
        
        Args:
            directory_path: Directory to search
            
        Returns:
            Dictionary mapping hash to list of duplicate files
        """
        file_hashes = {}
        duplicates = {}
        
        try:
            for file_path in directory_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Skip very large files
                if file_path.stat().st_size > 100 * 1024 * 1024:
                    continue
                
                file_hash = self.calculate_file_hash(file_path)
                if file_hash:
                    if file_hash not in file_hashes:
                        file_hashes[file_hash] = []
                    file_hashes[file_hash].append(file_path)
            
            # Find duplicates
            for file_hash, file_list in file_hashes.items():
                if len(file_list) > 1:
                    duplicates[file_hash] = file_list
            
            return duplicates
            
        except Exception as e:
            self.logger.error(f"Failed to find duplicates in {directory_path}: {e}")
            return {}
    
    def create_archive(self, source_paths: List[Path], 
                      archive_path: Path,
                      compression_type: str = 'zip') -> bool:
        """
        Create archive from list of files/directories.
        
        Args:
            source_paths: List of paths to archive
            archive_path: Path for output archive
            compression_type: Type of compression ('zip', 'tar', 'tar.gz')
            
        Returns:
            True if archive was created successfully
        """
        try:
            # Ensure archive directory exists
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            if compression_type == 'zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for source_path in source_paths:
                        if source_path.is_file():
                            archive.write(source_path, source_path.name)
                        elif source_path.is_dir():
                            for file_path in source_path.rglob('*'):
                                if file_path.is_file():
                                    relative_path = file_path.relative_to(source_path.parent)
                                    archive.write(file_path, str(relative_path))
            
            elif compression_type in ['tar', 'tar.gz']:
                import tarfile
                
                mode = 'w:gz' if compression_type == 'tar.gz' else 'w'
                with tarfile.open(archive_path, mode) as archive:
                    for source_path in source_paths:
                        archive.add(source_path, arcname=source_path.name)
            
            else:
                raise FileUtilsError(f"Unsupported compression type: {compression_type}")
            
            self.logger.info(f"Created archive: {archive_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create archive {archive_path}: {e}")
            return False
    
    def extract_archive(self, archive_path: Path, 
                       extract_to: Path) -> bool:
        """
        Extract archive to directory.
        
        Args:
            archive_path: Path to archive file
            extract_to: Directory to extract to
            
        Returns:
            True if extraction was successful
        """
        try:
            if not archive_path.exists():
                self.logger.error(f"Archive file does not exist: {archive_path}")
                return False
            
            # Ensure extraction directory exists
            extract_to.mkdir(parents=True, exist_ok=True)
            
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as archive:
                    archive.extractall(extract_to)
            
            elif archive_path.suffix.lower() in ['.tar', '.gz']:
                import tarfile
                with tarfile.open(archive_path, 'r:*') as archive:
                    archive.extractall(extract_to)
            
            else:
                raise FileUtilsError(f"Unsupported archive format: {archive_path.suffix}")
            
            self.logger.info(f"Extracted archive {archive_path} to {extract_to}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract archive {archive_path}: {e}")
            return False
    
    def rotate_files(self, file_pattern: str, directory: Path, 
                    max_files: int = 5) -> int:
        """
        Rotate files by renaming them with incremental numbers.
        
        Args:
            file_pattern: Pattern to match files (e.g., "app.log")
            directory: Directory containing files
            max_files: Maximum number of rotated files to keep
            
        Returns:
            Number of files rotated
        """
        try:
            if not directory.exists():
                return 0
            
            base_name = Path(file_pattern).stem
            extension = Path(file_pattern).suffix
            
            # Find existing rotated files
            existing_files = []
            for i in range(1, max_files + 1):
                rotated_name = f"{base_name}.{i}{extension}"
                rotated_path = directory / rotated_name
                if rotated_path.exists():
                    existing_files.append((i, rotated_path))
            
            # Rotate existing files (highest number first)
            existing_files.sort(key=lambda x: x[0], reverse=True)
            
            rotated_count = 0
            
            # Remove the oldest file if we're at the limit
            if len(existing_files) >= max_files:
                oldest_file = existing_files[0][1]
                try:
                    oldest_file.unlink()
                    rotated_count += 1
                    existing_files = existing_files[1:]
                except Exception as e:
                    self.logger.warning(f"Failed to remove oldest rotated file {oldest_file}: {e}")
            
            # Rotate existing files
            for number, file_path in existing_files:
                new_name = f"{base_name}.{number + 1}{extension}"
                new_path = directory / new_name
                try:
                    file_path.rename(new_path)
                    rotated_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to rotate {file_path} to {new_path}: {e}")
            
            # Rename the current file to .1
            current_file = directory / file_pattern
            if current_file.exists():
                rotated_name = f"{base_name}.1{extension}"
                rotated_path = directory / rotated_name
                try:
                    current_file.rename(rotated_path)
                    rotated_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to rotate current file {current_file}: {e}")
            
            if rotated_count > 0:
                self.logger.info(f"Rotated {rotated_count} files for pattern {file_pattern}")
            
            return rotated_count
            
        except Exception as e:
            self.logger.error(f"Failed to rotate files for pattern {file_pattern}: {e}")
            return 0
    
    def get_disk_usage(self, path: Path) -> Dict[str, float]:
        """
        Get disk usage information for a path.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with disk usage information (in MB)
        """
        try:
            stat = shutil.disk_usage(path)
            
            return {
                'total_mb': stat.total / (1024 * 1024),
                'used_mb': (stat.total - stat.free) / (1024 * 1024),
                'free_mb': stat.free / (1024 * 1024),
                'usage_percent': ((stat.total - stat.free) / stat.total) * 100
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get disk usage for {path}: {e}")
            return {}
    
    def save_json_file(self, data: Any, file_path: Path, 
                      backup_existing: bool = True,
                      pretty_format: bool = True) -> bool:
        """
        Save data to JSON file with backup option.
        
        Args:
            data: Data to save
            file_path: Path to JSON file
            backup_existing: Whether to backup existing file
            pretty_format: Whether to use pretty formatting
            
        Returns:
            True if save was successful
        """
        try:
            # Create backup if file exists and backup is requested
            if backup_existing and file_path.exists():
                self.create_backup_file(file_path)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                if pretty_format:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
            
            self.logger.debug(f"Saved JSON file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON file {file_path}: {e}")
            return False
    
    def load_json_file(self, file_path: Path) -> Optional[Any]:
        """
        Load data from JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Loaded data or None if failed
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"JSON file does not exist: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            return None