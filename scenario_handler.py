import json
import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

SCENARIO_FILE = "scenario_store.json"

def init_scenarios(bot, admin_id):
    @bot.message_handler(commands=["сценарий"])
    def handle_scenario(message):
        if message.from_user.id != admin_id:
            return
        bot.send_message(message.chat.id, "📝 Введите текст сценария:")
        bot.register_next_step_handler(message, get_scenario_text)

    def get_scenario_text(message):
        text = message.text
        bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
        bot.register_next_step_handler(message, get_scenario_file, text)

    def get_scenario_file(message, text):
        file_id = None
        if message.text and message.text.lower() == 'нет':
            pass
        elif message.document:
            file_id = message.document.file_id
        else:
            bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте ещё раз.")
            return
        bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
        bot.register_next_step_handler(message, preview_scenario, text, file_id)

    def preview_scenario(message, text, file_id):
        link = message.text if message.text.lower() != 'нет' else ""
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Сохранить", callback_data=f"save_scenario|{uuid.uuid4()}|{file_id or 'no'}|{link or 'no'}|{text}"))
        final_text = f"📘 Предпросмотр сценария:\n\n{text}"
        if link:
            final_text += f"\n\n🔗 {link}"
        if file_id:
            bot.send_document(message.chat.id, file_id, caption=final_text)
        else:
            bot.send_message(message.chat.id, final_text)
        bot.send_message(message.chat.id, "Сохранить этот сценарий?", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("save_scenario"))
    def handle_save_scenario(call):
        _, scenario_id, file_id, link, text = call.data.split("|", 4)
        bot.send_message(call.message.chat.id, "💬 Введите короткий код сценария (латиницей):")
        bot.register_next_step_handler(call.message, save_scenario_final, text, file_id if file_id != 'no' else None, link if link != 'no' else "")

    def save_scenario_final(message, text, file_id, link):
        code = message.text.strip()
        with open(SCENARIO_FILE, "r") as f:
            scenarios = json.load(f)
        scenarios[code] = {
            "text": text,
            "file_id": file_id,
            "file_or_link": link
        }
        with open(SCENARIO_FILE, "w") as f:
            json.dump(scenarios, f)

        bot.send_message(
            message.chat.id,
            f"✅ Сценарий сохранён!\nСсылка: t.me/{bot.get_me().username}?start={code}"
        )
