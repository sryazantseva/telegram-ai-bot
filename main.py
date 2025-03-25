import telebot
import os
import json
from broadcast_handler import init_broadcast
from scenario_handler import init_scenarios
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔐 Конфигурация
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

# 📁 Файлы данных
SCENARIO_FILE = "scenario_store.json"
USER_FILE = "user_db.json"
BROADCAST_FILE = "broadcasts.json"

# 📦 Создание файлов, если не существуют
for file in [SCENARIO_FILE, USER_FILE, BROADCAST_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file != USER_FILE else [], f)

# 👤 Сохранение пользователя
def save_user(user):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    user_data = {
        "id": user.id,
        "first_name": getattr(user, "first_name", ""),
        "username": getattr(user, "username", ""),
        "phone": ""  # placeholder
    }
    if user.id not in [u["id"] for u in users]:
        users.append(user_data)
        with open(USER_FILE, "w") as f:
            json.dump(users, f)

# 🚀 Команды
@bot.message_handler(commands=["start"])
def handle_start(message):
    save_user(message.from_user)
    args = message.text.split()
    if len(args) > 1:
        scenario_code = args[1]
        with open(SCENARIO_FILE, "r") as f:
            scenarios = json.load(f)
        scenario = scenarios.get(scenario_code)
        if scenario:
            send_content(message.chat.id, scenario["text"], scenario.get("file_id"), scenario.get("file_or_link"))
        else:
            bot.send_message(message.chat.id, "❌ Такой сценарий не найден.")
    else:
        bot.send_message(message.chat.id, "Привет! Я бот Академии 🌿 Напиши /ping для проверки.")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

@bot.message_handler(commands=["контакты"])
def handle_download_users(message):
    if message.from_user.id != ADMIN_ID:
        return
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    if not users:
        bot.send_message(message.chat.id, "Пользователей пока нет.")
        return

    # Генерация CSV
    csv = "ID,Имя,Username\n"
    for u in users:
        csv += f"{u['id']},{u.get('first_name','')},{u.get('username','')}\n"
    with open("contacts.csv", "w", encoding="utf-8") as f:
        f.write(csv)

    bot.send_document(message.chat.id, open("contacts.csv", "rb"), caption="📋 Контакты пользователей")

# 📦 Утилита для отправки контента
def send_content(chat_id, text, file_id=None, link=None):
    final_text = text
    if link:
        final_text += f"\n\n🔗 {link}"
    if file_id:
        bot.send_document(chat_id, file_id, caption=final_text)
    else:
        bot.send_message(chat_id, final_text)

# 🔌 Подключение модулей
init_broadcast(bot, ADMIN_ID)
init_scenarios(bot, ADMIN_ID)

# ▶️ Запуск бота
bot.polling()
