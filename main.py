from asyncio import create_task, new_event_loop, set_event_loop
import re
from os import environ

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes, filters
from dotenv import load_dotenv
from beanie import init_beanie, WriteRules
from beanie.operators import And
from motor.motor_asyncio import AsyncIOMotorClient

from ptb import Client, Conversation, callback_query, command, message, startup
from manga.readmanga import ReadManga
from database.models import TelegramChat, Manga, SiteType
from consts import SITES

load_dotenv()

client = Client()
read_manga = ReadManga()

SEARCH_BUTTON = "🔍 Поиск"
SUBSCRIPTIONS_BUTTON = "❤️ Подписки"
MENU_BUTTONS = [SEARCH_BUTTON, SUBSCRIPTIONS_BUTTON]

conversation = Conversation()
START, SEARCH, SELECT, SUBSCRIBE = conversation.States.generate_state(4)


def send_notification(chat: TelegramChat, manga: Manga):
    create_task(
        client.bot.send_message(
            chat.id,
            f"Вышла новая глава {manga.name}\n\n{manga.volume}-{manga.chapter}",
        )
    )


async def send_notifications(manga: Manga):
    # noinspection PyTypeChecker
    chats = await TelegramChat.find(
        And(
            TelegramChat.subscriptions.type == manga.type,
            TelegramChat.subscriptions.urn == manga.urn,
        ),
        fetch_links=True,
    ).to_list()

    [send_notification(chat, manga) for chat in chats]


async def fetch_data(context: ContextTypes.DEFAULT_TYPE):
    all_mangas = Manga.find_all()

    async for manga in all_mangas:
        if manga.type == SiteType.READMANGA:
            new = await read_manga.get_latest_chapter(manga.urn)

        if new["volume"] > manga.volume or new["chapter"] > manga.chapter:
            manga.volume = new["volume"]
            manga.chapter = new["chapter"]

            await manga.save()
            await send_notifications(manga)


@startup
async def on_startup():
    await init_beanie(
        database=AsyncIOMotorClient(environ["MONGODB_URL"]).manga_notifs_bot,
        document_models=[TelegramChat, Manga],
    )
    job = client.job_queue.run_repeating(fetch_data, interval=60 * 60)
    await job.run(client.app)

    print(f"{client.bot.username} started")


@command()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(text) for text in MENU_BUTTONS]]

    await update.message.reply_text(
        "Хай", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


@conversation.entry_point()
@message(filters.Text([SEARCH_BUTTON]))
async def find_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название тайтла\n\n/cancel - для отмены")

    return SEARCH


@conversation.state(SEARCH)
@message(filters.TEXT & ~filters.COMMAND)
async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in MENU_BUTTONS:
        return

    titles = await read_manga.search(text)

    keyboard = []
    context.user_data["manga_list"] = {}

    for i in range(len(titles)):
        keyboard.append(
            [InlineKeyboardButton(titles[i]["name"], callback_data=f"search:{i}")]
        )
        context.user_data["manga_list"][str(i)] = titles[i]["url"]

    await update.message.reply_text(
        f"Найдено {len(titles)} тайтлов", reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECT


@conversation.state(SELECT)
@callback_query(re.compile("search:"))
async def on_title_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = update.callback_query.data.removeprefix("search:")
    urn = context.user_data["manga_list"][index]
    context.user_data.pop("manga_list")

    data = await read_manga.get_latest_chapter(urn)

    keyboard = [[InlineKeyboardButton("Подписаться", callback_data=f"sub:{index}")]]

    await update.effective_message.delete()
    await update.callback_query.answer()
    await update.effective_chat.send_message(
        f"{data['name']}\nПоследняя глава: {data['volume']}-{data['chapter']}\n{data['image_url']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    context.user_data["manga"] = Manga(
        type=SiteType.READMANGA,
        name=data["name"],
        urn=urn,
        chapter=data["chapter"],
        volume=data["volume"],
    )

    return SUBSCRIBE


@conversation.state(SUBSCRIBE)
@callback_query(re.compile("sub:"))
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manga: Manga = context.user_data["manga"]

    db_manga = await Manga.find_one(
        And(
            Manga.type == manga.type,
            Manga.urn == manga.urn,
        )
    )

    if not db_manga:
        await manga.create()
    else:
        manga = db_manga

    chat_id = str(update.effective_chat.id)
    chat = await TelegramChat.find_one(TelegramChat.id == chat_id, fetch_links=True)

    if not chat:
        chat = TelegramChat(id=chat_id, subscriptions=[])
        await chat.create()

    await update.effective_message.delete()
    await update.callback_query.answer()

    if chat.has_subscription(manga):
        await update.effective_chat.send_message(f"Вы уже подписаны на этот тайтл")
    else:
        # noinspection PyTypeChecker
        chat.subscriptions.append(manga)
        await chat.save(link_rule=WriteRules.DO_NOTHING)

        await update.effective_chat.send_message(f"Вы успешно подписались на {manga.name}")

    return conversation.States.END


@conversation.fallback()
@command()
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Поиск отменён")

    return conversation.States.END


@command(description="Просмотр ваших подписок")
async def subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = await TelegramChat.find_one(TelegramChat.id == str(update.effective_chat.id), fetch_links=True)

    if not chat or not chat.subscriptions:
        await update.message.reply_text("У вас нет подписок")

    text = ""
    unsub_btns = []
    i = -1
    context.user_data["unsub_list"] = {}

    for index, manga in enumerate(chat.subscriptions, start=0):
        manga: Manga
        text += f"{index + 1}. {manga.name} в {SITES[manga.type]}"
        if index % 5 == 0:
            unsub_btns.append([])
            i += 1

        unsub_btns[i].append(InlineKeyboardButton(str(index + 1), callback_data=f"unsub:{index}"))
        context.user_data["unsub_list"][str(index)] = manga

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(unsub_btns))


@callback_query(re.compile("unsub:"))
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = update.callback_query.data.removeprefix("unsub:")
    manga: Manga = context.user_data["unsub_list"][index]
    context.user_data.pop("unsub_list")

    await update.effective_message.delete()

    chat = await TelegramChat.get(str(update.effective_chat.id), fetch_links=True)
    chat.unsubscribe(manga)
    await chat.save()

    await update.callback_query.answer()
    await update.effective_chat.send_message("Успешно отписано")


client.run(environ["TELEGRAM_BOT_TOKEN"])
