import telebot
import os
import json
import threading
from datetime import datetime, timedelta

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
    msg = bot.send_message(message.chat.id, "📝 Введите текст сценария:")
    bot.register_next_step_handler(msg, process_scenario_text)

def process_scenario_text(message):
    text = message.text
    msg = bot.send_message(message.chat.id, "🔗 Прикрепите ссылку или файл (если нужно), или напишите 'нет':")
    bot.register_next_step_handler(msg, process_scenario_link, text)

def process_scenario_link(message, text):
    file_or_link = message.text if message.text.lower() != "нет" else ""
    msg = bot.send_message(message.chat.id, "💬 Введите короткий код сценария (латиницей):")
    bot.register_next_step_handler(msg, save_scenario, text, file_or_link)

def save_scenario(message, text, file_or_link):
    code = message.text.strip()
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    scenarios[code] = {"text": text, "file_or_link": file_or_link}
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
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Сейчас", "Завтра в определённое время")
    bot.send_message(message.chat.id, "⏰ Когда отправить сообщение?", reply_markup=markup)
    bot.register_next_step_handler(message, handle_schedule_choice, text)

def handle_schedule_choice(message, text):
    choice = message.text.lower()
    if "сейчас" in choice:
        send_broadcast(text, message.chat.id)
    elif "завтра" in choice:
        msg = bot.send_message(message.chat.id, "🕒 Введите время в формате ЧЧ:ММ по МСК (например, 10:30):")
        bot.register_next_step_handler(msg, schedule_for_tomorrow, text)
    else:
        bot.send_message(message.chat.id, "❌ Неверный выбор. Попробуйте снова.")


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
