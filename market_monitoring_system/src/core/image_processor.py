"""
Image processing and merging module for market monitoring system.
Handles screenshot merging, optimization, and cleanup operations.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import uuid
import time

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError as e:
    PILLOW_AVAILABLE = False
    PILLOW_ERROR = str(e)

from config.settings import SettingsManager, ImageProcessingConfig


class ImageProcessingError(Exception):
    """Exception raised for image processing errors."""
    pass


class ImageProcessor:
    """
    Handles image processing operations for the market monitoring system.
    Includes screenshot merging, optimization, and file management.
    """
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Initialize image processor.
        
        Args:
            settings_manager: Configuration manager instance
        """
        if not PILLOW_AVAILABLE:
            raise ImageProcessingError(f"Pillow library not available: {PILLOW_ERROR}")
        
        self.settings = settings_manager
        self.logger = logging.getLogger(__name__)
        self.config: ImageProcessingConfig = settings_manager.image_processing
        
        # Processing statistics
        self._processing_stats = {
            'total_processed': 0,
            'successful_merges': 0,
            'failed_merges': 0,
            'files_cleaned': 0,
            'total_processing_time': 0.0,
            'last_processing_time': None
        }
    
    def find_screenshots_in_folder(self, folder_path: Path, 
                                  hotkey_name: Optional[str] = None) -> List[Path]:
        """
        Find all screenshot files in specified folder.
        
        Args:
            folder_path: Path to folder containing screenshots
            hotkey_name: Optional hotkey name to filter files
            
        Returns:
            List of screenshot file paths sorted by modification time
        """
        try:
            if not folder_path.exists():
                self.logger.warning(f"Screenshot folder does not exist: {folder_path}")
                return []
            
            # Define patterns to search for
            patterns = []
            if hotkey_name:
                patterns.append(f"{hotkey_name}_*.png")
                patterns.append(f"{hotkey_name}_*.jpg")
                patterns.append(f"{hotkey_name}_*.jpeg")
            else:
                patterns.extend(["*.png", "*.jpg", "*.jpeg"])
            
            # Find all matching files
            files = []
            for pattern in patterns:
                files.extend(folder_path.glob(pattern))
            
            # Remove duplicates and sort by modification time
            unique_files = list(set(files))
            unique_files.sort(key=lambda f: f.stat().st_mtime)
            
            self.logger.debug(f"Found {len(unique_files)} screenshot files in {folder_path}")
            return unique_files
            
        except Exception as e:
            self.logger.error(f"Failed to find screenshots in {folder_path}: {e}")
            return []
    
    def merge_to_vertical_column(self, image_paths: List[Path], 
                               output_path: Optional[Path] = None,
                               max_width: Optional[int] = None) -> Optional[Path]:
        """
        Merge multiple images into a single vertical column.
        Memory-efficient implementation using streaming processing.
        
        Args:
            image_paths: List of image file paths to merge
            output_path: Optional output path (auto-generated if not provided)
            max_width: Maximum width for the merged image
            
        Returns:
            Path to merged image file or None if failed
        """
        if not image_paths:
            self.logger.warning("No images provided for merging")
            return None
        
        start_time = time.time()
        
        # Log processing info for large batches
        if len(image_paths) > 50:
            self.logger.info(f"Processing large batch of {len(image_paths)} images - using streaming processing")
        
        try:
            # First pass: collect image metadata without loading into memory
            image_metadata = []
            total_height = 0
            max_image_width = 0
            
            for img_path in image_paths:
                try:
                    with Image.open(img_path) as img:
                        metadata = {
                            'path': img_path,
                            'width': img.width,
                            'height': img.height,
                            'mode': img.mode,
                            'format': img.format
                        }
                        image_metadata.append(metadata)
                        total_height += img.height
                        max_image_width = max(max_image_width, img.width)
                        
                except Exception as e:
                    self.logger.error(f"Failed to read metadata from {img_path}: {e}")
                    continue
            
            if not image_metadata:
                self.logger.error("No valid images found for merging")
                return None
            
            # Determine final dimensions
            final_width = min(max_image_width, max_width or self.config.max_image_width)
            
            # Check size constraints and calculate scaling
            scale_factor = 1.0
            if total_height > self.config.max_image_height:
                self.logger.warning(
                    f"Merged image height ({total_height}) exceeds maximum "
                    f"({self.config.max_image_height}), will be resized"
                )
                scale_factor = self.config.max_image_height / total_height
                final_width = int(final_width * scale_factor)
                total_height = self.config.max_image_height
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"merged_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
                output_path = self.settings.paths.temp_merged / filename
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create merged image
            merged_image = None
            try:
                merged_image = Image.new('RGB', (final_width, total_height), 'white')
                
                # Second pass: stream process images one by one
                current_y = 0
                processed_count = 0
                
                for metadata in image_metadata:
                    if current_y >= total_height:
                        break
                        
                    try:
                        # Load image in context manager for automatic cleanup
                        with Image.open(metadata['path']) as img:
                            # Calculate target dimensions
                            target_width = final_width
                            if scale_factor != 1.0:
                                target_height = int(img.height * scale_factor)
                            else:
                                target_height = img.height
                            
                            # Resize if necessary
                            if img.width != target_width or (scale_factor != 1.0 and img.height != target_height):
                                if scale_factor != 1.0:
                                    img = img.resize((target_width, target_height), Image.LANCZOS)
                                else:
                                    aspect_ratio = img.height / img.width
                                    new_height = int(target_width * aspect_ratio)
                                    img = img.resize((target_width, new_height), Image.LANCZOS)
                                    target_height = new_height
                            
                            # Check if image fits in remaining space
                            remaining_height = total_height - current_y
                            if target_height > remaining_height:
                                if remaining_height > 0:
                                    # Crop image to fit
                                    img = img.crop((0, 0, img.width, remaining_height))
                                    target_height = remaining_height
                                else:
                                    break
                            
                            # Paste image into merged image
                            merged_image.paste(img, (0, current_y))
                            current_y += target_height
                            processed_count += 1
                            
                            # Log progress for large batches
                            if processed_count % 5 == 0:
                                self.logger.debug(f"Processed {processed_count}/{len(image_metadata)} images")
                    
                    except Exception as e:
                        self.logger.error(f"Failed to process image {metadata['path']}: {e}")
                        continue
                
                # Optimize image for OCR if requested
                if self.config.optimize_for_ocr:
                    optimized_image = self._optimize_for_ocr(merged_image)
                    merged_image.close()
                    merged_image = optimized_image
                
                # Save merged image
                save_kwargs = {'format': 'JPEG', 'optimize': True}
                if output_path.suffix.lower() in ['.jpg', '.jpeg']:
                    save_kwargs['quality'] = self.config.jpeg_quality
                
                merged_image.save(output_path, **save_kwargs)
                
                # Update statistics
                processing_time = time.time() - start_time
                self._processing_stats['successful_merges'] += 1
                self._processing_stats['total_processing_time'] += processing_time
                self._processing_stats['last_processing_time'] = datetime.now().isoformat()
                
                self.logger.info(
                    f"Successfully merged {processed_count} images into {output_path.name} "
                    f"({final_width}x{total_height}) in {processing_time:.3f}s"
                )
                
                return output_path
            
            finally:
                # Ensure merged image is always closed
                if merged_image:
                    merged_image.close()
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._processing_stats['failed_merges'] += 1
            self.logger.error(f"Failed to merge images: {e} (failed after {processing_time:.3f}s)")
            return None
    
    def _optimize_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Optimize image for better OCR recognition.
        Creates a new optimized image, original image should be closed by caller.
        
        Args:
            image: PIL Image to optimize
            
        Returns:
            New optimized PIL Image (caller responsible for closing)
        """
        try:
            # Convert to grayscale if not already
            working_image = image
            if image.mode != 'L':
                working_image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(working_image)
            contrast_image = enhancer.enhance(1.2)
            
            # Clean up intermediate image if different from original
            if working_image is not image:
                working_image.close()
            working_image = contrast_image
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(working_image)
            sharp_image = enhancer.enhance(1.1)
            
            # Clean up previous image
            if working_image is not image:
                working_image.close()
            working_image = sharp_image
            
            # Apply slight denoising
            denoised_image = working_image.filter(ImageFilter.MedianFilter(size=3))
            
            # Clean up previous image
            if working_image is not image:
                working_image.close()
            working_image = denoised_image
            
            # Convert back to RGB for JPEG compatibility
            final_image = working_image.convert('RGB')
            
            # Clean up previous image if different
            if working_image is not image and working_image is not final_image:
                working_image.close()
            
            return final_image
            
        except Exception as e:
            self.logger.warning(f"Failed to optimize image for OCR: {e}")
            # Return a copy of the original to maintain consistency
            return image.copy()
    
    def cleanup_source_files(self, file_paths: List[Path], 
                           backup_failed: bool = True) -> Tuple[int, int]:
        """
        Clean up source files immediately after processing.
        
        Args:
            file_paths: List of file paths to delete
            backup_failed: Whether to backup files that fail to delete
            
        Returns:
            Tuple of (successful_deletions, failed_deletions)
        """
        successful = 0
        failed = 0
        
        for file_path in file_paths:
            try:
                if not file_path.exists():
                    continue
                
                # Create backup if deletion fails and backup is requested
                if backup_failed:
                    backup_path = file_path.with_suffix(f'.backup{file_path.suffix}')
                    try:
                        shutil.copy2(file_path, backup_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to create backup for {file_path}: {e}")
                
                # Delete the original file
                file_path.unlink()
                successful += 1
                self.logger.debug(f"Deleted source file: {file_path.name}")
                
            except Exception as e:
                failed += 1
                self.logger.error(f"Failed to delete source file {file_path}: {e}")
        
        # Update statistics
        self._processing_stats['files_cleaned'] += successful
        
        if successful > 0 or failed > 0:
            self.logger.info(f"Cleaned up source files: {successful} successful, {failed} failed")
        
        return successful, failed
    
    def process_hotkey_folder(self, hotkey_name: str, 
                            auto_cleanup: bool = True) -> Optional[Path]:
        """
        Process all screenshots in a hotkey's folder.
        
        Args:
            hotkey_name: Name of the hotkey
            auto_cleanup: Whether to automatically cleanup source files
            
        Returns:
            Path to merged image or None if processing failed
        """
        try:
            # Get hotkey configuration
            hotkey_config = self.settings.get_hotkey_config(hotkey_name)
            if not hotkey_config:
                self.logger.error(f"No configuration found for hotkey {hotkey_name}")
                return None
            
            # Get screenshot folder
            screenshot_folder = self.settings.get_screenshot_path(hotkey_name)
            if not screenshot_folder:
                self.logger.error(f"No screenshot path configured for hotkey {hotkey_name}")
                return None
            
            # Find screenshots
            screenshot_files = self.find_screenshots_in_folder(screenshot_folder, hotkey_name)
            if not screenshot_files:
                self.logger.debug(f"No screenshots found for hotkey {hotkey_name}")
                return None
            
            self.logger.info(f"Processing {len(screenshot_files)} screenshots for {hotkey_name}")
            
            # Merge images
            merged_path = self.merge_to_vertical_column(screenshot_files)
            if not merged_path:
                return None
            
            # Clean up source files if successful and auto_cleanup is enabled
            if auto_cleanup:
                self.cleanup_source_files(screenshot_files)
            
            # Update total processing statistics
            self._processing_stats['total_processed'] += len(screenshot_files)
            
            return merged_path
            
        except Exception as e:
            self.logger.error(f"Failed to process hotkey folder {hotkey_name}: {e}")
            return None
    
    def batch_process_all_hotkeys(self, enabled_only: bool = True) -> Dict[str, Optional[Path]]:
        """
        Process screenshots for all configured hotkeys.
        
        Args:
            enabled_only: Whether to process only enabled hotkeys
            
        Returns:
            Dictionary mapping hotkey names to merged image paths
        """
        results = {}
        
        try:
            # Get hotkeys to process
            if enabled_only:
                hotkeys = self.settings.get_enabled_hotkeys()
            else:
                hotkeys = self.settings.hotkeys
            
            self.logger.info(f"Batch processing {len(hotkeys)} hotkeys")
            
            # Process each hotkey
            for hotkey_name in hotkeys:
                try:
                    result = self.process_hotkey_folder(hotkey_name)
                    results[hotkey_name] = result
                    
                    if result:
                        self.logger.info(f"Successfully processed {hotkey_name} -> {result.name}")
                    else:
                        self.logger.info(f"No processing needed for {hotkey_name}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to process {hotkey_name}: {e}")
                    results[hotkey_name] = None
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            return {}
    
    def cleanup_old_merged_images(self, max_age_hours: int = 24) -> int:
        """
        Clean up old merged images.
        
        Args:
            max_age_hours: Maximum age of merged images to keep
            
        Returns:
            Number of files deleted
        """
        try:
            merged_path = self.settings.paths.temp_merged
            if not merged_path.exists():
                return 0
            
            cutoff_time = time.time() - (max_age_hours * 3600)
            deleted_count = 0
            
            # Find and delete old merged images
            for file_path in merged_path.glob("merged_*.jpg"):
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to delete old merged image {file_path}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old merged images")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old merged images: {e}")
            return 0
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get image processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = self._processing_stats.copy()
        
        # Calculate averages
        if stats['successful_merges'] > 0:
            stats['average_processing_time'] = (
                stats['total_processing_time'] / stats['successful_merges']
            )
        else:
            stats['average_processing_time'] = 0.0
        
        # Add success rate
        total_attempts = stats['successful_merges'] + stats['failed_merges']
        if total_attempts > 0:
            stats['success_rate'] = stats['successful_merges'] / total_attempts
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def validate_image_file(self, file_path: Path) -> bool:
        """
        Validate that a file is a valid image.
        
        Args:
            file_path: Path to image file
            
        Returns:
            True if file is valid image, False otherwise
        """
        try:
            if not file_path.exists():
                return False
            
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception as e:
            self.logger.debug(f"Image validation failed for {file_path}: {e}")
            return False
    
    def get_image_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about an image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dictionary with image information or None if failed
        """
        try:
            with Image.open(file_path) as img:
                return {
                    'filename': file_path.name,
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': file_path.stat().st_size,
                    'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
        except Exception as e:
            self.logger.error(f"Failed to get image info for {file_path}: {e}")
            return None