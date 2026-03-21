import sqlite3
import time
import logging
import threading
import queue
from abc import ABC, abstractmethod
from typing import Optional, List

logger = logging.getLogger(__name__)

class AuditBackend(ABC):
    @abstractmethod
    def log_processing(self, template_name: str, data_source_name: str, output_path: str, processing_time: float, status: str,
                      input_hash: str = None, output_hash: str = None, encryption_key_id: str = None,
                      worker_id: int = None, error_message: str = None):
        pass

class SQLiteAuditBackend(AuditBackend):
    def __init__(self, db_path: str = "document_assembly.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY,
                    template_name TEXT,
                    data_source_name TEXT,
                    output_path TEXT,
                    processing_time REAL,
                    status TEXT,
                    input_hash TEXT,
                    output_hash TEXT,
                    encryption_key_id TEXT,
                    worker_id INTEGER,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def log_processing(self, **kwargs):
        with sqlite3.connect(self.db_path) as conn:
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?'] * len(kwargs))
            values = tuple(kwargs.values())
            conn.execute(f"INSERT INTO processing_history ({keys}) VALUES ({placeholders})", values)

class PostgreSQLAuditBackend(AuditBackend):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_db()

    def _init_db(self):
        import psycopg2
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS processing_history (
                        id SERIAL PRIMARY KEY,
                        template_name TEXT,
                        data_source_name TEXT,
                        output_path TEXT,
                        processing_time REAL,
                        status TEXT,
                        input_hash TEXT,
                        output_hash TEXT,
                        encryption_key_id TEXT,
                        worker_id INTEGER,
                        error_message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

    def log_processing(self, **kwargs):
        import psycopg2
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                keys = ', '.join(kwargs.keys())
                placeholders = ', '.join(['%s'] * len(kwargs))
                values = tuple(kwargs.values())
                cur.execute(f"INSERT INTO processing_history ({keys}) VALUES ({placeholders})", values)

class ReplicationManager(AuditBackend):
    def __init__(self, primary: AuditBackend, replicas: List[AuditBackend] = None, sync_mode: bool = False):
        self.primary = primary
        self.replicas = replicas or []
        self.sync_mode = sync_mode
        self.queue = queue.Queue()
        if not self.sync_mode:
            self.worker = threading.Thread(target=self._replication_worker, daemon=True)
            self.worker.start()

    def _replication_worker(self):
        while True:
            item = self.queue.get()
            if item is None: break
            for replica in self.replicas:
                try:
                    replica.log_processing(**item)
                except Exception as e:
                    logger.error(f"Replication failed: {e}")
            self.queue.task_done()

    def log_processing(self, **kwargs):
        # Always write to primary
        self.primary.log_processing(**kwargs)

        # Replicate
        if self.sync_mode:
            for replica in self.replicas:
                replica.log_processing(**kwargs)
        else:
            self.queue.put(kwargs)

    def failover(self, new_primary_index: int):
        if 0 <= new_primary_index < len(self.replicas):
            old_primary = self.primary
            self.primary = self.replicas.pop(new_primary_index)
            self.replicas.append(old_primary)
            logger.info(f"Failover successful. New primary: {type(self.primary).__name__}")
