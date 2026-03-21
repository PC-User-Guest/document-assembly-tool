from abc import ABC, abstractmethod
from typing import Optional, Any

class TemplateCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, expire: int = None):
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
