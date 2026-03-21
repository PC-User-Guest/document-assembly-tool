import sqlite3
import pickle
from typing import Optional, Any
from .interface import TemplateCache

class SQLiteCache(TemplateCache):
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    expires_at DATETIME
                )
            """)

    def get(self, key: str) -> Optional[Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return pickle.loads(row[0])
        return None

    def set(self, key: str, value: Any, expire: int = None):
        data = pickle.dumps(value)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", (key, data))

    def exists(self, key: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM cache WHERE key = ?", (key,))
            return cursor.fetchone() is not None
