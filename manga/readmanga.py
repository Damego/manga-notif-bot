# TODO: Run parsing in thread
from typing import Optional

from httpx import AsyncClient
from bs4 import BeautifulSoup, Tag

from .base import MangaParser
from .models import PartialManga, Manga, Release

BASE_URL = "https://readmanga.live"
SEARCH_URL = f"{BASE_URL}/search"


def parse_search_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    tiles_row = soup.find("div", "tiles")

    if not tiles_row:
        return []

    tiles_elements = tiles_row.find_all("div", "tile")[:5]
    tiles = []

    for tile_element in tiles_elements:
        info: Tag = tile_element.find("div", "desc").find("h3").find("a")

        tiles.append({"name": info.get("title"), "url": info.get("href")})

    return tiles


def parse_latest_release(html: str):
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("a", "read-last-chapter")

    if not tag:
        return

    data = tag.text.strip().split()

    return {"volume": int(data[1]), "chapter": int(data[3])}


def parse_title_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("a", "read-last-chapter")

    if not tag:
        return

    data = tag.text.strip().split()
    name = soup.find("h1", "names").find("span", "name").text
    image_url = soup.find("div", "picture-fotorama").find("img").get("src")

    return {"name": name, "volume": int(data[1]), "chapter": int(data[3]), "image_url": image_url}


class ReadManga(MangaParser):
    def __init__(self):
        self.client = AsyncClient(
            headers={"User-Agent": "MangaNotification Telegram Bot"}
        )

    async def search(self, query: str):
        data = {"q": query, "+": "Искать!", "fast-filter": "CREATION"}

        response = await self.client.post(
            SEARCH_URL,
            data=data,
        )
        res = parse_search_page(response.text)

        return [PartialManga(**manga) for manga in res]

    async def get_info(self, urn: str) -> Optional[Manga]:
        response = await self.client.get(f"{BASE_URL}{urn}")
        data = parse_title_page(response.text)

        if data:
            return Manga(**data)

    async def get_latest_release(self, urn: str) -> Optional[Release]:
        response = await self.client.get(f"{BASE_URL}{urn}")
        data = parse_latest_release(response.text)

        if data:
            return Release(**data)
