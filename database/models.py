from typing import List

from beanie import Document, Link

from enums import SiteType


class Manga(Document):
    type: SiteType
    name: str
    urn: str
    volume: int
    chapter: int


class TelegramChat(Document):
    id: str
    subscriptions: List[Link[Manga]]

    def has_subscription(self, manga: Manga) -> bool:
        return bool(next((m for m in self.subscriptions if m.type == manga.type and m.urn == manga.urn), None))

    def unsubscribe(self, manga: Manga):
        self.subscriptions.remove(manga)
