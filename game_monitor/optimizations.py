"""
Performance Optimizations for Game Monitor System

Advanced optimizations for OCR processing, database operations,
memory management, and threading to achieve sub-second response times.
"""

import threading
import time
import gc
import psutil
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import queue
import weakref
from collections import defaultdict, OrderedDict
import hashlib
import numpy as np
from functools import wraps, lru_cache
import logging

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCROptimizer:
    """Advanced OCR performance optimizations"""
    
    def __init__(self):
        self.image_cache = OrderedDict()
        self.cache_max_size = 100
        self.preprocessing_cache = OrderedDict()
        self.region_configs = self._init_region_configs()
        self.template_cache = {}
        
        # OCR engine pool
        self.ocr_pool = queue.Queue(maxsize=3)
        self._init_ocr_pool()
        
        logging.info("OCROptimizer initialized with advanced optimizations")
    
    def _init_region_configs(self) -> Dict[str, Dict]:
        """Initialize region-specific OCR configurations"""
        return {
            'trader_name': {
                'config': '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_',
                'preprocessing': 'text_enhance',
                'expected_length': (3, 16)
            },
            'quantity': {
                'config': '--psm 8 -c tessedit_char_whitelist=0123456789',
                'preprocessing': 'number_enhance',
                'expected_length': (1, 6)
            },
            'price': {
                'config': '--psm 8 -c tessedit_char_whitelist=0123456789.',
                'preprocessing': 'number_enhance',
                'expected_length': (1, 10)
            },
            'item_name': {
                'config': '--psm 7 -l rus+eng',
                'preprocessing': 'text_enhance',
                'expected_length': (5, 50)
            }
        }
    
    def _init_ocr_pool(self):
        """Initialize OCR engine pool for parallel processing"""
        if not TESSERACT_AVAILABLE:
            return
        
        for _ in range(3):
            # Pre-initialize OCR configurations
            ocr_config = {
                'initialized': True,
                'last_used': time.time()
            }
            self.ocr_pool.put(ocr_config)
    
    def optimize_image_for_ocr(self, image: np.ndarray, region_type: str) -> np.ndarray:
        """Optimize image preprocessing based on region type"""
        if not CV2_AVAILABLE:
            return image
        
        # Check preprocessing cache
        image_hash = self._hash_image(image)
        cache_key = f"{image_hash}_{region_type}"
        
        if cache_key in self.preprocessing_cache:
            return self.preprocessing_cache[cache_key]
        
        # Apply region-specific preprocessing
        preprocessing_type = self.region_configs.get(region_type, {}).get('preprocessing', 'default')
        
        if preprocessing_type == 'text_enhance':
            optimized = self._enhance_text_image(image)
        elif preprocessing_type == 'number_enhance':
            optimized = self._enhance_number_image(image)
        else:
            optimized = self._default_enhance(image)
        
        # Cache the result
        if len(self.preprocessing_cache) >= self.cache_max_size:
            self.preprocessing_cache.popitem(last=False)
        self.preprocessing_cache[cache_key] = optimized
        
        return optimized
    
    def _enhance_text_image(self, image: np.ndarray) -> np.ndarray:
        """Optimize image for text recognition"""
        # Convert to grayscale
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Noise reduction
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Enhance contrast
        enhanced = cv2.equalizeHist(cleaned)
        
        return enhanced
    
    def _enhance_number_image(self, image: np.ndarray) -> np.ndarray:
        """Optimize image specifically for number recognition"""
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # More aggressive preprocessing for numbers
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(image, (3, 3), 0)
        
        # Binary threshold with Otsu's method
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        return cleaned
    
    def _default_enhance(self, image: np.ndarray) -> np.ndarray:
        """Default image enhancement"""
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Simple enhancement
        enhanced = cv2.equalizeHist(image)
        return enhanced
    
    def _hash_image(self, image: np.ndarray) -> str:
        """Create hash for image caching"""
        return hashlib.md5(image.tobytes()).hexdigest()[:16]
    
    def smart_region_detection(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect text regions intelligently to reduce OCR processing area"""
        if not CV2_AVAILABLE:
            # Fallback: return whole image as single region
            return [(0, 0, image.shape[1], image.shape[0])]
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Find contours that likely contain text
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter based on size (likely text regions)
            if 10 < w < 200 and 8 < h < 40:
                # Add some padding
                x = max(0, x - 2)
                y = max(0, y - 2)
                w = min(image.shape[1] - x, w + 4)
                h = min(image.shape[0] - y, h + 4)
                
                regions.append((x, y, w, h))
        
        # If no regions found, return full image
        if not regions:
            regions = [(0, 0, image.shape[1], image.shape[0])]
        
        return regions
    
    def template_match_numbers(self, image: np.ndarray) -> Optional[str]:
        """Fast template matching for common numbers"""
        if not CV2_AVAILABLE:
            return None
        
        # Simple template matching for digits 0-9
        # This is much faster than OCR for simple number recognition
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # This would require pre-built templates for each digit
        # For now, return None to fall back to OCR
        return None
    
    def parallel_ocr_processing(self, image_regions: List[Tuple[np.ndarray, str]]) -> List[Dict]:
        """Process multiple OCR regions in parallel"""
        if not TESSERACT_AVAILABLE:
            return [{'text': 'OCR_NOT_AVAILABLE', 'confidence': 0.0} for _ in image_regions]
        
        if len(image_regions) <= 1:
            # Single region, process normally
            if image_regions:
                image, region_type = image_regions[0]
                return [self._process_single_region(image, region_type)]
            return []
        
        # Multi-threading for parallel OCR
        results = [None] * len(image_regions)
        threads = []
        
        def process_region(idx, image, region_type):
            results[idx] = self._process_single_region(image, region_type)
        
        # Create threads for each region
        for i, (image, region_type) in enumerate(image_regions):
            thread = threading.Thread(target=process_region, args=(i, image, region_type))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=2.0)  # 2 second timeout per thread
        
        # Filter out None results
        return [r for r in results if r is not None]
    
    def _process_single_region(self, image: np.ndarray, region_type: str) -> Dict:
        """Process a single OCR region with optimizations"""
        try:
            # Get OCR engine from pool
            try:
                ocr_engine = self.ocr_pool.get(timeout=0.1)
            except queue.Empty:
                ocr_engine = {'initialized': True, 'last_used': time.time()}
            
            # Optimize image for this region type
            optimized_image = self.optimize_image_for_ocr(image, region_type)
            
            # Get region-specific config
            config = self.region_configs.get(region_type, {})
            ocr_config = config.get('config', '--psm 8')
            
            # Try template matching first for numbers
            if region_type in ['quantity', 'price']:
                template_result = self.template_match_numbers(optimized_image)
                if template_result:
                    return {
                        'text': template_result,
                        'confidence': 95.0,
                        'method': 'template'
                    }
            
            # Perform OCR
            try:
                if TESSERACT_AVAILABLE:
                    data = pytesseract.image_to_data(optimized_image, config=ocr_config, output_type=pytesseract.Output.DICT)
                    
                    # Extract text and confidence
                    words = []
                    confidences = []
                    
                    for i in range(len(data['text'])):
                        if int(data['conf'][i]) > 0:
                            words.append(data['text'][i])
                            confidences.append(int(data['conf'][i]))
                    
                    text = ' '.join(words).strip()
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    result = {
                        'text': text,
                        'confidence': avg_confidence,
                        'method': 'ocr'
                    }
                else:
                    result = {
                        'text': f'mock_{region_type}',
                        'confidence': 85.0,
                        'method': 'simulation'
                    }
            
            finally:
                # Return OCR engine to pool
                ocr_engine['last_used'] = time.time()
                try:
                    self.ocr_pool.put(ocr_engine, timeout=0.1)
                except queue.Full:
                    pass  # Pool is full, let it be garbage collected
            
            return result
            
        except Exception as e:
            logging.error(f"Error in OCR processing: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'method': 'error',
                'error': str(e)
            }


class DatabaseOptimizer:
    """Advanced database performance optimizations"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.query_cache = OrderedDict()
        self.cache_max_size = 1000
        self.prepared_statements = {}
        self.batch_queue = queue.Queue()
        self.batch_thread = None
        self.batch_processing = False
        
        # Start batch processing thread
        self.start_batch_processing()
        
        logging.info("DatabaseOptimizer initialized")
    
    def optimize_sqlite_connection(self, conn: sqlite3.Connection):
        """Apply SQLite performance optimizations"""
        # Performance pragmas
        optimizations = [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL", 
            "PRAGMA cache_size=10000",
            "PRAGMA temp_store=MEMORY",
            "PRAGMA mmap_size=268435456",  # 256MB
            "PRAGMA optimize"
        ]
        
        for pragma in optimizations:
            try:
                conn.execute(pragma)
            except sqlite3.Error as e:
                logging.warning(f"Failed to apply optimization '{pragma}': {e}")
        
        conn.commit()
    
    def create_advanced_indexes(self, conn: sqlite3.Connection):
        """Create optimized indexes for common queries"""
        indexes = [
            # Compound indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp_item ON trades(timestamp DESC, item_name)",
            "CREATE INDEX IF NOT EXISTS idx_trades_trader_timestamp ON trades(trader_nickname, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_item_trader ON current_inventory(item_name, trader_nickname)",
            
            # Partial indexes for active records
            "CREATE INDEX IF NOT EXISTS idx_active_search_queue ON search_queue(item_name) WHERE status = 'pending'",
            
            # Expression indexes for computed columns
            "CREATE INDEX IF NOT EXISTS idx_trades_price_range ON trades(price_per_unit) WHERE price_per_unit > 0"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except sqlite3.Error as e:
                logging.warning(f"Failed to create index: {e}")
        
        conn.commit()
    
    def prepare_common_statements(self, conn: sqlite3.Connection):
        """Prepare frequently used statements"""
        statements = {
            'insert_trade': """
                INSERT INTO trades (trade_type, trader_nickname, item_name, 
                                  quantity_change, price_per_unit, total_value, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            'update_inventory': """
                INSERT OR REPLACE INTO current_inventory 
                (trader_nickname, item_name, current_quantity, last_updated)
                VALUES (?, ?, ?, ?)
            """,
            'get_recent_trades': """
                SELECT timestamp, trader_nickname, item_name, quantity_change, price_per_unit, confidence
                FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            """,
            'get_trader_inventory': """
                SELECT item_name, current_quantity, last_updated
                FROM current_inventory 
                WHERE trader_nickname = ?
                ORDER BY last_updated DESC
            """
        }
        
        for name, sql in statements.items():
            try:
                self.prepared_statements[name] = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
            except sqlite3.Error as e:
                logging.warning(f"Failed to prepare statement '{name}': {e}")
    
    @lru_cache(maxsize=500)
    def cached_query(self, query_hash: str, query: str, params: tuple):
        """Cache query results for repeated queries"""
        # This is a simplified version - in practice, you'd need to handle cache invalidation
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def batch_insert_trades(self, trades: List[Tuple]):
        """Optimized batch insert for trades"""
        if not trades:
            return
        
        # Use executemany for batch operations
        with self.db_manager.get_connection() as conn:
            conn.executemany("""
                INSERT INTO trades (trade_type, trader_nickname, item_name, 
                                  quantity_change, price_per_unit, total_value, 
                                  confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, trades)
            conn.commit()
    
    def start_batch_processing(self):
        """Start background batch processing thread"""
        if self.batch_thread and self.batch_thread.is_alive():
            return
        
        self.batch_processing = True
        self.batch_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self.batch_thread.start()
    
    def stop_batch_processing(self):
        """Stop batch processing thread"""
        self.batch_processing = False
        if self.batch_thread:
            self.batch_thread.join(timeout=5)
    
    def _batch_processor(self):
        """Background batch processor"""
        batch_trades = []
        batch_timeout = 1.0  # Process batches every second
        
        while self.batch_processing:
            try:
                # Collect trades for batching
                deadline = time.time() + batch_timeout
                
                while time.time() < deadline and len(batch_trades) < 100:
                    try:
                        trade = self.batch_queue.get(timeout=0.1)
                        batch_trades.append(trade)
                    except queue.Empty:
                        continue
                
                # Process batch if we have trades
                if batch_trades:
                    self.batch_insert_trades(batch_trades)
                    logging.info(f"Processed batch of {len(batch_trades)} trades")
                    batch_trades.clear()
                
            except Exception as e:
                logging.error(f"Error in batch processor: {e}")
                batch_trades.clear()
    
    def queue_trade_for_batch(self, trade_data: Tuple):
        """Queue trade for batch processing"""
        try:
            self.batch_queue.put(trade_data, timeout=0.1)
        except queue.Full:
            logging.warning("Batch queue full, processing synchronously")
            self.batch_insert_trades([trade_data])


class MemoryOptimizer:
    """Memory usage optimization and leak detection"""
    
    def __init__(self):
        self.memory_snapshots = []
        self.weak_refs = weakref.WeakSet()
        self.object_pools = {}
        self.gc_stats = {'collections': 0, 'objects_collected': 0}
        
        # Configure garbage collection
        self.configure_gc()
        
        logging.info("MemoryOptimizer initialized")
    
    def configure_gc(self):
        """Configure garbage collection for better performance"""
        # Increase GC thresholds to reduce frequency
        gc.set_threshold(1000, 15, 15)
        
        # Enable automatic garbage collection
        gc.enable()
        
        logging.info(f"GC thresholds set to: {gc.get_threshold()}")
    
    def create_object_pool(self, pool_name: str, factory_func: callable, max_size: int = 10):
        """Create object pool for expensive-to-create objects"""
        self.object_pools[pool_name] = {
            'objects': queue.Queue(maxsize=max_size),
            'factory': factory_func,
            'max_size': max_size,
            'created_count': 0,
            'reuse_count': 0
        }
    
    def get_from_pool(self, pool_name: str):
        """Get object from pool or create new one"""
        if pool_name not in self.object_pools:
            raise ValueError(f"Pool '{pool_name}' not found")
        
        pool = self.object_pools[pool_name]
        
        try:
            obj = pool['objects'].get(timeout=0.01)
            pool['reuse_count'] += 1
            return obj
        except queue.Empty:
            # Create new object
            obj = pool['factory']()
            pool['created_count'] += 1
            return obj
    
    def return_to_pool(self, pool_name: str, obj):
        """Return object to pool"""
        if pool_name not in self.object_pools:
            return
        
        pool = self.object_pools[pool_name]
        
        try:
            pool['objects'].put(obj, timeout=0.01)
        except queue.Full:
            # Pool is full, let object be garbage collected
            pass
    
    def track_object(self, obj):
        """Track object for memory monitoring"""
        self.weak_refs.add(obj)
    
    def force_gc_collection(self) -> int:
        """Force garbage collection and return objects collected"""
        collected = gc.collect()
        self.gc_stats['collections'] += 1
        self.gc_stats['objects_collected'] += collected
        
        logging.info(f"Forced GC: collected {collected} objects")
        return collected
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / (1024 * 1024),
            'vms_mb': memory_info.vms / (1024 * 1024),
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / (1024 * 1024),
            'gc_stats': self.gc_stats.copy(),
            'tracked_objects': len(self.weak_refs),
            'object_pools': {
                name: {
                    'size': pool['objects'].qsize(),
                    'created': pool['created_count'],
                    'reused': pool['reuse_count']
                }
                for name, pool in self.object_pools.items()
            }
        }
    
    def detect_memory_leaks(self) -> List[Dict]:
        """Detect potential memory leaks"""
        current_usage = self.get_memory_usage()
        self.memory_snapshots.append({
            'timestamp': time.time(),
            'usage': current_usage
        })
        
        # Keep only recent snapshots
        if len(self.memory_snapshots) > 20:
            self.memory_snapshots = self.memory_snapshots[-10:]
        
        if len(self.memory_snapshots) < 3:
            return []
        
        # Check for consistent memory growth
        recent_snapshots = self.memory_snapshots[-5:]
        growth_trend = []
        
        for i in range(1, len(recent_snapshots)):
            prev_rss = recent_snapshots[i-1]['usage']['rss_mb']
            curr_rss = recent_snapshots[i]['usage']['rss_mb']
            growth_trend.append(curr_rss - prev_rss)
        
        # If memory is consistently growing, flag as potential leak
        avg_growth = sum(growth_trend) / len(growth_trend)
        if avg_growth > 5.0:  # More than 5MB average growth
            return [{
                'type': 'memory_leak',
                'avg_growth_mb': avg_growth,
                'total_growth_mb': sum(growth_trend),
                'snapshots_analyzed': len(growth_trend)
            }]
        
        return []


class ThreadingOptimizer:
    """Threading and concurrency optimizations"""
    
    def __init__(self):
        self.thread_pools = {}
        self.load_balancers = {}
        self.thread_stats = defaultdict(lambda: {'created': 0, 'completed': 0, 'errors': 0})
        
        # Optimal thread pool sizes based on CPU cores
        self.cpu_count = psutil.cpu_count()
        self.optimal_pool_sizes = {
            'io_bound': min(20, self.cpu_count * 4),  # I/O bound tasks
            'cpu_bound': self.cpu_count,              # CPU bound tasks
            'ocr_processing': min(4, self.cpu_count), # OCR processing
            'database': min(8, self.cpu_count * 2)    # Database operations
        }
        
        logging.info(f"ThreadingOptimizer initialized for {self.cpu_count} CPU cores")
    
    def create_optimized_thread_pool(self, pool_name: str, pool_type: str = 'io_bound'):
        """Create optimized thread pool"""
        if pool_name in self.thread_pools:
            return self.thread_pools[pool_name]
        
        pool_size = self.optimal_pool_sizes.get(pool_type, self.cpu_count)
        
        # Create thread pool
        thread_pool = {
            'workers': [],
            'task_queue': queue.Queue(),
            'pool_size': pool_size,
            'pool_type': pool_type,
            'active': True,
            'stats': {'tasks_processed': 0, 'errors': 0}
        }
        
        # Start worker threads
        for i in range(pool_size):
            worker = threading.Thread(
                target=self._worker_thread,
                args=(pool_name, thread_pool),
                daemon=True,
                name=f"{pool_name}_worker_{i}"
            )
            worker.start()
            thread_pool['workers'].append(worker)
        
        self.thread_pools[pool_name] = thread_pool
        logging.info(f"Created thread pool '{pool_name}' with {pool_size} workers")
        
        return thread_pool
    
    def _worker_thread(self, pool_name: str, thread_pool: Dict):
        """Worker thread for processing tasks"""
        while thread_pool['active']:
            try:
                # Get task from queue
                task = thread_pool['task_queue'].get(timeout=1.0)
                if task is None:  # Shutdown signal
                    break
                
                func, args, kwargs, callback = task
                
                # Execute task
                try:
                    result = func(*args, **kwargs)
                    thread_pool['stats']['tasks_processed'] += 1
                    
                    # Call callback if provided
                    if callback:
                        callback(result)
                        
                except Exception as e:
                    thread_pool['stats']['errors'] += 1
                    logging.error(f"Error in worker thread {pool_name}: {e}")
                
                # Mark task as done
                thread_pool['task_queue'].task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Worker thread {pool_name} error: {e}")
    
    def submit_task(self, pool_name: str, func: callable, *args, callback: callable = None, **kwargs):
        """Submit task to thread pool"""
        if pool_name not in self.thread_pools:
            raise ValueError(f"Thread pool '{pool_name}' not found")
        
        thread_pool = self.thread_pools[pool_name]
        task = (func, args, kwargs, callback)
        
        try:
            thread_pool['task_queue'].put(task, timeout=0.1)
        except queue.Full:
            logging.warning(f"Thread pool '{pool_name}' queue is full")
            # Execute synchronously as fallback
            try:
                result = func(*args, **kwargs)
                if callback:
                    callback(result)
            except Exception as e:
                logging.error(f"Synchronous fallback error: {e}")
    
    def create_load_balancer(self, balancer_name: str, pool_names: List[str]):
        """Create load balancer for multiple thread pools"""
        pools = []
        for name in pool_names:
            if name in self.thread_pools:
                pools.append(self.thread_pools[name])
        
        if not pools:
            raise ValueError("No valid thread pools for load balancer")
        
        self.load_balancers[balancer_name] = {
            'pools': pools,
            'pool_names': pool_names,
            'current_index': 0,
            'tasks_distributed': 0
        }
        
        logging.info(f"Created load balancer '{balancer_name}' with {len(pools)} pools")
    
    def submit_balanced_task(self, balancer_name: str, func: callable, *args, **kwargs):
        """Submit task using load balancer"""
        if balancer_name not in self.load_balancers:
            raise ValueError(f"Load balancer '{balancer_name}' not found")
        
        balancer = self.load_balancers[balancer_name]
        
        # Simple round-robin load balancing
        pool_index = balancer['current_index'] % len(balancer['pools'])
        pool_name = balancer['pool_names'][pool_index]
        
        # Submit to selected pool
        self.submit_task(pool_name, func, *args, **kwargs)
        
        # Update balancer state
        balancer['current_index'] = (balancer['current_index'] + 1) % len(balancer['pools'])
        balancer['tasks_distributed'] += 1
    
    def get_thread_pool_stats(self) -> Dict[str, Any]:
        """Get thread pool statistics"""
        stats = {}
        
        for pool_name, thread_pool in self.thread_pools.items():
            stats[pool_name] = {
                'pool_size': thread_pool['pool_size'],
                'pool_type': thread_pool['pool_type'],
                'queue_size': thread_pool['task_queue'].qsize(),
                'tasks_processed': thread_pool['stats']['tasks_processed'],
                'errors': thread_pool['stats']['errors'],
                'active_workers': sum(1 for w in thread_pool['workers'] if w.is_alive())
            }
        
        return stats
    
    def shutdown_all_pools(self):
        """Shutdown all thread pools gracefully"""
        for pool_name, thread_pool in self.thread_pools.items():
            thread_pool['active'] = False
            
            # Send shutdown signals to workers
            for _ in thread_pool['workers']:
                thread_pool['task_queue'].put(None)
            
            # Wait for workers to finish
            for worker in thread_pool['workers']:
                worker.join(timeout=2.0)
            
            logging.info(f"Shutdown thread pool '{pool_name}'")


# Global optimizer instances
_ocr_optimizer = None
_memory_optimizer = None
_threading_optimizer = None

def get_ocr_optimizer() -> OCROptimizer:
    """Get global OCR optimizer"""
    global _ocr_optimizer
    if _ocr_optimizer is None:
        _ocr_optimizer = OCROptimizer()
    return _ocr_optimizer

def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer

def get_threading_optimizer() -> ThreadingOptimizer:
    """Get global threading optimizer"""
    global _threading_optimizer
    if _threading_optimizer is None:
        _threading_optimizer = ThreadingOptimizer()
    return _threading_optimizer


def optimization_decorator(operation_name: str):
    """Decorator to apply automatic optimizations to functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            memory_optimizer = get_memory_optimizer()
            
            # Take memory snapshot before operation
            memory_before = memory_optimizer.get_memory_usage()
            
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance
                from .logging_config import log_timing
                log_timing(operation_name, duration, success=True)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                from .logging_config import log_timing, log_error
                log_timing(operation_name, duration, success=False)
                log_error(e, operation_name)
                raise
            
            finally:
                # Check memory usage after operation
                memory_after = memory_optimizer.get_memory_usage()
                memory_growth = memory_after['rss_mb'] - memory_before['rss_mb']
                
                # Force GC if memory growth is significant
                if memory_growth > 50:  # More than 50MB growth
                    memory_optimizer.force_gc_collection()
        
        return wrapper
    return decorator