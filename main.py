import telebot
import os
import json
from broadcast_handler import init_broadcast
from scenario_handler import init_scenarios

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

# ===== Инициализация функциональности =====
init_broadcast(bot, ADMIN_ID)
init_scenarios(bot, ADMIN_ID)

# ===== Хендлер /start =====
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Сохраняем пользователя в user_db.json
    with open("user_db.json", "r") as f:
        users = json.load(f)
    if not any(u["id"] == user_id for u in users):
        users.append({
            "id": user_id,
            "username": username or "",
            "first_name": first_name or ""
        })
        with open("user_db.json", "w") as f:
            json.dump(users, f)

    bot.send_message(
        message.chat.id,
        "Привет! Я бот Академии \U0001F331 Напиши /ping для проверки."
    )

# ===== Хендлер /ping =====
@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

# ===== Запуск бота =====
bot.polling(non_stop=True)

