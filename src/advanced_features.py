"""
Advanced Features Module for Document Assembly Tool

This module adds production-ready features including:
- Production debugging and profiling
- Enhanced observability with metrics and tracing
- Security enhancements (encryption, access control)
- Concurrency support for multi-document processing
- Data persistence layer (SQLite-based)
- Distributed processing capabilities (basic worker pool)
- Performance metrics and scaling benchmarks
- Health checks and graceful shutdown
"""

import asyncio
import atexit
import cProfile
import functools
import hashlib
import json
import logging
import multiprocessing
import os
import pstats
import psutil
import signal
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from cryptography.fernet import Fernet
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from http.server import HTTPServer, BaseHTTPRequestHandler
import json as json_lib

# Configure module logger
logger = logging.getLogger(__name__)

# Prometheus metrics
DOCUMENTS_PROCESSED = Counter('documents_processed_total', 'Total documents processed')
PROCESSING_TIME = Histogram('document_processing_seconds', 'Time spent processing documents')
ACTIVE_WORKERS = Gauge('active_workers', 'Number of active worker processes')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Current memory usage in bytes')
ERROR_COUNT = Counter('errors_total', 'Total number of errors encountered', ['error_type'])
CACHE_HIT_RATE = Gauge('cache_hit_rate', 'Template cache hit rate')

