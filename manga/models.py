from pydantic import BaseModel


class PartialManga(BaseModel):
    name: str
    url: str


class Release(BaseModel):
    volume: str
    chapter: str


class Manga(Release):
    name: str
    image_url: str
