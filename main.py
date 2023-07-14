import re
from os import environ

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, filters
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
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
load_dotenv()

client = Client()

read_manga = ReadManga()
active_search = []

SEARCH_BUTTON = "🔍 Поиск"
SUBSCRIPTIONS_BUTTON = "❤️ Подписки"
ignore_text = [SEARCH_BUTTON, SUBSCRIPTIONS_BUTTON]


def generate_state(length: int):
    return map(str, range(length))


GENDER, PHOTO, LOCATION, BIO = generate_state(4)

conv = Conversation()


@conv.state(GENDER)
@command()
async def gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return PHOTO


@conv.entry_point()
@command()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about their gender."""
    reply_keyboard = [["Boy", "Girl", "Other"]]

    await update.message.reply_text(
        "Hi! My name is Professor Bot. I will hold a conversation with you. "
        "Send /cancel to stop talking to me.\n\n"
        "Are you a boy or a girl?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Boy or Girl?"
        ),
    )

    return GENDER


@conv.state(GENDER)
@message(filters.Regex("^(Boy|Girl|Other)$"))
async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected gender and asks for a photo."""
    user = update.message.from_user

    await update.message.reply_text(
        "I see! Please send me a photo of yourself, "
        "so I know what you look like, or send /skip if you don't want to.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return PHOTO


@conv.state(PHOTO)
@message(filters.PHOTO)
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo and asks for a location."""
    user = update.message.from_user
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive("user_photo.jpg")

    await update.message.reply_text(
        "Gorgeous! Now, send me your location please, or send /skip if you don't want to."
    )

    return LOCATION


@conv.state(PHOTO)
@command("skip", register=False)
async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the photo and asks for a location."""
    user = update.message.from_user

    await update.message.reply_text(
        "I bet you look great! Now, send me your location please, or send /skip."
    )

    return LOCATION


@conv.state(LOCATION)
@message(filters.LOCATION)
async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_location = update.message.location

    await update.message.reply_text(
        "Maybe I can visit you sometime! At last, tell me something about yourself."
    )

    return BIO


@conv.state(LOCATION)
@command("skip", register=False)
async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the location and asks for info about the user."""
    user = update.message.from_user

    await update.message.reply_text(
        "You seem a bit paranoid! At last, tell me something about yourself."
    )

    return BIO


@conv.state(BIO)
@message(filters.TEXT & ~filters.COMMAND)
async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the info about the user and ends the conversation."""
    user = update.message.from_user

    await update.message.reply_text("Thank you! I hope we can talk again some day.")

    return ConversationHandler.END


@conv.fallback()
@command()
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


SEARCH, SELECT = generate_state(2)


@startup
async def on_startup():
    print(f"{client.bot.username} started")


@command()
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(SEARCH_BUTTON), KeyboardButton(SUBSCRIPTIONS_BUTTON)]]

    await update.message.reply_text(
        "Хай", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


@message(filters.Text([SEARCH_BUTTON]))
async def find_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_search.append(update.effective_user.id)

    await update.message.reply_text("Введите название тайтла")

    return SEARCH


# @message(filters.TEXT & ~filters.COMMAND)
# async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     print(1)
#     if update.effective_user.id not in active_search:
#         return
#     active_search.remove(update.effective_user.id)
#
#     text = update.message.text
#     if text in ignore_text:
#         return
#
#     titles = await read_manga.search(text)
#
#     keyboard = [
#         [
#             InlineKeyboardButton(title["name"], callback_data=f"search:{title['url']}")
#         ]
#         for title in titles
#     ]
#
#     await update.message.reply_text(f"Найдено {len(titles)} тайтлов", reply_markup=InlineKeyboardMarkup(keyboard))
#


@callback_query(re.compile("search:"))
async def on_title_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urn = update.callback_query.data.removeprefix("search:")
    data = await read_manga.get_latest_chapter(urn)

    keyboard = [
        [
            InlineKeyboardButton("Подписаться", callback_data=f"sub:{urn}")
        ]
    ]
    await update.callback_query.answer(f"{data['name']}\nПоследняя глава: {data['volume']}-{data['chapter']}")

client.run(environ["TELEGRAM_BOT_TOKEN"])
