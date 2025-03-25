import telebot
import os
import json
from openai import OpenAI

# Переменные окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Инициализация
bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.proxyapi.ru/openai/v1")

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

@bot.message_handler(commands=["поговорим"])
def handle_ai_intro(message):
    bot.send_message(message.chat.id, "🧠 Напиши мне, что чувствуешь или хочешь обсудить — я рядом.")
    bot.register_next_step_handler(message, process_ai_message)

# Системный промт
SYSTEM_PROMPT = (
    "Ты доброжелательный ассистент Академии Практической Психологии. "
    "Отвечай на вопросы только по программам, обучению, помощи, эмоциям. "
    "Если вопрос не по теме — вежливо откажи и предложи спросить про обучение."
)

# AI ответ
user_interests = {}

def process_ai_message(message):
    user_id = message.from_user.id
    user_input = message.text

    try:
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.8,
            max_tokens=500
        )
        reply = response.choices[0].message.content
        bot.send_message(message.chat.id, reply)

        # Текстовый лог
        print("="*40)
        print(f"[USER {user_id}]: {user_input}")
        print(f"[BOT]: {reply}")
        print("="*40)

        # Сохраняем интерес
        keywords = {
            "КПТ": "Когнитивно-поведенческая терапия",
            "коуч": "Профессиональный коучинг",
            "телесн": "Телесно-ориентированная психотерапия",
            "ДФС": "Методика ДФС",
            "интенс": "Интенсив 'Психолог-консультант'"
        }
        for key, name in keywords.items():
            if key.lower() in reply.lower():
                user_interests[str(user_id)] = name
                print(f"[MEMO] User {user_id} is interested in: {name}")
                break

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Что-то пошло не так... Попробуй ещё раз чуть позже.")
        print(f"[AI Error]: {e}")

bot.polling()


