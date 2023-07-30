from pydantic import BaseModel


class PartialManga(BaseModel):
    name: str
    url: str


class Release(BaseModel):
    volume: str
    chapter: str
    url: str


class Manga(PartialManga):
    image_url: str
    latest_release: Release
