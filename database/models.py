from enum import IntEnum

from beanie import Document, Link


class SiteType(IntEnum):
    MANGALIB = 1
    MANGA_OVH = 2
    READMANGA = 3


class Manga(Document):
    type: SiteType
    name: str
    urn: str
    chapter: str


class User(Document):
    id: str
    subscriptions: list[Link[Manga]]
