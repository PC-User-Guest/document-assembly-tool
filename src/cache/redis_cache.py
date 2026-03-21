import redis
import pickle
from typing import Optional, Any
from .interface import TemplateCache

class RedisCache(TemplateCache):
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: str = None):
        self.client = redis.Redis(host=host, port=port, db=db, password=password)

    def get(self, key: str) -> Optional[Any]:
        data = self.client.get(key)
        if data:
            return pickle.loads(data)
        return None

    def set(self, key: str, value: Any, expire: int = None):
        data = pickle.dumps(value)
        self.client.set(key, data, ex=expire)

    def exists(self, key: str) -> bool:
        return self.client.exists(key) > 0
