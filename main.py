import re
from os import environ

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, filters
from dotenv import load_dotenv
from beanie import init_beanie, WriteRules
from motor.motor_asyncio import AsyncIOMotorClient

from handlers.decorators import callback_query, command, message, startup
from handlers.conversation import Conversation
from core import Client
from manga.readmanga import ReadManga
from database.models import User, Manga, SiteType

load_dotenv()

client = Client()
read_manga = ReadManga()

SEARCH_BUTTON = "🔍 Поиск"
SUBSCRIPTIONS_BUTTON = "❤️ Подписки"
MENU_BUTTONS = [SEARCH_BUTTON, SUBSCRIPTIONS_BUTTON]

conversation = Conversation()
START, SEARCH, SELECT, SUBSCRIBE = conversation.States.generate_state(4)


@startup
async def on_startup():
    await init_beanie(
        database=AsyncIOMotorClient(environ["MONGODB_URL"]).manga_notifs_bot,
        document_models=[User, Manga]
    )
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
        context.user_data["manga_list"][str(i)] = titles[i]['url']

    await update.message.reply_text(f"Найдено {len(titles)} тайтлов", reply_markup=InlineKeyboardMarkup(keyboard))

    return SELECT


@conversation.state(SELECT)
@callback_query(re.compile("search:"))
async def on_title_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = update.callback_query.data.removeprefix("search:")
    urn = context.user_data["manga_list"][index]
    data = await read_manga.get_latest_chapter(urn)

    keyboard = [
        [
            InlineKeyboardButton("Подписаться", callback_data=f"sub:{index}")
        ]
    ]

    await update.effective_message.delete()
    await update.callback_query.answer()
    await update.effective_chat.send_message(
        f"{data['name']}\nПоследняя глава: {data['volume']}-{data['chapter']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data["manga"] = Manga(
        type=SiteType.READMANGA,
        name=data["name"],
        urn=urn,
        chapter=f"{data['volume']}-{data['chapter']}"
    )

    return SUBSCRIBE


@conversation.state(SUBSCRIBE)
@callback_query(re.compile("sub:"))
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO: Проверить, если уже подписан
    # TODO: Проверить, если манга уже есть в базе
    manga: Manga = context.user_data["manga"]

    user = await User.find_one(User.id == update.effective_user.id)
    if not user:
        user = User(id=update.effective_user.id, subscriptions=[])
        await user.create()

    # noinspection PyTypeChecker
    user.subscriptions.append(manga)
    await user.save(link_rule=WriteRules.WRITE)

    await update.effective_message.delete()
    await update.callback_query.answer()
    await update.effective_chat.send_message(f"Вы успешно подписались на {manga.name}")

    return conversation.States.END


@conversation.fallback()
@command()
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Поиск отменён")

    return conversation.States.END

# TODO: Просмотр подписок
# TODO: Отписка
# TODO: парсинг картинок

client.run(environ["TELEGRAM_BOT_TOKEN"])
