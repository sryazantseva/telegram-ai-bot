import telebot
import os
import json
import openai

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

# 🔒 Безопасная загрузка промта
try:
    with open("ai_prompt_academy.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = (
        "Ты ассистент Академии Практической Психологии и Консалтинга. "
        "Говори мягко, поддерживающе, на русском языке. "
        "Отвечай только на темы, связанные с обучением, эмоциями и психологией. "
        "Если вопрос не по теме — вежливо откажись и предложи вернуться к поддержке."
    )
    print("⚠️ Промт не найден — используется резервная версия.")

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Команда для начала диалога
@bot.message_handler(commands=["поговорим"])
def handle_ai_intro(message):
    bot.send_message(message.chat.id, "🧠 Напиши мне, что чувствуешь или хочешь обсудить — я рядом.")
    bot.register_next_step_handler(message, process_ai_message)

# Заглушка для мини-памяти (можно заменить на файл позже)
user_interests = {}

def process_ai_message(message):
    user_id = message.from_user.id
    user_input = message.text

    try:
        response = openai.ChatCompletion.create(
            model="	o3-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.8,
            max_tokens=500
        )
        reply = response["choices"][0]["message"]["content"]
        bot.send_message(message.chat.id, reply)

        # ✅ Печатаем в консоль
        print("="*40)
        print(f"[USER {user_id}]: {user_input}")
        print(f"[BOT]: {reply}")
        print("="*40)

        # ✅ Простейшая "память": ищем ключевые интересы в ответе
        keywords = {
            "КПТ": "Когнитивно-поведенческая терапия",
            "коучинг": "Профессиональный коучинг",
            "телесно": "Телесно-ориентированная психотерапия",
            "ДФС": "Методика ДФС",
            "интенсив": "Интенсив «Психолог-консультант»"
        }
        for key, name in keywords.items():
            if key.lower() in reply.lower():
                user_interests[str(user_id)] = name
                print(f"[💾 Память] Пользователь {user_id} заинтересовался: {name}")
                break

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Что-то пошло не так... Попробуй ещё раз.")
        print(f"[Ошибка AI]: {e}")


bot.polling()

