import telebot
import os
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaDocument
from datetime import datetime, timedelta
import threading
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

SCENARIO_FILE = "scenario_store.json"
USER_FILE = "user_db.json"
BROADCAST_FILE = "broadcasts.json"

for file in [SCENARIO_FILE, USER_FILE, BROADCAST_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file != USER_FILE else [], f)

def save_user(user):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "username": getattr(user, "username", ""),
        "phone": ""  # можно будет добавить позже
    }
    if user.id not in [u["id"] for u in users]:
        users.append(user_data)
        with open(USER_FILE, "w") as f:
            json.dump(users, f)

@bot.message_handler(commands=["start"])
def handle_start(message):
    save_user(message.from_user)
    bot.send_message(message.chat.id, "Привет! Я бот Академии 🌿 Напиши /ping для проверки.")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

@bot.message_handler(commands=["рассылка"])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📣 Введите текст для рассылки:")
    bot.register_next_step_handler(message, get_broadcast_text)

def get_broadcast_text(message):
    text = message.text
    bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
    bot.register_next_step_handler(message, get_broadcast_file, text)

def get_broadcast_file(message, text):
    file_id = None
    if message.text and message.text.lower() == 'нет':
        file_id = None
    elif message.document:
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте ещё раз.")
        return

    bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
    bot.register_next_step_handler(message, preview_broadcast, text, file_id)

def preview_broadcast(message, text, file_id):
    link = message.text if message.text.lower() != 'нет' else ""
    preview = f"<b>📢 Предпросмотр рассылки:</b>\n\n{text}"
    if link:
        preview += f"\n\n🔗 <a href='{link}'>Ссылка</a>"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Отправить сейчас", callback_data=f"send_now|{text}|{file_id or 'no'}|{link}"),
        InlineKeyboardButton("⏰ Запланировать на завтра", callback_data=f"send_later|{text}|{file_id or 'no'}|{link}")
    )
    bot.send_message(message.chat.id, preview, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def handle_send(call):
    action, text, file_id, link = call.data.split("|", 3)
    send_time = datetime.now()
    if action == "send_later":
        send_time = send_time + timedelta(days=1)
        send_time = send_time.replace(hour=12, minute=0, second=0)
        schedule_broadcast(text, file_id if file_id != 'no' else None, link, send_time)
        bot.send_message(call.message.chat.id, "🕓 Запланировано на завтра 12:00 МСК")
    else:
        do_broadcast(text, file_id if file_id != 'no' else None, link)

def schedule_broadcast(text, file_id, link, when):
    def task():
        time_to_wait = (when - datetime.now()).total_seconds()
        time.sleep(max(0, time_to_wait))
        do_broadcast(text, file_id, link)
    threading.Thread(target=task).start()

def do_broadcast(text, file_id, link):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    count = 0
    for user in users:
        try:
            uid = user["id"]
            bot.send_message(uid, text)
            if file_id:
                bot.send_document(uid, file_id)
            if link:
                bot.send_message(uid, link)
            count += 1
        except Exception as e:
            print(f"Ошибка отправки {uid}: {e}")
    print(f"Рассылка завершена. Отправлено: {count}")

bot.polling()
