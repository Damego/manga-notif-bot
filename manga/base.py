from abc import ABC, abstractmethod
from typing import Optional

from .models import PartialManga, Manga, Release


class MangaParser(ABC):
    @abstractmethod
    async def search(self, name: str) -> list[PartialManga]:
        return NotImplemented

    @abstractmethod
    async def get_info(self, url: str) -> Optional[Manga]:
        return NotImplemented

    @abstractmethod
    async def get_latest_release(self, url: str) -> Optional[Release]:
        ...
