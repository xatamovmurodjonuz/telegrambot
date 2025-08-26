import asyncio
import logging
import json
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re

# Loggerni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot tokenini environment variable dan olish yoki to'g'ridan-to'g'ri yozish
API_TOKEN = os.getenv("BOT_TOKEN", "7261239478:AAGTCZ_KuTfmIF8wXBVYZKJ07yZ-gHdlE6A")

# Asosiy bot uchun
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DATA_FILE = "user_data.json"
WEBHOOK_URL = "https://your-server.com"  # O'z serveringiz manzilini qo'ying


def load_data():
    """Foydalanuvchi ma'lumotlarini yuklash"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ma'lumotlarni yuklashda xatolik: {e}")
        return {}


def save_data(data):
    """Foydalanuvchi ma'lumotlarini saqlash"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Ma'lumotlarni saqlashda xatolik: {e}")
        return False


def validate_token(token):
    """Token formati validatsiyasi"""
    pattern = r'^\d+:[a-zA-Z0-9_-]{35}$'
    return re.match(pattern, token) is not None


class BotCreation(StatesGroup):
    waiting_for_token = State()
    waiting_for_start_response = State()
    waiting_for_command = State()
    waiting_for_command_response = State()
    waiting_for_bot_selection = State()
    waiting_for_command_deletion = State()


# Asosiy menyu
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤖 Bot qo'shish"), KeyboardButton(text="📋 Mening botlarim")],
        [KeyboardButton(text="❌ Bot o'chirish"), KeyboardButton(text="ℹ️ Yordam")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Quyidagilardan birini tanlang..."
)

# Tasdiqlash tugmalari
confirmation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Ha"), KeyboardButton(text="❌ Yo'q")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


def get_bots_keyboard(user_id):
    """Foydalanuvchi botlari uchun inline keyboard yaratish"""
    data = load_data()
    user_bots = data.get(user_id, {})

    if not user_bots:
        return None

    builder = InlineKeyboardBuilder()
    for token, bot_data in user_bots.items():
        username = bot_data.get("bot_username", "Noma'lum")
        builder.button(
            text=f"@{username}",
            callback_data=f"bot_{token}"
        )

    builder.adjust(2)  # 2 ta tugma qatorida
    return builder.as_markup()


@dp.message(Command(commands=["start"]))
async def cmd_start(message: Message, state: FSMContext):
    """Start komandasi"""
    await state.clear()
    await message.answer(
        "🤖 Bot yaratish platformasiga xush kelibsiz!\n\n"
        "Bu yerdan o'zingizning Telegram botlaringizni yaratishingiz va boshqarishingiz mumkin.",
        reply_markup=main_menu
    )


@dp.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    """Yordam komandasi"""
    help_text = (
        "📖 <b>Bot Yordachi</b>\n\n"
        "🤖 <b>Bot qo'shish</b> - Yangi bot yaratish\n"
        "📋 <b>Mening botlarim</b> - Yaratilgan botlarni ko'rish\n"
        "❌ <b>Bot o'chirish</b> - Botni o'chirish\n\n"
        "📝 <b>Qo'llanma:</b>\n"
        "1. BotFather dan yangi bot yarating va token oling\n"
        "2. 'Bot qo'shish' tugmasini bosing\n"
        "3. Tokenni yuboring\n"
        "4. Komandalar va ularga javoblar belgilang\n"
        "5. Botingiz tayyor!\n\n"
        "⚠️ <b>Eslatma:</b> Botlaringiz faqat webhook server ishlaganda ishlaydi."
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Text(text="ℹ️ Yordam"))
async def help_button(message: Message):
    """Yordam tugmasi"""
    await cmd_help(message)


