import telebot
import os
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
bot = telebot.TeleBot(BOT_TOKEN)

SCENARIO_FILE = "scenario_store.json"
USER_FILE = "user_db.json"
BROADCAST_FILE = "broadcasts.json"

# Инициализация файлов
for file in [SCENARIO_FILE, USER_FILE, BROADCAST_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({} if file != USER_FILE else [], f)

def save_user(user):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    if user.id not in [u["id"] for u in users]:
        users.append({
            "id": user.id,
            "first_name": getattr(user, "first_name", ""),
            "username": getattr(user, "username", ""),
            "phone": ""
        })
        with open(USER_FILE, "w") as f:
            json.dump(users, f)

@bot.message_handler(commands=["start"])
def handle_start(message):
    save_user(message.from_user)
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        with open(SCENARIO_FILE, "r") as f:
            scenarios = json.load(f)
        scenario = scenarios.get(code)
        if scenario:
            send_content(message.chat.id, scenario["text"], scenario.get("file_id"), scenario.get("file_type"), scenario.get("file_or_link"))
        else:
            bot.send_message(message.chat.id, "❌ Такой сценарий не найден.")
    else:
        bot.send_message(message.chat.id, "Привет! Я бот Академии 🌿 Напиши /ping для проверки.")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

def send_content(chat_id, text, file_id=None, file_type=None, link=None):
    caption = text + (f"\n\n🔗 {link}" if link else "")
    if file_id and file_type:
        if file_type == "document":
            bot.send_document(chat_id, file_id, caption=caption)
        elif file_type == "audio":
            bot.send_audio(chat_id, file_id, caption=caption)
        elif file_type == "video":
            bot.send_video(chat_id, file_id, caption=caption)
        elif file_type == "photo":
            bot.send_photo(chat_id, file_id, caption=caption)
    else:
        bot.send_message(chat_id, caption)

# ==== Сценарий ====
@bot.message_handler(commands=["сценарий"])
def scenario_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📝 Введите текст сценария:")
    bot.register_next_step_handler(message, scenario_text)

def scenario_text(message):
    text = message.text
    bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
    bot.register_next_step_handler(message, scenario_file, text)

def scenario_file(message, text):
    file_id, file_type = None, None
    if message.content_type == "document":
        file_id, file_type = message.document.file_id, "document"
    elif message.content_type == "audio":
        file_id, file_type = message.audio.file_id, "audio"
    elif message.content_type == "video":
        file_id, file_type = message.video.file_id, "video"
    elif message.content_type == "photo":
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.text.lower() == "нет":
        pass
    else:
        bot.send_message(message.chat.id, "❌ Неверный тип файла.")
        return
    bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
    bot.register_next_step_handler(message, preview_scenario, text, file_id, file_type)

def preview_scenario(message, text, file_id, file_type):
    link = message.text if message.text.lower() != "нет" else ""
    preview_text = f"📘 Предпросмотр сценария:\n\n{text}"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Сохранить", callback_data=f"save_scenario|{uuid.uuid4()}|{file_id or 'no'}|{file_type or 'no'}|{link or 'no'}|{text}"))
    send_content(message.chat.id, preview_text, file_id, file_type, link)
    bot.send_message(message.chat.id, "Сохранить этот сценарий?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_scenario"))
def save_scenario_handler(call):
    _, uid, file_id, file_type, link, text = call.data.split("|", 5)
    bot.send_message(call.message.chat.id, "💬 Введите короткий код сценария (латиницей):")
    bot.register_next_step_handler(call.message, save_scenario_final, text, file_id if file_id != 'no' else None, file_type if file_type != 'no' else None, link if link != 'no' else "")

def save_scenario_final(message, text, file_id, file_type, link):
    code = message.text.strip()
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    scenarios[code] = {
        "text": text,
        "file_id": file_id,
        "file_type": file_type,
        "file_or_link": link
    }
    with open(SCENARIO_FILE, "w") as f:
        json.dump(scenarios, f)
    bot.send_message(message.chat.id, f"✅ Сценарий сохранён!\nСсылка: t.me/{bot.get_me().username}?start={code}")

# ==== Рассылка ====
@bot.message_handler(commands=["рассылка"])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📣 Введите текст рассылки:")
    bot.register_next_step_handler(message, broadcast_text)

def broadcast_text(message):
    text = message.text
    bot.send_message(message.chat.id, "📎 Прикрепите файл (или 'нет'):")
    bot.register_next_step_handler(message, broadcast_file, text)

def broadcast_file(message, text):
    file_id, file_type = None, None
    if message.content_type == "document":
        file_id, file_type = message.document.file_id, "document"
    elif message.content_type == "audio":
        file_id, file_type = message.audio.file_id, "audio"
    elif message.content_type == "video":
        file_id, file_type = message.video.file_id, "video"
    elif message.content_type == "photo":
        file_id, file_type = message.photo[-1].file_id, "photo"
    elif message.text.lower() == "нет":
        pass
    else:
        bot.send_message(message.chat.id, "❌ Неверный тип файла.")
        return
    bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
    bot.register_next_step_handler(message, preview_broadcast, text, file_id, file_type)

def preview_broadcast(message, text, file_id, file_type):
    link = message.text if message.text.lower() != "нет" else ""
    broadcast_id = str(uuid.uuid4())
    with open(BROADCAST_FILE, "r") as f:
        broadcasts = json.load(f)
    broadcasts[broadcast_id] = {"text": text, "file_id": file_id, "file_type": file_type, "link": link}
    with open(BROADCAST_FILE, "w") as f:
        json.dump(broadcasts, f)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Отправить сейчас", callback_data=f"send_now|{broadcast_id}"),
        InlineKeyboardButton("⏰ Запланировать на завтра", callback_data=f"send_later|{broadcast_id}")
    )
    send_content(message.chat.id, f"📢 Предпросмотр рассылки:\n\n{text}", file_id, file_type, link)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def handle_send_broadcast(call):
    action, broadcast_id = call.data.split("|", 1)
    with open(BROADCAST_FILE, "r") as f:
        broadcasts = json.load(f)
    data = broadcasts.get(broadcast_id)
    if not data:
        bot.send_message(call.message.chat.id, "❌ Рассылка не найдена.")
        return
    if action == "send_now":
        do_broadcast(data["text"], data.get("file_id"), data.get("file_type"), data.get("link"))
    else:
        send_time = datetime.now() + timedelta(days=1)
        send_time = send_time.replace(hour=12, minute=0, second=0)
        schedule_broadcast(data["text"], data.get("file_id"), data.get("file_type"), data.get("link"), send_time)
        bot.send_message(call.message.chat.id, "🕓 Запланировано на завтра 12:00 МСК")

def schedule_broadcast(text, file_id, file_type, link, when):
    def task():
        delay = (when - datetime.now()).total_seconds()
        time.sleep(max(0, delay))
        do_broadcast(text, file_id, file_type, link)
    threading.Thread(target=task).start()

def do_broadcast(text, file_id, file_type, link):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    sent = 0
    for user in users:
        try:
            send_content(user["id"], text, file_id, file_type, link)
            sent += 1
        except Exception as e:
            print(f"Ошибка: {user['id']}", e)
    print(f"✅ Рассылка завершена. Отправлено: {sent}")

# ==== Экспорт данных ====
@bot.message_handler(commands=["экспорт"])
def export_data(message):
    if message.from_user.id != ADMIN_ID:
        return
    files = [SCENARIO_FILE, BROADCAST_FILE, USER_FILE]
    for fpath in files:
        bot.send_document(message.chat.id, InputFile(fpath))

bot.polling()
