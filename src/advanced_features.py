import time
import logging
import hashlib
import os
import signal
import asyncio
import threading
import multiprocessing
import socket
import cProfile
import pstats
import atexit
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from contextlib import contextmanager

from cryptography.fernet import Fernet
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Logging configuration
logger = logging.getLogger(__name__)

# Prometheus Metrics
DOCUMENTS_PROCESSED = Counter('documents_processed_total', 'Total documents processed')
PROCESSING_TIME = Histogram('document_processing_seconds', 'Time spent processing documents')
ACTIVE_WORKERS = Gauge('active_workers', 'Number of active worker threads/processes')
ERRORS_TOTAL = Counter('errors_total', 'Total errors by type', ['error_type'])
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Current memory usage in bytes')
CACHE_HIT_RATE = Gauge('cache_hit_rate', 'Template cache hit rate')

_shutdown_event = threading.Event()

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks and metrics."""
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            import json
            import psutil
            health_data = {
                'status': 'healthy',
                'uptime_seconds': int(time.time()), # Simplification
                'documents_processed': int(DOCUMENTS_PROCESSED._value.get()),
                'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
                'db_healthy': True,
                'cache_hit_rate': CACHE_HIT_RATE._value.get(),
            }
            self.wfile.write(json.dumps(health_data).encode())
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()

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

    def get_all_metrics(self) -> Dict[str, float]:
        return {
            "total_documents": float(self.total_documents),
            "total_processing_time": float(self.total_processing_time),
            "average_time": float(self.get_average_time()),
            "throughput": float(self.get_throughput())
        }

class SecurityManager:
    """Handles encryption, access control, and security features."""

    def __init__(self, key_file: str = None):
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
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            return key

    def _generate_key_id(self) -> str:
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

    def hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

class ConcurrencyManager:
    """Manages concurrent document processing."""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        _shutdown_event.set()
        self._shutdown_gracefully()

    def _shutdown_gracefully(self):
        self.executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)

    def process_batch_sync(self, tasks: List[Callable], use_processes: bool = False):
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

# Global instances
metrics = PerformanceMetrics()
security = SecurityManager()
concurrency = ConcurrencyManager()

def start_health_check_server(port: int = 8000):
    def run_server():
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Health check server started on port {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

atexit.register(lambda: concurrency._shutdown_gracefully())
