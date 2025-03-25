import json
import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

SCENARIO_FILE = "scenario_store.json"
TEMP_SCENARIO_FILE = "temp_scenarios.json"


def init_scenarios(bot):
    @bot.message_handler(commands=["сценарий"])
    def handle_scenario(message):
        if message.from_user.id != int(bot.ADMIN_ID):
            return
        bot.send_message(message.chat.id, "📝 Введите текст сценария:")
        bot.register_next_step_handler(message, get_scenario_text, bot)

    def get_scenario_text(message, bot):
        text = message.text
        bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
        bot.register_next_step_handler(message, get_scenario_file, bot, text)

    def get_scenario_file(message, bot, text):
        file_id = None
        if message.text and message.text.lower() == 'нет':
            pass
        elif message.document:
            file_id = message.document.file_id
        elif message.audio:
            file_id = message.audio.file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.photo:
            file_id = message.photo[-1].file_id
        else:
            bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте ещё раз.")
            return
        bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
        bot.register_next_step_handler(message, preview_scenario, bot, text, file_id)

    def preview_scenario(message, bot, text, file_id):
        link = message.text if message.text.lower() != "нет" else ""
        scenario_id = str(uuid.uuid4())

        temp_data = load_temp()
        temp_data[scenario_id] = {
            "text": text,
            "file_id": file_id,
            "file_or_link": link
        }
        save_temp(temp_data)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Сохранить", callback_data=f"save_scenario|{scenario_id}"),
            InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_scenario|{scenario_id}"),
            InlineKeyboardButton("❌ Удалить", callback_data=f"delete_scenario|{scenario_id}")
        )

        preview = f"📘 <b>Предпросмотр сценария:</b>\n\n{text}"
        if link:
            preview += f"\n\n🔗 <a href='{link}'>{link}</a>"

        bot.send_message(message.chat.id, preview, parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("save_scenario"))
    def save_scenario(call):
        _, scenario_id = call.data.split("|", 1)
        temp_data = load_temp()
        data = temp_data.get(scenario_id)

        if not data:
            bot.send_message(call.message.chat.id, "❌ Ошибка: данные не найдены.")
            return

        msg = bot.send_message(call.message.chat.id, "💬 Введите короткий код сценария (латиницей):")
        bot.register_next_step_handler(msg, save_final, bot, data)

    def save_final(message, bot, data):
        code = message.text.strip()

        with open(SCENARIO_FILE, "r") as f:
            scenarios = json.load(f)

        scenarios[code] = data

        with open(SCENARIO_FILE, "w") as f:
            json.dump(scenarios, f)

        bot.send_message(message.chat.id, f"✅ Сценарий сохранён!\nСсылка: t.me/{bot.get_me().username}?start={code}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_scenario"))
    def edit_scenario(call):
        bot.send_message(call.message.chat.id, "🔁 Повторите команду /сценарий, чтобы начать заново.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_scenario"))
    def delete_scenario(call):
        _, scenario_id = call.data.split("|", 1)
        temp_data = load_temp()
        if scenario_id in temp_data:
            del temp_data[scenario_id]
            save_temp(temp_data)
            bot.send_message(call.message.chat.id, "🗑️ Черновик удалён.")
        else:
            bot.send_message(call.message.chat.id, "❌ Черновик не найден.")


def load_temp():
    try:
        with open(TEMP_SCENARIO_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_temp(data):
    with open(TEMP_SCENARIO_FILE, "w") as f:
        json.dump(data, f)
