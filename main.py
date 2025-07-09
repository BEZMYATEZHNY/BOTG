import logging
import asyncio
import os
import json
import secrets
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
DELETE_DELAY = 5
SETTINGS_DIR = "Settings"
MESSAGES_FILE = "stored_messages.json"
USER_LAST_MESSAGE = {}
SENT_MESSAGES = []

# Стандартные настройки
DEFAULT_SETTINGS = {
    'welcome_text': "₊⊹  Приветик⋆˚꩜｡\n\nೀ 🍨 ‧ ˚ 🎀 ⊹˚. ♡\n\n♡⸝⸝  Я ботик для анонимных сообщений :3\n˚ʚОтправь мне сообщение - и я его доставлю куда нужноɞ˚\n🐾 by @Bbl_KOH4EHblE",
    'welcome_gif': "https://media.tenor.com/4YmoLrHy-yoAAAAi/vtuber-anime-girl.gif",
    'channel_template': "💬 {content}",
    'tagline': "💌 Анонимное сообщение",
    'notify_owner': True,
    'accumulate_mode': False,
}

# Создание папки Settings и файлов настроек если их нет
def initialize_settings():
    """Создает папку Settings и файлы настроек с дефолтными значениями"""
    try:
        # Создаем папку если её нет
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)
            logger.info(f"Создана папка настроек: {SETTINGS_DIR}")
        
        # Список файлов настроек
        setting_files = {
            'welcome_text.txt': DEFAULT_SETTINGS['welcome_text'],
            'welcome_gif.txt': DEFAULT_SETTINGS['welcome_gif'],
            'channel_template.txt': DEFAULT_SETTINGS['channel_template'],
            'tagline.txt': DEFAULT_SETTINGS['tagline'],
        }
        
        # Создаем файлы с дефолтными значениями
        for filename, default_value in setting_files.items():
            file_path = os.path.join(SETTINGS_DIR, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(default_value)
                logger.info(f"Создан файл настроек: {filename}")
        
        logger.info("Настройки инициализированы")
    except Exception as e:
        logger.error(f"Ошибка инициализации настроек: {e}")

# Инициализация настроек при импорте
initialize_settings()

# Функции для работы с файлами настроек
def load_setting(setting_name):
    """Загружает настройку из файла"""
    try:
        file_path = os.path.join(SETTINGS_DIR, f"{setting_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return DEFAULT_SETTINGS.get(setting_name, "")
    except Exception as e:
        logger.error(f"Ошибка загрузки {setting_name}: {e}")
        return DEFAULT_SETTINGS.get(setting_name, "")

def load_all_settings():
    """Загружает все настройки из файлов"""
    return {
        'welcome_text': load_setting('welcome_text'),
        'welcome_gif': load_setting('welcome_gif'),
        'channel_template': load_setting('channel_template'),
        'tagline': load_setting('tagline'),
        'notify_owner': DEFAULT_SETTINGS['notify_owner'],
        'accumulate_mode': DEFAULT_SETTINGS['accumulate_mode']
    }

# Загрузка сообщений
def load_messages():
    """Загружает сообщения из файла"""
    try:
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки сообщений: {e}")
        return {}

def save_messages():
    """Сохраняет сообщения в файл"""
    try:
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(stored_messages, f, indent=4, default=str)
        logger.info("Сообщения сохранены")
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщений: {e}")

# Инициализация данных
bot_settings = load_all_settings()
stored_messages = load_messages()

# Генерация уникальной ссылки
def generate_invite_link(context):
    code = secrets.token_urlsafe(6)[:8]
    bot_username = context.bot.username
    return f"https://t.me/{bot_username}?start={code}"

# Приветственное сообщение
async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    try:
        await update.message.reply_animation(
            animation=bot_settings['welcome_gif'],
            caption=bot_settings['welcome_text'],
            parse_mode=None
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке приветствия: {e}")
        await update.message.reply_text(bot_settings['welcome_text'])

# Админ-панель
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != context.bot_data['OWNER_ID']:
        await update.message.reply_text("⛔️ Доступ запрещен!")
        return
    
    new_count = sum(1 for user_msgs in stored_messages.values() for msg in user_msgs if not msg.get('viewed', False))
    total_count = sum(len(msgs) for msgs in stored_messages.values())
    
    keyboard = [
        [InlineKeyboardButton(f"💌 Сообщения ({new_count}/{total_count})", callback_data="view_messages")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("⚙️ Основные настройки", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 *Админ-панель* ✨\n\n"
        "Выбери действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Основные настройки
async def show_main_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"🔔 Уведомления: {'✅ ВКЛ' if bot_settings['notify_owner'] else '❌ ВЫКЛ'}",
                callback_data="toggle_notify"
            )
        ],
        [
            InlineKeyboardButton(
                f"📦 Накопление: {'✅ ВКЛ' if bot_settings['accumulate_mode'] else '❌ ВЫКЛ'}",
                callback_data="toggle_accumulate"
            )
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ *Основные настройки* ✨\n\n"
        f"🔔 Уведомления: {'Включены' if bot_settings['notify_owner'] else 'Выключены'}\n"
        f"📦 Режим накопления: {'Включен' if bot_settings['accumulate_mode'] else 'Выключен'}\n\n"
        "ℹ️ Настройки контента (приветствие, гифка, формат сообщений) редактируются "
        "только через файлы в папке Settings",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Просмотр сообщений
async def view_accumulated_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not stored_messages:
        await query.edit_message_text("📭 Нет накопленных сообщений!")
        return
    
    keyboard = []
    for user_id, messages in stored_messages.items():
        new_count = sum(1 for msg in messages if not msg.get('viewed', False))
        username = messages[0].get('username', 'без @username')
        full_name = messages[0].get('full_name', 'Неизвестный')
        
        keyboard.append([
            InlineKeyboardButton(
                f"{full_name} (@{username}) - {len(messages)} сообщ. ({new_count} новых)",
                callback_data=f"user_msgs_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📬 *Накопленные сообщения* ✨\n\n"
        "Выберите пользователя для просмотра:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Просмотр сообщений пользователя
async def view_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.replace("user_msgs_", "")
    messages = stored_messages.get(user_id, [])
    
    if not messages:
        await query.answer("❌ Нет сообщений!")
        return
    
    # Помечаем как просмотренные
    for msg in messages:
        msg['viewed'] = True
    save_messages()
    
    # Формируем список
    message_list = []
    for i, msg in enumerate(messages, 1):
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%d.%m.%Y %H:%M")
        content_preview = msg['content'][:100] + ('...' if len(msg['content']) > 100 else '')
        message_list.append(f"📩 *Сообщение #{i}* ({timestamp}):\n{content_preview}")
    
    text = "\n\n".join(message_list)
    full_name = messages[0].get('full_name', 'Неизвестный')
    username = messages[0].get('username', 'без @username')
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="view_messages")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📭 *Сообщения от {full_name} (@{username})* ✨\n\n{text}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Генерация ссылки
async def generate_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    invite_link = generate_invite_link(context)
    
    keyboard = [[
        InlineKeyboardButton("📤 Поделиться", url=f"https://t.me/share/url?url={invite_link}&text=Задай мне анонимный вопрос! ✨")
    ], [InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 *Ваша ссылка для вопросов* ✨\n\n"
        f"Используйте эту ссылку:\n\n"
        f"👉 `{invite_link}`\n\n"
        "Нажмите кнопку ниже, чтобы поделиться:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "view_messages":
        await view_accumulated_messages(update, context)
    elif query.data == "get_link":
        await generate_link(update, context)
    elif query.data == "main_settings":
        await show_main_settings(update, context)
    elif query.data == "toggle_notify":
        bot_settings['notify_owner'] = not bot_settings['notify_owner']
        await show_main_settings(update, context)
    elif query.data == "toggle_accumulate":
        bot_settings['accumulate_mode'] = not bot_settings['accumulate_mode']
        await show_main_settings(update, context)
    elif query.data.startswith("user_msgs_"):
        await view_user_messages(update, context)
    elif query.data in ["back_to_admin", "back_to_main"]:
        await admin_panel_callback(update, context)

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome_message(update, context)

# Автоудаление сообщений
async def auto_delete_messages(context: CallbackContext):
    global SENT_MESSAGES
    current_time = datetime.now()
    
    for msg_data in SENT_MESSAGES[:]:
        if (current_time - msg_data['timestamp']) > timedelta(minutes=25):
            try:
                await context.bot.delete_message(
                    chat_id=msg_data['chat_id'],
                    message_id=msg_data['message_id']
                )
                SENT_MESSAGES.remove(msg_data)
                logger.info(f"Сообщение удалено: {msg_data['message_id']}")
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")

# Отправка в канал
async def send_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Антиспам
        user_id = update.message.from_user.id
        current_time = datetime.now()
        
        if user_id in USER_LAST_MESSAGE:
            if (current_time - USER_LAST_MESSAGE[user_id]).seconds < 10:
                warning = await update.message.reply_text("⏳ Подождите 10 секунд!")
                await asyncio.sleep(3)
                await warning.delete()
                return
        USER_LAST_MESSAGE[user_id] = current_time
        
        # Пропуск команд
        if update.message.text and update.message.text.startswith('/'):
            return
            
        user = update.message.from_user
        content = update.message.text or update.message.caption or "Медиа-файл"
        
        # Форматирование сообщения
        formatted_message = bot_settings['channel_template'].format(content=content)
        
        # Отправка в канал
        sent_message = None
        if update.message.text:
            sent_message = await context.bot.send_message(
                chat_id=context.bot_data['CHANNEL_ID'],
                text=formatted_message
            )
        elif update.message.photo:
            sent_message = await context.bot.send_photo(
                chat_id=context.bot_data['CHANNEL_ID'],
                photo=update.message.photo[-1].file_id,
                caption=formatted_message
            )
        elif update.message.video:
            sent_message = await context.bot.send_video(
                chat_id=context.bot_data['CHANNEL_ID'],
                video=update.message.video.file_id,
                caption=formatted_message
            )
        elif update.message.document:
            sent_message = await context.bot.send_document(
                chat_id=context.bot_data['CHANNEL_ID'],
                document=update.message.document.file_id,
                caption=formatted_message
            )
        elif update.message.audio:
            sent_message = await context.bot.send_audio(
                chat_id=context.bot_data['CHANNEL_ID'],
                audio=update.message.audio.file_id,
                caption=formatted_message
            )
        elif update.message.voice:
            sent_message = await context.bot.send_voice(
                chat_id=context.bot_data['CHANNEL_ID'],
                voice=update.message.voice.file_id,
                caption=formatted_message
            )
        elif update.message.sticker:
            sent_message = await context.bot.send_sticker(
                chat_id=context.bot_data['CHANNEL_ID'],
                sticker=update.message.sticker.file_id
            )
        elif update.message.animation:
            sent_message = await context.bot.send_animation(
                chat_id=context.bot_data['CHANNEL_ID'],
                animation=update.message.animation.file_id,
                caption=formatted_message
            )
        
        # Сохранение для автоудаления
        if sent_message:
            SENT_MESSAGES.append({
                'message_id': sent_message.message_id,
                'chat_id': context.bot_data['CHANNEL_ID'],
                'timestamp': datetime.now()
            })
        
        # Сохранение для владельца
        user_id = str(user.id)
        if user_id not in stored_messages:
            stored_messages[user_id] = []
        
        stored_messages[user_id].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'text',
            'content': content,
            'full_name': user.full_name,
            'username': user.username,
            'viewed': False
        })
        save_messages()
        
        # Подтверждение
        confirmation = await update.message.reply_text(
            "✨ *Сообщение отправлено!* 💖\n"
            "Это подтверждение исчезнет через несколько секунд...",
            parse_mode="Markdown"
        )
        await update.message.delete()
        await asyncio.sleep(DELETE_DELAY)
        await confirmation.delete()
        
        # Статистика
        context.bot_data['message_count'] = context.bot_data.get('message_count', 0) + 1
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Не удалось отправить сообщение!")

# Админ-панель через callback
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    new_count = sum(1 for user_msgs in stored_messages.values() for msg in user_msgs if not msg.get('viewed', False))
    total_count = sum(len(msgs) for msgs in stored_messages.values())
    
    keyboard = [
        [InlineKeyboardButton(f"💌 Сообщения ({new_count}/{total_count})", callback_data="view_messages")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("⚙️ Основные настройки", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👑 *Админ-панель* ✨\n\nВыбери действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def main():
    from config import BOT_TOKEN, CHANNEL_ID, OWNER_ID
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['CHANNEL_ID'] = CHANNEL_ID
    application.bot_data['OWNER_ID'] = OWNER_ID
    application.bot_data['message_count'] = 0
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, 
        send_to_channel
    ))
    
    # Автоудаление
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_delete_messages, interval=60, first=10)
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main() import logging
import asyncio
import os
import json
import secrets
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
DELETE_DELAY = 5
SETTINGS_DIR = "Settings"
MESSAGES_FILE = "stored_messages.json"
USER_LAST_MESSAGE = {}
SENT_MESSAGES = []

# Стандартные настройки
DEFAULT_SETTINGS = {
    'welcome_text': "₊⊹  Приветик⋆˚꩜｡\n\nೀ 🍨 ‧ ˚ 🎀 ⊹˚. ♡\n\n♡⸝⸝  Я ботик для анонимных сообщений :3\n˚ʚОтправь мне сообщение - и я его доставлю куда нужноɞ˚\n🐾 by @Bbl_KOH4EHblE",
    'welcome_gif': "https://media.tenor.com/4YmoLrHy-yoAAAAi/vtuber-anime-girl.gif",
    'channel_template': "💬 {content}",
    'tagline': "💌 Анонимное сообщение",
    'notify_owner': True,
    'accumulate_mode': False,
}

# Создание папки Settings и файлов настроек если их нет
def initialize_settings():
    """Создает папку Settings и файлы настроек с дефолтными значениями"""
    try:
        # Создаем папку если её нет
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)
            logger.info(f"Создана папка настроек: {SETTINGS_DIR}")
        
        # Список файлов настроек
        setting_files = {
            'welcome_text.txt': DEFAULT_SETTINGS['welcome_text'],
            'welcome_gif.txt': DEFAULT_SETTINGS['welcome_gif'],
            'channel_template.txt': DEFAULT_SETTINGS['channel_template'],
            'tagline.txt': DEFAULT_SETTINGS['tagline'],
        }
        
        # Создаем файлы с дефолтными значениями
        for filename, default_value in setting_files.items():
            file_path = os.path.join(SETTINGS_DIR, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(default_value)
                logger.info(f"Создан файл настроек: {filename}")
        
        logger.info("Настройки инициализированы")
    except Exception as e:
        logger.error(f"Ошибка инициализации настроек: {e}")

# Инициализация настроек при импорте
initialize_settings()

# Функции для работы с файлами настроек
def load_setting(setting_name):
    """Загружает настройку из файла"""
    try:
        file_path = os.path.join(SETTINGS_DIR, f"{setting_name}.txt")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return DEFAULT_SETTINGS.get(setting_name, "")
    except Exception as e:
        logger.error(f"Ошибка загрузки {setting_name}: {e}")
        return DEFAULT_SETTINGS.get(setting_name, "")

def load_all_settings():
    """Загружает все настройки из файлов"""
    return {
        'welcome_text': load_setting('welcome_text'),
        'welcome_gif': load_setting('welcome_gif'),
        'channel_template': load_setting('channel_template'),
        'tagline': load_setting('tagline'),
        'notify_owner': DEFAULT_SETTINGS['notify_owner'],
        'accumulate_mode': DEFAULT_SETTINGS['accumulate_mode']
    }

# Загрузка сообщений
def load_messages():
    """Загружает сообщения из файла"""
    try:
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки сообщений: {e}")
        return {}

def save_messages():
    """Сохраняет сообщения в файл"""
    try:
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(stored_messages, f, indent=4, default=str)
        logger.info("Сообщения сохранены")
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщений: {e}")

# Инициализация данных
bot_settings = load_all_settings()
stored_messages = load_messages()

# Генерация уникальной ссылки
def generate_invite_link(context):
    code = secrets.token_urlsafe(6)[:8]
    bot_username = context.bot.username
    return f"https://t.me/{bot_username}?start={code}"

# Приветственное сообщение
async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    try:
        await update.message.reply_animation(
            animation=bot_settings['welcome_gif'],
            caption=bot_settings['welcome_text'],
            parse_mode=None
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке приветствия: {e}")
        await update.message.reply_text(bot_settings['welcome_text'])

# Админ-панель
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id != context.bot_data['OWNER_ID']:
        await update.message.reply_text("⛔️ Доступ запрещен!")
        return
    
    new_count = sum(1 for user_msgs in stored_messages.values() for msg in user_msgs if not msg.get('viewed', False))
    total_count = sum(len(msgs) for msgs in stored_messages.values())
    
    keyboard = [
        [InlineKeyboardButton(f"💌 Сообщения ({new_count}/{total_count})", callback_data="view_messages")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("⚙️ Основные настройки", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 *Админ-панель* ✨\n\n"
        "Выбери действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Основные настройки
async def show_main_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"🔔 Уведомления: {'✅ ВКЛ' if bot_settings['notify_owner'] else '❌ ВЫКЛ'}",
                callback_data="toggle_notify"
            )
        ],
        [
            InlineKeyboardButton(
                f"📦 Накопление: {'✅ ВКЛ' if bot_settings['accumulate_mode'] else '❌ ВЫКЛ'}",
                callback_data="toggle_accumulate"
            )
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ *Основные настройки* ✨\n\n"
        f"🔔 Уведомления: {'Включены' if bot_settings['notify_owner'] else 'Выключены'}\n"
        f"📦 Режим накопления: {'Включен' if bot_settings['accumulate_mode'] else 'Выключен'}\n\n"
        "ℹ️ Настройки контента (приветствие, гифка, формат сообщений) редактируются "
        "только через файлы в папке Settings",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Просмотр сообщений
async def view_accumulated_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not stored_messages:
        await query.edit_message_text("📭 Нет накопленных сообщений!")
        return
    
    keyboard = []
    for user_id, messages in stored_messages.items():
        new_count = sum(1 for msg in messages if not msg.get('viewed', False))
        username = messages[0].get('username', 'без @username')
        full_name = messages[0].get('full_name', 'Неизвестный')
        
        keyboard.append([
            InlineKeyboardButton(
                f"{full_name} (@{username}) - {len(messages)} сообщ. ({new_count} новых)",
                callback_data=f"user_msgs_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📬 *Накопленные сообщения* ✨\n\n"
        "Выберите пользователя для просмотра:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Просмотр сообщений пользователя
async def view_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.replace("user_msgs_", "")
    messages = stored_messages.get(user_id, [])
    
    if not messages:
        await query.answer("❌ Нет сообщений!")
        return
    
    # Помечаем как просмотренные
    for msg in messages:
        msg['viewed'] = True
    save_messages()
    
    # Формируем список
    message_list = []
    for i, msg in enumerate(messages, 1):
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%d.%m.%Y %H:%M")
        content_preview = msg['content'][:100] + ('...' if len(msg['content']) > 100 else '')
        message_list.append(f"📩 *Сообщение #{i}* ({timestamp}):\n{content_preview}")
    
    text = "\n\n".join(message_list)
    full_name = messages[0].get('full_name', 'Неизвестный')
    username = messages[0].get('username', 'без @username')
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="view_messages")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📭 *Сообщения от {full_name} (@{username})* ✨\n\n{text}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Генерация ссылки
async def generate_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    invite_link = generate_invite_link(context)
    
    keyboard = [[
        InlineKeyboardButton("📤 Поделиться", url=f"https://t.me/share/url?url={invite_link}&text=Задай мне анонимный вопрос! ✨")
    ], [InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 *Ваша ссылка для вопросов* ✨\n\n"
        f"Используйте эту ссылку:\n\n"
        f"👉 `{invite_link}`\n\n"
        "Нажмите кнопку ниже, чтобы поделиться:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "view_messages":
        await view_accumulated_messages(update, context)
    elif query.data == "get_link":
        await generate_link(update, context)
    elif query.data == "main_settings":
        await show_main_settings(update, context)
    elif query.data == "toggle_notify":
        bot_settings['notify_owner'] = not bot_settings['notify_owner']
        await show_main_settings(update, context)
    elif query.data == "toggle_accumulate":
        bot_settings['accumulate_mode'] = not bot_settings['accumulate_mode']
        await show_main_settings(update, context)
    elif query.data.startswith("user_msgs_"):
        await view_user_messages(update, context)
    elif query.data in ["back_to_admin", "back_to_main"]:
        await admin_panel_callback(update, context)

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome_message(update, context)

# Автоудаление сообщений
async def auto_delete_messages(context: CallbackContext):
    global SENT_MESSAGES
    current_time = datetime.now()
    
    for msg_data in SENT_MESSAGES[:]:
        if (current_time - msg_data['timestamp']) > timedelta(minutes=25):
            try:
                await context.bot.delete_message(
                    chat_id=msg_data['chat_id'],
                    message_id=msg_data['message_id']
                )
                SENT_MESSAGES.remove(msg_data)
                logger.info(f"Сообщение удалено: {msg_data['message_id']}")
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")

# Отправка в канал
async def send_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Антиспам
        user_id = update.message.from_user.id
        current_time = datetime.now()
        
        if user_id in USER_LAST_MESSAGE:
            if (current_time - USER_LAST_MESSAGE[user_id]).seconds < 10:
                warning = await update.message.reply_text("⏳ Подождите 10 секунд!")
                await asyncio.sleep(3)
                await warning.delete()
                return
        USER_LAST_MESSAGE[user_id] = current_time
        
        # Пропуск команд
        if update.message.text and update.message.text.startswith('/'):
            return
            
        user = update.message.from_user
        content = update.message.text or update.message.caption or "Медиа-файл"
        
        # Форматирование сообщения
        formatted_message = bot_settings['channel_template'].format(content=content)
        
        # Отправка в канал
        sent_message = None
        if update.message.text:
            sent_message = await context.bot.send_message(
                chat_id=context.bot_data['CHANNEL_ID'],
                text=formatted_message
            )
        elif update.message.photo:
            sent_message = await context.bot.send_photo(
                chat_id=context.bot_data['CHANNEL_ID'],
                photo=update.message.photo[-1].file_id,
                caption=formatted_message
            )
        elif update.message.video:
            sent_message = await context.bot.send_video(
                chat_id=context.bot_data['CHANNEL_ID'],
                video=update.message.video.file_id,
                caption=formatted_message
            )
        elif update.message.document:
            sent_message = await context.bot.send_document(
                chat_id=context.bot_data['CHANNEL_ID'],
                document=update.message.document.file_id,
                caption=formatted_message
            )
        elif update.message.audio:
            sent_message = await context.bot.send_audio(
                chat_id=context.bot_data['CHANNEL_ID'],
                audio=update.message.audio.file_id,
                caption=formatted_message
            )
        elif update.message.voice:
            sent_message = await context.bot.send_voice(
                chat_id=context.bot_data['CHANNEL_ID'],
                voice=update.message.voice.file_id,
                caption=formatted_message
            )
        elif update.message.sticker:
            sent_message = await context.bot.send_sticker(
                chat_id=context.bot_data['CHANNEL_ID'],
                sticker=update.message.sticker.file_id
            )
        elif update.message.animation:
            sent_message = await context.bot.send_animation(
                chat_id=context.bot_data['CHANNEL_ID'],
                animation=update.message.animation.file_id,
                caption=formatted_message
            )
        
        # Сохранение для автоудаления
        if sent_message:
            SENT_MESSAGES.append({
                'message_id': sent_message.message_id,
                'chat_id': context.bot_data['CHANNEL_ID'],
                'timestamp': datetime.now()
            })
        
        # Сохранение для владельца
        user_id = str(user.id)
        if user_id not in stored_messages:
            stored_messages[user_id] = []
        
        stored_messages[user_id].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'text',
            'content': content,
            'full_name': user.full_name,
            'username': user.username,
            'viewed': False
        })
        save_messages()
        
        # Подтверждение
        confirmation = await update.message.reply_text(
            "✨ *Сообщение отправлено!* 💖\n"
            "Это подтверждение исчезнет через несколько секунд...",
            parse_mode="Markdown"
        )
        await update.message.delete()
        await asyncio.sleep(DELETE_DELAY)
        await confirmation.delete()
        
        # Статистика
        context.bot_data['message_count'] = context.bot_data.get('message_count', 0) + 1
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Не удалось отправить сообщение!")

# Админ-панель через callback
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    new_count = sum(1 for user_msgs in stored_messages.values() for msg in user_msgs if not msg.get('viewed', False))
    total_count = sum(len(msgs) for msgs in stored_messages.values())
    
    keyboard = [
        [InlineKeyboardButton(f"💌 Сообщения ({new_count}/{total_count})", callback_data="view_messages")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("⚙️ Основные настройки", callback_data="main_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👑 *Админ-панель* ✨\n\nВыбери действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def main():
    from config import BOT_TOKEN, CHANNEL_ID, OWNER_ID
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['CHANNEL_ID'] = CHANNEL_ID
    application.bot_data['OWNER_ID'] = OWNER_ID
    application.bot_data['message_count'] = 0
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, 
        send_to_channel
    ))
    
    # Автоудаление
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_delete_messages, interval=60, first=10)
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
