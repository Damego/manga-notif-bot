from enum import IntEnum
from typing import List

from beanie import Document, Link


class SiteType(IntEnum):
    MANGALIB = 1
    MANGA_OVH = 2
    READMANGA = 3


class Manga(Document):
    type: SiteType
    name: str
    urn: str
    volume: int
    chapter: int


class TelegramChat(Document):
    id: str
    subscriptions: List[Link[Manga]]
