import re
from os import environ

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, filters
from dotenv import load_dotenv

from handlers.decorators import callback_query, command, message, startup
from handlers.conversation import Conversation
from core import Client
from manga.readmanga import ReadManga
import logging
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()

client = Client()

read_manga = ReadManga()
active_search = []

SEARCH_BUTTON = "🔍 Поиск"
SUBSCRIPTIONS_BUTTON = "❤️ Подписки"
ignore_text = [SEARCH_BUTTON, SUBSCRIPTIONS_BUTTON]


conversation = Conversation()

START, SEARCH, SELECT, SUBSCRIBE = conversation.States.generate_state(4)


@startup
async def on_startup():
    print(f"{client.bot.username} started")


@conversation.entry_point()
@command()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(SEARCH_BUTTON), KeyboardButton(SUBSCRIPTIONS_BUTTON)]]

    await update.message.reply_text(
        "Хай", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return START


@conversation.state(START)
@message(filters.Text([SEARCH_BUTTON]))
async def find_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название тайтла")

    return SEARCH


@conversation.state(SEARCH)
@message(filters.TEXT & ~filters.COMMAND)
async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ignore_text:
        print("nope")
        return

    titles = await read_manga.search(text)

    keyboard = []
    context.user_data["manga"] = {}

    for i in range(len(titles)):
        keyboard.append(
            [InlineKeyboardButton(titles[i]["name"], callback_data=f"search:{i}")]
        )
        context.user_data["manga"][i] = titles[i]['url']

    await update.message.reply_text(f"Найдено {len(titles)} тайтлов", reply_markup=InlineKeyboardMarkup(keyboard))

    return SELECT


@conversation.state(SELECT)
@callback_query(re.compile("search:"))
async def on_title_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = update.callback_query.data.removeprefix("search:")
    urn = context.user_data["manga"][int(index)]

    data = await read_manga.get_latest_chapter(urn)

    keyboard = [
        [
            InlineKeyboardButton("Подписаться", callback_data=f"sub:{index}")
        ]
    ]
    await update.callback_query.answer()
    await update.effective_chat.send_message(
        f"{data['name']}\nПоследняя глава: {data['volume']}-{data['chapter']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SUBSCRIBE


@conversation.state(SUBSCRIBE)
@callback_query(re.compile("sub:"))
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = update.callback_query.data.removeprefix("sub:")
    print("подписано на", index)
    await update.callback_query.answer()

    return conversation.States.END


client.run(environ["TELEGRAM_BOT_TOKEN"])
