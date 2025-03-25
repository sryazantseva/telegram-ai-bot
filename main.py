import telebot
import os
import json

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

SCENARIO_FILE = "scenario_store.json"
USER_FILE = "user_db.json"

# Ensure scenario and user files exist
if not os.path.exists(SCENARIO_FILE):
    with open(SCENARIO_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump([], f)

# Save user to database
def save_user(user_id):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    if user_id not in users:
        users.append(user_id)
        with open(USER_FILE, "w") as f:
            json.dump(users, f)

# /start handler
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

# /ping
@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

# /admin
@bot.message_handler(commands=["admin"])
def handle_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    bot.send_message(message.chat.id, f"📊 Сценариев: {len(scenarios)}\n👥 Пользователей: {len(users)}")

# /сценарии
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

# /сценарий
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

# /рассылка
@bot.message_handler(commands=["рассылка"])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "📣 Введите текст для рассылки:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    text = message.text
    confirm = bot.send_message(message.chat.id, f"✅ Вот сообщение:\n{text}\n\nОтправляем?", reply_markup=confirm_keyboard())
    bot.register_next_step_handler(confirm, confirm_broadcast, text)

def confirm_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Да", "Нет")
    return markup

def confirm_broadcast(message, text):
    if message.text == "Да":
        with open(USER_FILE, "r") as f:
            users = json.load(f)
        count = 0
        for uid in users:
            try:
                bot.send_message(uid, text)
                count += 1
            except:
                pass
        bot.send_message(message.chat.id, f"✅ Рассылка завершена. Отправлено: {count}")
    else:
        bot.send_message(message.chat.id, "❌ Рассылка отменена.")

bot.polling()
