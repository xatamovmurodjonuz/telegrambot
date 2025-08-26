import json
import os
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot
import logging
from fastapi.responses import JSONResponse

app = FastAPI()
logging.basicConfig(level=logging.INFO)

DATA_FILE = "user_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@app.post("/webhook/{user_id}/{token}")
async def webhook(user_id: str, token: str, request: Request):
    data = load_data()

    # Foydalanuvchi va token mavjudligini tekshirish
    if user_id not in data or token not in data[user_id]:
        raise HTTPException(status_code=404, detail="Bot topilmadi")

    user_bot_data = data[user_id][token]
    commands = user_bot_data.get("commands", {})

    # Telegram update ni olish
    update = await request.json()

    # Agar message bo'lsa
    if "message" in update:
        message = update["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        # Bot yaratish
        bot = Bot(token=token)

        # Komanda bo'yicha javob qaytarish
        response_text = commands.get(text, "Bu komanda mavjud emas.")

        # Agar /start bo'lsa, maxsus javob
        if text == "/start":
            response_text = commands.get("/start", "Xush kelibsiz!")

        # Javob yuborish
        await bot.send_message(chat_id, response_text)
        await bot.session.close()

    return JSONResponse(content={"status": "ok"})


@app.get("/")
async def root():
    return {"message": "Webhook server ishlamoqda"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)