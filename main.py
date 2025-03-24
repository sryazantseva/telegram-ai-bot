import telebot
import os
import json

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
                bot.send_message(user_id, scenario["file_or_link"])
            if scenario.get("file_id"):
                file_type = scenario.get("file_type")
                if file_type == "document":
                    bot.send_document(user_id, scenario["file_id"])
                elif file_type == "audio":
                    bot.send_audio(user_id, scenario["file_id"])
                elif file_type == "video":
                    bot.send_video(user_id, scenario["file_id"])
                elif file_type == "photo":
                    bot.send_photo(user_id, scenario["file_id"])
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

bot.polling()