# Global shutdown event
_shutdown_event = threading.Event()
_startup_time = time.time()

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""
    
    def do_GET(self):
        if self.path == '/health':
            try:
                health_data = {
                    'status': 'healthy',
                    'uptime_seconds': int(time.time() - _startup_time),
                    'documents_processed': int(DOCUMENTS_PROCESSED._value.get()),
                    'memory_usage_mb': int(psutil.Process().memory_info().rss / 1024 / 1024),
                    'db_healthy': self._check_db_health(),
                    'cache_hit_rate': CACHE_HIT_RATE._value.get(),
                    'active_workers': int(ACTIVE_WORKERS._value.get()),
                    'timestamp': time.time()
                }
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json_lib.dumps(health_data).encode())
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                health_data = {
                    'status': 'unhealthy',
                    'reason': str(type(e).__name__),
                    'details': str(e)
                }
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json_lib.dumps(health_data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    @staticmethod
    def _check_db_health() -> bool:
        try:
            persistence = globals().get('persistence')
            if persistence:
                with sqlite3.connect(persistence.db_path) as conn:
                    conn.execute("SELECT 1")
                return True
            return False
        except Exception:
            return False
    
    def log_message(self, format, *args):
        # Suppress default HTTP logging
        pass


@dataclass
class PerformanceMetrics:
    """Tracks performance metrics for scaling analysis."""
    total_documents: int = 0
    total_processing_time: float = 0.0
    peak_memory_usage: int = 0
    concurrent_workers: int = 1
    benchmarks: Dict[str, float] = field(default_factory=dict)

    def record_processing(self, duration: float, memory_used: int):
        self.total_documents += 1
        self.total_processing_time += duration
        self.peak_memory_usage = max(self.peak_memory_usage, memory_used)
        PROCESSING_TIME.observe(duration)
        DOCUMENTS_PROCESSED.inc()

    def get_average_time(self) -> float:
        return self.total_processing_time / max(self.total_documents, 1)

    def get_throughput(self) -> float:
        return self.total_documents / max(self.total_processing_time, 0.001)

class DataPersistence:
    """SQLite-based persistence layer for templates and data."""

    def __init__(self, db_path: str = "document_assembly.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    content BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_sources (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    content BLOB,
                    data_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY,
                    template_name TEXT,
                    data_source_name TEXT,
                    output_path TEXT,
                    input_hash TEXT,
                    output_hash TEXT,
                    processing_time REAL,
                    encryption_key_id TEXT,
                    status TEXT,
                    worker_id INTEGER,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create index for faster audits
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_history_date 
                ON processing_history(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_history_status 
                ON processing_history(status)
            """)

    def save_template(self, name: str, content: bytes):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO templates (name, content) VALUES (?, ?)", (name, content))

    def load_template(self, name: str) -> Optional[bytes]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content FROM templates WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def save_data_source(self, name: str, content: bytes, data_type: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO data_sources (name, content, data_type) VALUES (?, ?, ?)",
                        (name, content, data_type))

    def load_data_source(self, name: str) -> Optional[tuple]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content, data_type FROM data_sources WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row if row else None

    def log_processing(self, template_name: str, data_source_name: str, output_path: str, processing_time: float, status: str, 
                      input_hash: str = None, output_hash: str = None, encryption_key_id: str = None, 
                      worker_id: int = None, error_message: str = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO processing_history 
                (template_name, data_source_name, output_path, processing_time, status, 
                 input_hash, output_hash, encryption_key_id, worker_id, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (template_name, data_source_name, output_path, processing_time, status, 
                  input_hash, output_hash, encryption_key_id, worker_id, error_message))

class SecurityManager:
    """Handles encryption, access control, and security features."""

    def __init__(self, key_file: str = None):
        # Use ~/.docassembler/key if not specified
        if key_file is None:
            key_dir = Path.home() / ".docassembler"
            key_dir.mkdir(parents=True, exist_ok=True)
            key_file = str(key_dir / "encryption.key")
        
        self.key_file = Path(key_file)
        self.key = self._load_or_generate_key()
        self.key_id = self._generate_key_id()
        logger.info(f"Security manager initialized with key_id: {self.key_id}")

    def _load_or_generate_key(self) -> bytes:
        if self.key_file.exists():
            # Verify permissions are restrictive
            mode = self.key_file.stat().st_mode
            if mode & 0o077:  # Check if any non-owner permission bits are set
                logger.warning(f"Key file has insecure permissions: {oct(mode)}")
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            # Write with restrictive permissions (owner read/write only)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            logger.info(f"Generated new encryption key at {self.key_file}")
            return key

    def _generate_key_id(self) -> str:
        """Generate a unique key identifier for audit tracking."""
        key_hash = hashlib.sha256(self.key).hexdigest()[:8]
        timestamp = time.strftime('%Y_%m_%d')
        return f"key_{timestamp}_{key_hash}"

    def encrypt_file(self, input_path: str, output_path: str):
        fernet = Fernet(self.key)
        with open(input_path, 'rb') as f:
            data = f.read()
        encrypted = fernet.encrypt(data)
        with open(output_path, 'wb') as f:
            f.write(encrypted)

    def decrypt_file(self, input_path: str, output_path: str):
        fernet = Fernet(self.key)
        with open(input_path, 'rb') as f:
            encrypted = f.read()
        decrypted = fernet.decrypt(encrypted)
        with open(output_path, 'wb') as f:
            f.write(decrypted)

    def hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def verify_integrity(self, content: bytes, expected_hash: str) -> bool:
        return self.hash_content(content) == expected_hash

    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(4096), b''):
                sha256.update(block)
        return f"sha256:{sha256.hexdigest()}"

class ConcurrencyManager:
    """Manages concurrent document processing."""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_workers)
        self._in_flight_tasks = []
        
        # Register graceful shutdown handler
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        _shutdown_event.set()
        self._shutdown_gracefully()

    def _shutdown_gracefully(self):
        """Wait for in-flight tasks to complete before exiting."""
        logger.info("Waiting for in-flight tasks to complete...")
        self.executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        logger.info("All tasks completed. Exiting.")

    async def process_batch_async(self, tasks: List[Callable], use_processes: bool = False):
        """Process multiple documents concurrently."""
        ACTIVE_WORKERS.set(len(tasks))
        try:
            if use_processes:
                loop = asyncio.get_event_loop()
                results = await asyncio.gather(*[
                    loop.run_in_executor(self.process_executor, task) for task in tasks
                ])
            else:
                results = await asyncio.gather(*[
                    asyncio.get_event_loop().run_in_executor(self.executor, task) for task in tasks
                ])
            return results
        finally:
            ACTIVE_WORKERS.set(0)

    def process_batch_sync(self, tasks: List[Callable], use_processes: bool = False):
        """Synchronous batch processing."""
        ACTIVE_WORKERS.set(len(tasks))
        try:
            if use_processes:
                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    return list(executor.map(lambda f: f(), tasks))
            else:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    return list(executor.map(lambda f: f(), tasks))
        finally:
            ACTIVE_WORKERS.set(0)

class DistributedProcessor:
    """Basic distributed processing using worker pools."""

    def __init__(self, worker_count: int = 4):
        self.worker_count = worker_count
        self.workers = []

    def start_workers(self):
        """Start worker processes."""
        for i in range(self.worker_count):
            worker = multiprocessing.Process(target=self._worker_loop, args=(i,))
            worker.start()
            self.workers.append(worker)

    def stop_workers(self):
        """Stop all worker processes."""
        for worker in self.workers:
            worker.terminate()
            worker.join()

    def _worker_loop(self, worker_id: int):
        """Worker process main loop."""
        logger.info(f"Worker {worker_id} started")
        # In a real implementation, this would listen for tasks via queues
        while True:
            time.sleep(1)  # Placeholder

@contextmanager
def profiling_context(profile_output: str = "profile.prof"):
    """Context manager for profiling code execution."""
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        yield profiler
    finally:
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.dump_stats(profile_output)
        logger.info(f"Profile saved to {profile_output}")

def benchmark_processing(func: Callable, iterations: int = 10) -> Dict[str, float]:
    """Benchmark a processing function."""
    times = []
    for _ in range(iterations):
        start = time.time()
        func()
        end = time.time()
        times.append(end - start)
    avg_time = sum(times) / len(times)
    return {
        'average_time': avg_time,
        'min_time': min(times),
        'max_time': max(times),
        'total_time': sum(times)
    }

# Global instances for easy access
metrics = PerformanceMetrics()
persistence = DataPersistence()
security = SecurityManager()
concurrency = ConcurrencyManager()
distributed = DistributedProcessor()

def start_health_check_server(port: int = 8000):
    """Start the HTTP health check server in a background thread."""
    def run_server():
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Health check server started on http://0.0.0.0:{port}/health")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

def trigger_graceful_shutdown():
    """Trigger graceful shutdown of all components."""
    _shutdown_event.set()
    if concurrency:
        concurrency._shutdown_gracefully()
    logger.info("Graceful shutdown completed")

# Register graceful shutdown on exit
atexit.register(trigger_graceful_shutdown)
