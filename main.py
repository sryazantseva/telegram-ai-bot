import telebot
import os
import json
import threading
from datetime import datetime, timedelta
import re

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

SCENARIO_FILE = "scenario_store.json"
USER_FILE = "user_db.json"

if not os.path.exists(SCENARIO_FILE):
    with open(SCENARIO_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump([], f)

def save_user(user_id):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    if user_id not in users:
        users.append(user_id)
        with open(USER_FILE, "w") as f:
            json.dump(users, f)

@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    save_user(user_id)

    args = message.text.split()
    if len(args) > 1:
        scenario_code = args[1]
        with open(SCENARIO_FILE, "r") as f:
            scenarios = json.load(f)
        scenario = scenarios.get(scenario_code)
        if scenario:
            bot.send_message(user_id, scenario["text"])
            if scenario.get("file_or_link"):
                url = scenario["file_or_link"]
                if re.search(r"(youtu\.be|youtube\.com|\.mp4|vimeo\.com)", url):
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton("▶️ Смотреть видео", url=url))
                    bot.send_message(user_id, "🎥 Видео к сценарию:", reply_markup=markup)
                else:
                    bot.send_message(user_id, url)
            if scenario.get("file_id"):
                f_id = scenario["file_id"]
                f_type = scenario["file_type"]
                if f_type == "document":
                    bot.send_document(user_id, f_id)
                elif f_type == "audio":
                    bot.send_audio(user_id, f_id)
                elif f_type == "video":
                    bot.send_video(user_id, f_id)
                elif f_type == "photo":
                    bot.send_photo(user_id, f_id)
        else:
            bot.send_message(user_id, "❌ Такой сценарий не найден.")
    else:
        bot.send_message(user_id, "Привет! Я бот Академии 🌿 Напиши /ping для проверки.")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

@bot.message_handler(commands=["admin"])
def handle_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    bot.send_message(message.chat.id, f"📊 Сценариев: {len(scenarios)}\n👥 Пользователей: {len(users)}")

@bot.message_handler(commands=["сценарии"])
def handle_list_scenarios(message):
    if message.from_user.id != ADMIN_ID:
        return
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    if not scenarios:
        bot.send_message(message.chat.id, "📭 Сценарии не найдены.")
    else:
        reply = "📚 Список сценариев:\n"
        for code, data in scenarios.items():
            short = data["text"][:40].replace('\n', ' ') + "..." if len(data["text"]) > 40 else data["text"]
            reply += f"🔹 `{code}` — {short}\n"
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")

@bot.message_handler(commands=["сценарий"])
def handle_scenario(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📝 Введите текст сценария:")
    bot.register_next_step_handler(message, process_scenario_text)

def process_scenario_text(message):
    text = message.text
    bot.send_message(message.chat.id, "📎 Прикрепите файл (pdf/audio/video/photo) или отправьте 'нет':")
    bot.register_next_step_handler(message, process_file_step, text)

def process_file_step(message, text):
    if message.content_type == "text" and message.text.lower() == "нет":
        file_id = ""
        file_type = ""
        ask_for_link(message, text, file_id, file_type)
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        ask_for_link(message, text, file_id, file_type)
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
        ask_for_link(message, text, file_id, file_type)
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        ask_for_link(message, text, file_id, file_type)
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        ask_for_link(message, text, file_id, file_type)
    else:
        bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуй ещё раз.")
        return

def ask_for_link(message, text, file_id, file_type):
    msg = bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или отправьте 'нет'):")
    bot.register_next_step_handler(msg, ask_for_code, text, file_id, file_type)

def ask_for_code(message, text, file_id, file_type):
    file_or_link = message.text if message.text.lower() != "нет" else ""
    msg = bot.send_message(message.chat.id, "💬 Введите короткий код сценария (латиницей):")
    bot.register_next_step_handler(msg, save_scenario, text, file_id, file_type, file_or_link)

def save_scenario(message, text, file_id, file_type, file_or_link):
    code = message.text.strip()
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    scenarios[code] = {
        "text": text,
        "file_id": file_id,
        "file_type": file_type,
        "file_or_link": file_or_link
    }
    with open(SCENARIO_FILE, "w") as f:
        json.dump(scenarios, f)
    bot.send_message(message.chat.id, f"✅ Сценарий сохранён!\nСсылка: t.me/{bot.get_me().username}?start={code}")

@bot.message_handler(commands=["рассылка"])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "📣 Введите текст для рассылки:")
    bot.register_next_step_handler(msg, ask_schedule_type)

def ask_schedule_type(message):
    text = message.text
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📤 Отправить сейчас", callback_data=f"broadcast_now|{text}"),
        telebot.types.InlineKeyboardButton("⏰ Запланировать на завтра", callback_data=f"broadcast_tomorrow|{text}")
    )
    bot.send_message(message.chat.id, "Выберите время отправки:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("broadcast_"))
def handle_broadcast_choice(call):
    action, text = call.data.split("|", 1)
    if action == "broadcast_now":
        send_broadcast(text, call.message.chat.id)
    elif action == "broadcast_tomorrow":
        msg = bot.send_message(call.message.chat.id, "🕒 Введите время в формате ЧЧ:ММ по МСК (например, 10:30):")
        bot.register_next_step_handler(msg, schedule_for_tomorrow, text)

def schedule_for_tomorrow(message, text):
    try:
        hour, minute = map(int, message.text.strip().split(":"))
        now = datetime.now()
        target_time = datetime(now.year, now.month, now.day, hour, minute) + timedelta(days=1)
        delay = (target_time - now).total_seconds()

        threading.Timer(delay, send_broadcast, args=(text, message.chat.id)).start()
        bot.send_message(message.chat.id, f"📨 Сообщение будет отправлено завтра в {hour:02d}:{minute:02d} по МСК.")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Ошибка в формате времени. Попробуйте ещё раз.")
        print(f"[Time Parse Error]: {e}")

def send_broadcast(text, chat_id):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    count = 0
    for uid in users:
        try:
            bot.send_message(uid, text)
            count += 1
        except:
            pass
    bot.send_message(chat_id, f"✅ Рассылка завершена. Отправлено: {count}")

bot.polling()