@dp.message(Text(text="🤖 Bot qo'shish"))
async def add_bot_start(message: Message, state: FSMContext):
    """Yangi bot qo'shishni boshlash"""
    await message.answer(
        "🤖 <b>Yangi bot qo'shish</b>\n\n"
        "BotFather dan olingan API tokenini yuboring:\n"
        "<code>123456789:AAHpfhi4x0dB6pgtmBreRZq9RX39mDc2YtI</code>\n\n"
        "❕ Token quyidagi formatda bo'lishi kerak: <code>raqam:harflar</code>",
        parse_mode="HTML"
    )
    await state.set_state(BotCreation.waiting_for_token)


@dp.message(BotCreation.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    """Tokenni qayta ishlash"""
    token = message.text.strip()
    user_id = str(message.from_user.id)

    # Token validatsiyasi
    if not validate_token(token):
        await message.answer(
            "❌ <b>Token noto'g'ri formatda!</b>\n\n"
            "Token quyidagicha bo'lishi kerak:\n"
            "<code>123456789:AAHpfhi4x0dB6pgtmBreRZq9RX39mDc2YtI</code>\n\n"
            "Iltimos, to'g'ri token yuboring yoki /start bilan qaytadan boshlang.",
            parse_mode="HTML"
        )
        return

    # Token tekshirish - Soddalashtirilgan versiya
    try:
        # To'g'ridan-to'g'ri Bot obyekti yaratish
        test_bot = Bot(token=token)
        me = await test_bot.get_me()
        await test_bot.session.close()

        # Token allaqachon mavjudligini tekshirish
        data = load_data()
        if user_id in data and token in data[user_id]:
            await message.answer(
                "⚠️ <b>Bu token allaqachon qo'shilgan!</b>\n\n"
                "Boshqa token yuboring yoki /start bilan qaytadan boshlang.",
                parse_mode="HTML"
            )
            return

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            await message.answer(
                "❌ <b>Token noto'g'ri yoki yopiq!</b>\n\n"
                "BotFather dan to'g'ri token olinganligini tekshiring.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"❌ <b>Xatolik yuz berdi:</b>\n<code>{error_msg[:100]}...</code>\n\n"
                "Iltimos, qaytadan urinib ko'ring.",
                parse_mode="HTML"
            )
        return

    # Ma'lumotlarni saqlash
    data = load_data()
    if user_id not in data:
        data[user_id] = {}

    data[user_id][token] = {
        "commands": {},
        "bot_username": me.username,
        "bot_first_name": me.first_name,
        "created_at": message.date.isoformat()
    }

    if save_data(data):
        await state.update_data(token=token)
        await message.answer(
            f"✅ <b>Token qabul qilindi!</b>\n\n"
            f"Bot: @{me.username}\n"
            f"Nomi: {me.first_name}\n\n"
            "Endi /start komandasi uchun javob matnini yozing:",
            parse_mode="HTML"
        )
        await state.set_state(BotCreation.waiting_for_start_response)
    else:
        await message.answer(
            "❌ <b>Ma'lumotlarni saqlashda xatolik!</b>\n\n"
            "Iltimos, qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )
        await state.clear()


@dp.message(BotCreation.waiting_for_start_response)
async def process_start_response(message: Message, state: FSMContext):
    """Start komandasi javobini qayta ishlash"""
    user_id = str(message.from_user.id)
    text = message.text.strip()
    state_data = await state.get_data()
    token = state_data.get("token")

    data = load_data()
    if user_id not in data or token not in data[user_id]:
        await message.answer(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Iltimos, /start bilan qaytadan boshlang.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    # Matn validatsiyasi
    if len(text) < 2 or len(text) > 1000:
        await message.answer(
            "❌ <b>Matn noto'g'ri uzunlikda!</b>\n\n"
            "Javob matni 2 dan 1000 ta belgigacha bo'lishi kerak.\n"
            "Qaytadan yuboring:",
            parse_mode="HTML"
        )
        return

    data[user_id][token]["commands"]["/start"] = text
    if save_data(data):
        await message.answer(
            "✅ <b>/start komandasi saqlandi!</b>\n\n"
            "Endi boshqa komanda qo'shishingiz mumkin:\n"
            "• Masalan: /help, /about, /info\n\n"
            "Yoki <b>'Tugatish'</b> deb yozib, bot yaratishni yakunlashingiz mumkin.",
            parse_mode="HTML"
        )
        await state.set_state(BotCreation.waiting_for_command)
    else:
        await message.answer(
            "❌ <b>Saqlashda xatolik!</b>\n\n"
            "Iltimos, qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )


@dp.message(BotCreation.waiting_for_command)
async def process_command(message: Message, state: FSMContext):
    """Yangi komanda qo'shish"""
    text = message.text.strip()
    user_id = str(message.from_user.id)
    state_data = await state.get_data()
    token = state_data.get("token")

    # Yakunlash
    if text.lower() in ["tugatish", "stop", "cancel", "done", "tayyor"]:
        # Webhook sozlash - Soddalashtirilgan versiya
        try:
            user_bot = Bot(token=token)

            # Avval webhook ni o'chirish
            try:
                await user_bot.delete_webhook(drop_pending_updates=True)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Webhook o'chirishda xatolik: {e}")

            # Yangi webhook sozlash
            webhook_url = f"{WEBHOOK_URL}/webhook/{user_id}/{token}"
            await user_bot.set_webhook(webhook_url, drop_pending_updates=True)
            await user_bot.session.close()

            data = load_data()
            bot_username = data[user_id][token].get("bot_username", "Noma'lum")
            commands_count = len(data[user_id][token].get("commands", {}))

            await message.answer(
                f"🎉 <b>Bot muvaffaqiyatli yaratildi!</b>\n\n"
                f"🤖 Bot: @{bot_username}\n"
                f"📊 Komandalar soni: {commands_count}\n\n"
                "✅ Endi sizning botingiz ishga tushdi!",
                parse_mode="HTML",
                reply_markup=main_menu
            )
        except Exception as e:
            error_msg = str(e)
            await message.answer(
                f"⚠️ <b>Bot yaratildi, lekin webhook sozlashda xatolik:</b>\n"
                f"<code>{error_msg[:200]}...</code>\n\n"
                "Iltimos, keyinroq qayta urinib ko'ring.",
                parse_mode="HTML",
                reply_markup=main_menu
            )

        await state.clear()
        return

    # Komanda validatsiyasi
    if not text.startswith("/"):
        await message.answer(
            "❌ <b>Komanda / bilan boshlanishi kerak!</b>\n\n"
            "Masalan: /help, /about, /info\n\n"
            "Qaytadan yuboring:",
            parse_mode="HTML"
        )
        return

    if len(text) > 32:
        await message.answer(
            "❌ <b>Komanda juda uzun!</b>\n\n"
            "Komanda 32 ta belgidan oshmasligi kerak.\n"
            "Qaytadan yuboring:",
            parse_mode="HTML"
        )
        return

    # Komanda allaqachon mavjudligini tekshirish
    data = load_data()
    if user_id in data and token in data[user_id]:
        if text in data[user_id][token]["commands"]:
            await message.answer(
                f"⚠️ <b>Komanda allaqachon mavjud!</b>\n\n"
                f"<code>{text}</code> komandasi uchun javob:\n"
                f"<i>{data[user_id][token]['commands'][text][:100]}...</i>\n\n"
                "Boshqa komanda yuboring yoki 'Tugatish' deb yozing:",
                parse_mode="HTML"
            )
            return

        data[user_id][token]["current_command"] = text
        if save_data(data):
            await message.answer(
                f"✅ <b>Komanda qabul qilindi:</b> <code>{text}</code>\n\n"
                "Endi ushbu komanda uchun javob matnini yozing:",
                parse_mode="HTML"
            )
            await state.set_state(BotCreation.waiting_for_command_response)
        else:
            await message.answer(
                "❌ <b>Saqlashda xatolik!</b>\n\n"
                "Iltimos, qaytadan urinib ko'ring.",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Iltimos, /start bilan qaytadan boshlang.",
            parse_mode="HTML"
        )
        await state.clear()


@dp.message(BotCreation.waiting_for_command_response)
async def process_command_response(message: Message, state: FSMContext):
    """Komanda javobini qayta ishlash"""
    user_id = str(message.from_user.id)
    state_data = await state.get_data()
    token = state_data.get("token")
    data = load_data()

    if user_id not in data or token not in data[user_id]:
        await message.answer(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Iltimos, /start bilan qaytadan boshlang.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    current_cmd = data[user_id][token].get("current_command")
    if not current_cmd:
        await message.answer(
            "❌ <b>Xatolik yuz berdi!</b>\n\n"
            "Iltimos, qaytadan boshlang.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    response = message.text.strip()

    # Matn validatsiyasi
    if len(response) < 1 or len(response) > 4000:
        await message.answer(
            "❌ <b>Javob matni noto'g'ri uzunlikda!</b>\n\n"
            "Javob matni 1 dan 4000 ta belgigacha bo'lishi kerak.\n"
            "Qaytadan yuboring:",
            parse_mode="HTML"
        )
        return

    data[user_id][token]["commands"][current_cmd] = response
    data[user_id][token].pop("current_command", None)

    if save_data(data):
        await message.answer(
            f"✅ <b>Komanda saqlandi!</b>\n\n"
            f"<code>{current_cmd}</code> → <i>{response[:50]}...</i>\n\n"
            "Yana bir komanda yozing yoki <b>'Tugatish'</b> deb yozib, bot yaratishni yakunlang:",
            parse_mode="HTML"
        )
        await state.set_state(BotCreation.waiting_for_command)
    else:
        await message.answer(
            "❌ <b>Saqlashda xatolik!</b>\n\n"
            "Iltimos, qaytadan urinib ko'ring.",
            parse_mode="HTML"
        )


@dp.message(Text(text="📋 Mening botlarim"))
async def my_bots(message: Message):
    """Foydalanuvchi botlarini ko'rsatish"""
    user_id = str(message.from_user.id)
    data = load_data()
    user_bots = data.get(user_id, {})

    if not user_bots:
        await message.answer(
            "🤖 <b>Sizda hali botlar mavjud emas.</b>\n\n"
            "Yangi bot yaratish uchun <b>'Bot qo'shish'</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=main_menu
        )
        return

    text_lines = ["📋 <b>Sizning botlaringiz:</b>\n"]
    total_commands = 0

    for token, bot_data in user_bots.items():
        username = bot_data.get("bot_username", "Noma'lum")
        first_name = bot_data.get("bot_first_name", "Noma'lum")
        commands = bot_data.get("commands", {})
        commands_count = len(commands)
        total_commands += commands_count

        text_lines.append(
            f"🤖 <b>@{username}</b> - {first_name}\n"
            f"   📊 Komandalar: {commands_count} ta\n"
            f"   🔑 Token: <code>{token[:10]}...{token[-5:]}</code>\n"
        )

    text_lines.append(f"\n📈 <b>Jami:</b> {len(user_bots)} ta bot, {total_commands} ta komanda")

    text = "\n".join(text_lines)
    await message.answer(text, parse_mode="HTML")


@dp.message(Text(text="❌ Bot o'chirish"))
async def delete_bot_start(message: Message, state: FSMContext):
    """Bot o'chirishni boshlash"""
    user_id = str(message.from_user.id)
    data = load_data()
    user_bots = data.get(user_id, {})

    if not user_bots:
        await message.answer(
            "❌ <b>Sizda o'chirish uchun botlar mavjud emas.</b>",
            parse_mode="HTML",
            reply_markup=main_menu
        )
        return

    keyboard = get_bots_keyboard(user_id)
    if keyboard:
        await message.answer(
            "🗑️ <b>O'chirish uchun botni tanlang:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.set_state(BotCreation.waiting_for_bot_selection)
    else:
        await message.answer(
            "❌ <b>Xatolik yuz berdi!</b>",
            parse_mode="HTML",
            reply_markup=main_menu
        )


@dp.callback_query(BotCreation.waiting_for_bot_selection, Text(startswith="bot_"))
async def process_bot_selection(callback: CallbackQuery, state: FSMContext):
    """Bot tanlashni qayta ishlash"""
    token = callback.data.replace("bot_", "")
    user_id = str(callback.from_user.id)

    data = load_data()
    if user_id in data and token in data[user_id]:
        bot_data = data[user_id][token]
        username = bot_data.get("bot_username", "Noma'lum")

        await state.update_data(delete_token=token)
        await callback.message.edit_text(
            f"⚠️ <b>Haqiqatan ham botni o'chirmoqchimisiz?</b>\n\n"
            f"🤖 Bot: @{username}\n"
            f"🔑 Token: <code>{token[:10]}...{token[-5:]}</code>\n\n"
            "❌ Bu amalni ortga qaytarib bo'lmaydi!",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "O'chirishni tasdiqlaysizmi?",
            reply_markup=confirmation_keyboard
        )
        await state.set_state(BotCreation.waiting_for_command_deletion)
    else:
        await callback.message.edit_text(
            "❌ <b>Bot topilmadi!</b>",
            parse_mode="HTML"
        )

    await callback.answer()


@dp.message(BotCreation.waiting_for_command_deletion)
async def process_deletion_confirmation(message: Message, state: FSMContext):
    """O'chirishni tasdiqlash"""
    user_id = str(message.from_user.id)
    state_data = await state.get_data()
    token = state_data.get("delete_token")

    if message.text == "✅ Ha":
        data = load_data()
        if user_id in data and token in data[user_id]:
            bot_data = data[user_id].pop(token)
            username = bot_data.get("bot_username", "Noma'lum")

            # Agar foydalanuvchida boshqa botlar qolmasa, user_id ni o'chirish
            if not data[user_id]:
                data.pop(user_id, None)

            if save_data(data):
                # Webhook ni o'chirish
                try:
                    user_bot = Bot(token=token)
                    await user_bot.delete_webhook()
                    await user_bot.session.close()
                except Exception as e:
                    logger.error(f"Webhook o'chirishda xatolik: {e}")

                await message.answer(
                    f"✅ <b>Bot muvaffaqiyatli o'chirildi!</b>\n\n"
                    f"🤖 @{username} boti va uning barcha ma'lumotlari o'chirildi.",
                    parse_mode="HTML",
                    reply_markup=main_menu
                )
            else:
                await message.answer(
                    "❌ <b>O'chirishda xatolik!</b>\n\n"
                    "Iltimos, keyinroq qayta urinib ko'ring.",
                    parse_mode="HTML",
                    reply_markup=main_menu
                )
        else:
            await message.answer(
                "❌ <b>Bot topilmadi!</b>",
                parse_mode="HTML",
                reply_markup=main_menu
            )
    else:
        await message.answer(
            "❌ <b>O'chirish bekor qilindi.</b>",
            parse_mode="HTML",
            reply_markup=main_menu
        )

    await state.clear()


@dp.message()
async def unknown_message(message: Message):
    """Noma'lum xabarlarga javob"""
    await message.answer(
        "❓ <b>Noma'lum buyruq!</b>\n\n"
        "Quyidagi menyudan biror narsani tanlang yoki /help buyrug'idan foydalaning.",
        parse_mode="HTML",
        reply_markup=main_menu
    )


async def main():
    """Asosiy dastur"""
    logger.info("Asosiy bot ishga tushmoqda...")

    try:
        # Bot ma'lumotlarini olish
        me = await bot.get_me()
        logger.info(f"Bot: @{me.username} (ID: {me.id})")

        # Polling ni boshlash
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}")
    finally:
        # Session ni yopish
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    # Graceful shutdown
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")
    except Exception as e:
        logger.error(f"Kutilmagan xatolik: {e}")