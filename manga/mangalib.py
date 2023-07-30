import asyncio
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
from typing import Callable, Union
from urllib.parse import quote

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from manga.base import MangaParser
from manga.models import PartialManga
from ptb.inner_types import AsyncCallable


def run_in_thread(func: Union[AsyncCallable, Callable]):
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    return wrapper


def build_chrome_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


URL = "https://mangalib.me"
time_format = "%d.%m.%Y"
xpath = (
    '//*[@id="main-page"]/div/div/div/div[2]/div[2]/div[3]/div/div[1]/div[1]/div[2]/div[{index}]'
)


def get_search_url(query: str) -> str:
    return f"https://{URL}/manga-list?sort=rate&dir=desc&page=1&name={quote(query)}"


class MangalibParser(MangaParser):
    def __init__(self) -> None:
        self.driver = build_chrome_driver()
        self.not_processing = asyncio.Event()

        self.not_processing.set()

    @run_in_thread
    async def search(self, query: str) -> list[PartialManga]:
        self.driver.get(get_search_url(query))

        data = []
        elements = []

        with suppress(NoSuchElementException):
            elements = self.driver.find_elements(By.CLASS_NAME, "media-card")

        for element in elements:
            url = element.get_attribute("href")
            name = element.find_element(By.CLASS_NAME, "media-card__title")
            data.append({"name": name, "url": url})

        return [PartialManga(**manga) for manga in data]

    # OLD

    @run_in_thread
    def get_info(self, url: str):
        if self.blocked:
            return

        self.driver.get(url=url)

        if self.blocked:
            return

        data = {
            "name": self.driver.find_element(By.CLASS_NAME, "media-name__main").text,
            "url": url,
        }

        image_card = self.driver.find_element(By.CLASS_NAME, "media-sidebar__cover")
        data["image_url"] = image_card.find_element(By.XPATH, "img").get_attribute("src")

        self.driver.get(url=f"{url}?section=chapters")

        last_chapter_data = self._get_latest_release()
        data["last_chapter"] = last_chapter_data

    @property
    def blocked(self) -> bool:
        if not self.has_header:
            return False

        url = self.driver.current_url
        logging.warning("Received captcha. Reloading driver")
        self.driver.close()

        self.driver = build_chrome_driver()
        self.driver.get(url)
        if self.has_header:
            logging.warning("Captcha still here. Returning empty response")
            return True
        return False

    @property
    def has_header(self) -> bool:
        with suppress(NoSuchElementException):
            return not self.driver.find_element(By.CLASS_NAME, "header")
        return True

    def _get_latest_release(self) -> dict | None:
        try:
            chapter_data = self.driver.find_element(By.CLASS_NAME, "media-chapter")
            chapter_data = chapter_data.find_element(By.CLASS_NAME, "link-default")
            chapter_name = chapter_data.text.splitlines()
            if not chapter_name:
                return
            chapter_name = chapter_name[0]
            chapter_url = chapter_data.get_attribute("href")
        except NoSuchElementException:
            # Тайтл имеет несколько переводов, поэтому начальная страница пустая
            return self.get_chapter_from_team()

        return {"name": chapter_name, "url": chapter_url}

    def get_chapter_from_team(self):
        team_list = self.driver.find_element(By.CLASS_NAME, "team-list")
        teams: list[WebElement] = team_list.find_elements(By.CLASS_NAME, "team-list-item")

        data = {}

        for i in range(len(teams)):
            team = team_list.find_element(By.XPATH, xpath.format(index=i + 1))
            # Получаем элемент через XPATH, т.к. иначе на него нельзя нажать
            team.click()
            # Нажимаем, чтобы получить все части перевода от команды

            chapter = self._get_latest_team_chapter()
            chapter_url = chapter.find_element(By.CLASS_NAME, "link-default").get_attribute("href")
            chapter_data = chapter.text.splitlines()
            time = chapter_data[2]
            dtime = datetime.datetime.strptime(time, time_format)
            data[dtime] = {"name": chapter_data[0], "url": chapter_url}

        return self.filter_chapters_by_time(data)

    def _get_latest_team_chapter(self) -> WebElement:
        chapters = self.driver.find_elements(By.CLASS_NAME, "vue-recycle-scroller__item-view")
        for chapter in chapters:
            attr = chapter.get_attribute("style")
            if attr == "transform: translateY(0px);":
                # При переключении команд, предыдущие главы скрываются css свойством,
                # при этом, они всё ещё присутствуют в списке, поэтому их надо игнорить
                return chapter.find_element(By.CLASS_NAME, "media-chapter")

    @staticmethod
    def filter_chapters_by_time(data: dict[datetime.datetime, dict[str, str]]):
        return data[max(data)]

    def get_latest_chapter(self, url: str) -> Chapter:
        if "section=chapters" not in url:
            url += "?section=chapters"

        self.driver.get(url)
        chapter_data = self._get_latest_release()
