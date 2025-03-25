import telebot
import os
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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
    if not any(u["id"] == user.id for u in users):
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
            send_content(message.chat.id, scenario["text"], scenario.get("file_id"), scenario.get("file_or_link"))
        else:
            bot.send_message(message.chat.id, "❌ Такой сценарий не найден.")
    else:
        bot.send_message(message.chat.id, "Привет! Я бот Академии 🌿 Напиши /ping для проверки.")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

def send_content(chat_id, text, file_id=None, link=None):
    text_with_link = text
    if link:
        text_with_link += f"\n\n🔗 {link}"
    if file_id:
        bot.send_document(chat_id, file_id, caption=text_with_link)
    else:
        bot.send_message(chat_id, text_with_link)

# === Сценарии ===
@bot.message_handler(commands=["сценарий"])
def handle_scenario(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📝 Введите текст сценария:")
    bot.register_next_step_handler(message, get_scenario_text)

def get_scenario_text(message):
    text = message.text
    bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
    bot.register_next_step_handler(message, get_scenario_file, text)

def get_scenario_file(message, text):
    file_id = None
    if message.text.lower() != "нет" and message.document:
        file_id = message.document.file_id
    elif message.text.lower() != "нет":
        bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте снова.")
        return
    bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
    bot.register_next_step_handler(message, preview_scenario, text, file_id)

def preview_scenario(message, text, file_id):
    link = message.text if message.text.lower() != "нет" else ""
    preview = f"📘 Предпросмотр сценария:\n\n{text}"
    if link:
        preview += f"\n\n🔗 {link}"
    markup = InlineKeyboardMarkup()
    scenario_id = str(uuid.uuid4())
    markup.add(
        InlineKeyboardButton("✅ Сохранить", callback_data=f"save_scenario|{scenario_id}|{file_id or 'no'}|{link or 'no'}|{text}"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    )
    send_content(message.chat.id, preview, file_id, link)
    bot.send_message(message.chat.id, "Сохранить сценарий?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_scenario"))
def handle_save_scenario(call):
    _, scenario_id, file_id, link, text = call.data.split("|", 4)
    bot.send_message(call.message.chat.id, "💬 Введите короткий код сценария:")
    bot.register_next_step_handler(call.message, save_scenario_final, text, file_id if file_id != 'no' else None, link if link != 'no' else "")

def save_scenario_final(message, text, file_id, link):
    code = message.text.strip()
    with open(SCENARIO_FILE, "r") as f:
        scenarios = json.load(f)
    scenarios[code] = {
        "text": text,
        "file_id": file_id,
        "file_type": "document" if file_id else "",
        "file_or_link": link
    }
    with open(SCENARIO_FILE, "w") as f:
        json.dump(scenarios, f)
    bot.send_message(message.chat.id, f"✅ Сценарий сохранён!\nСсылка: t.me/{bot.get_me().username}?start={code}")

# === Рассылка ===
@bot.message_handler(commands=["рассылка"])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "📣 Введите текст рассылки:")
    bot.register_next_step_handler(message, get_broadcast_text)

def get_broadcast_text(message):
    text = message.text
    bot.send_message(message.chat.id, "📎 Прикрепите файл (или 'нет'):")
    bot.register_next_step_handler(message, get_broadcast_file, text)

def get_broadcast_file(message, text):
    file_id = None
    if message.text.lower() != 'нет' and message.document:
        file_id = message.document.file_id
    elif message.text.lower() != 'нет':
        bot.send_message(message.chat.id, "❌ Неверный тип файла.")
        return
    bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
    bot.register_next_step_handler(message, preview_broadcast, text, file_id)

def preview_broadcast(message, text, file_id):
    link = message.text if message.text.lower() != "нет" else ""
    broadcast_id = str(uuid.uuid4())

    with open(BROADCAST_FILE, "r") as f:
        broadcasts = json.load(f)
    broadcasts[broadcast_id] = {"text": text, "file_id": file_id, "link": link}
    with open(BROADCAST_FILE, "w") as f:
        json.dump(broadcasts, f)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Отправить сейчас", callback_data=f"send_now|{broadcast_id}"),
        InlineKeyboardButton("⏰ Запланировать на завтра", callback_data=f"send_later|{broadcast_id}")
    )
    send_content(message.chat.id, f"📢 Предпросмотр рассылки:\n\n{text}", file_id, link)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def handle_send(call):
    action, broadcast_id = call.data.split("|", 1)
    with open(BROADCAST_FILE, "r") as f:
        broadcasts = json.load(f)
    data = broadcasts.get(broadcast_id)
    if not data:
        bot.send_message(call.message.chat.id, "❌ Ошибка: рассылка не найдена.")
        return

    if action == "send_later":
        send_time = datetime.now() + timedelta(days=1)
        send_time = send_time.replace(hour=12, minute=0, second=0)
        schedule_broadcast(data["text"], data.get("file_id"), data.get("link"), send_time)
        bot.send_message(call.message.chat.id, "🕓 Запланировано на завтра в 12:00 МСК")
    else:
        do_broadcast(data["text"], data.get("file_id"), data.get("link"), call.message)

def schedule_broadcast(text, file_id, link, when):
    def task():
        time.sleep(max(0, (when - datetime.now()).total_seconds()))
        do_broadcast(text, file_id, link)
    threading.Thread(target=task).start()

def do_broadcast(text, file_id, link, notify_message=None):
    with open(USER_FILE, "r") as f:
        users = json.load(f)
    count = 0
    for user in users:
        try:
            send_content(user["id"], text, file_id, link)
            count += 1
        except Exception as e:
            print(f"❌ Не отправлено {user['id']}: {e}")
    if notify_message:
        bot.send_message(notify_message.chat.id, f"✅ Рассылка завершена. Отправлено: {count}")
    print(f"✅ Рассылка завершена. Всего отправлено: {count}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_action(call):
    bot.send_message(call.message.chat.id, "❌ Действие отменено.")

bot.polling()
