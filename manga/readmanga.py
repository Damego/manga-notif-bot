# TODO: Run parsing in thread

from httpx import AsyncClient
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://readmanga.live"
SEARCH_URL = f"{BASE_URL}/search"


class ReadManga:
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
        return self.parse_search_page(response.text)

    def parse_search_page(self, html: str):
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

    async def get_latest_chapter(self, urn: str):
        response = await self.client.get(f"{BASE_URL}{urn}")
        return self.parse_title_page(response.text)

    def parse_title_page(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        raw_data = soup.find("a", "read-last-chapter")

        if not raw_data:
            return

        data = raw_data.text.strip().split()
        name = soup.find("h1", "names").find("span", "name").text
        image_url = soup.find("div", "picture-fotorama").find("img").get("src")

        return {"name": name, "volume": int(data[1]), "chapter": int(data[3]), "image_url": image_url}
