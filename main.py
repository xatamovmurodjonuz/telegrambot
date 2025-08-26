import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.state import StateFilter

logging.basicConfig(level=logging.INFO)

API_TOKEN = "8394413141:-"  # Asosiy bot tokeni

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- FSM holatlar ---
class BotCreation(StatesGroup):
    waiting_for_token = State()
    waiting_for_start_response = State()
    waiting_for_command = State()
    waiting_for_command_response = State()

# --- Foydalanuvchi ma'lumotlarini vaqtincha saqlash ---
user_data_store = {}

# --- Yaratilgan foydalanuvchi botlarini saqlash ---
running_user_bots = {}

# --- Asosiy menyu klaviaturasi ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Bot qo'shish")],
        [KeyboardButton(text="Mening botlarim")]
    ],
    resize_keyboard=True
)

# /start komandasi
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Asosiy menyu:", reply_markup=main_menu)
    await state.clear()

# Bot qo'shish bosilganda ko'rsatma berish
@dp.message(Text("Bot qo'shish"))
async def bot_add_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Avvalo, BotFather’dan API token olish kerak.\n"
        "1. @BotFather ga kiring.\n"
        "2. /newbot buyrug'ini yozing va bot uchun nom va username tanlang.\n"
        "3. Sizga API token beriladi, uni shu yerga yuboring."
    )
    await state.set_state(BotCreation.waiting_for_token)

# API tokenni qabul qilish
@dp.message(StateFilter(BotCreation.waiting_for_token))
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    user_id = message.from_user.id

    user_data_store[user_id] = {
        "token": token,
        "commands": {}
    }
    await message.answer("Ajoyib! Endi /start komandasi uchun javob matnini yozing:")
    await state.set_state(BotCreation.waiting_for_start_response)

# /start komandasi uchun javob matni qabul qilish
@dp.message(StateFilter(BotCreation.waiting_for_start_response))
async def process_start_response(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    user_data_store[user_id]["commands"]["/start"] = text

    await message.answer(
        "Yana bir komandani qo‘shmoqchimisiz? / (slash) bilan boshlanadigan komandani yozing yoki 'Tugatish' deb yozing."
    )
    await state.set_state(BotCreation.waiting_for_command)

# Qo‘shimcha komandalarni qabul qilish
@dp.message(StateFilter(BotCreation.waiting_for_command))
async def process_command(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if text.lower() == "tugatish":
        await message.answer("Bot yaratish jarayoni yakunlandi. Rahmat!", reply_markup=main_menu)
        await state.clear()

        # Yangi foydalanuvchi botini ishga tushiramiz
        user_id = message.from_user.id
        user_bot_data = user_data_store.get(user_id)

        if user_bot_data and user_bot_data.get("token"):
            # Agar oldin bot ishlayotgan bo'lsa, uni to'xtatamiz
            if user_id in running_user_bots:
                running_user_bots[user_id].cancel()

            # Yangi botni ishga tushirish
            task = asyncio.create_task(run_user_bot(user_bot_data["token"], user_bot_data["commands"]))
            running_user_bots[user_id] = task

        return

    if not text.startswith("/"):
        await message.answer("Iltimos, komanda / bilan boshlanishi kerak.")
        return

    await state.update_data(current_command=text)
    await message.answer(f"Komanda {text} uchun javob matnini yozing:")
    await state.set_state(BotCreation.waiting_for_command_response)

# Qo‘shimcha komandalar uchun javob matnini qabul qilish
@dp.message(StateFilter(BotCreation.waiting_for_command_response))
async def process_command_response(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    cmd = data.get("current_command")
    resp = message.text.strip()

    if user_id in user_data_store:
        user_data_store[user_id]["commands"][cmd] = resp
    else:
        user_data_store[user_id] = {
            "token": None,
            "commands": {cmd: resp}
        }

    await message.answer(
        "Yana bir komandani qo‘shmoqchimisiz? / (slash) bilan boshlanadigan komandani yozing yoki 'Tugatish' deb yozing."
    )
    await state.set_state(BotCreation.waiting_for_command)

# "Mening botlarim" tugmasi bosilganda
@dp.message(Text("Mening botlarim"))
async def my_bots(message: types.Message):
    user_id = message.from_user.id
    bots = user_data_store.get(user_id)

    if not bots or not bots.get("commands"):
        await message.answer("Sizda hozircha bot yoki komandalar mavjud emas.")
        return

    commands = bots["commands"]
    if len(commands) == 0:
        await message.answer("Sizda hozircha bot uchun qo‘shilgan komandalar yo‘q.")
        return

    text_lines = ["Sizning botlaringiz va ularning komandalari:\n"]
    for cmd, resp in commands.items():
        text_lines.append(f"➡️ {cmd}: {resp}")

    text = "\n".join(text_lines)

    max_length = 4000
    if len(text) > max_length:
        text = text[:max_length] + "\n\n...va yana boshqa komandalar mavjud."

    await message.answer(text)

# Foydalanuvchi botini ishga tushirish funksiyasi
async def run_user_bot(token: str, commands: dict):
    user_bot = Bot(token=token)
    user_dp = Dispatcher()

    @user_dp.message_handler(commands=[cmd.strip("/") for cmd in commands.keys()])
    async def handle_commands(message: types.Message):
        cmd = "/" + message.text.lstrip("/")
        response = commands.get(cmd, "Bu komanda uchun javob topilmadi.")
        await message.answer(response)

    try:
        logging.info(f"Foydalanuvchi boti ishga tushmoqda: {token[:10]}***")
        await user_dp.start_polling(user_bot)
    except asyncio.CancelledError:
        logging.info(f"Foydalanuvchi boti to'xtatildi: {token[:10]}***")
    finally:
        await user_bot.session.close()

# Asosiy bot ishga tushirilishi
async def main():
    print("Asosiy bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
