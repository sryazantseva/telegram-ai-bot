import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BROADCAST_FILE = "broadcasts.json"
USER_FILE = "user_db.json"

def init_broadcast(bot, admin_id):
    @bot.message_handler(commands=["рассылка"])
    def handle_broadcast(message):
        if message.from_user.id != admin_id:
            return
        bot.send_message(message.chat.id, "📣 Введите текст для рассылки:")
        bot.register_next_step_handler(message, get_broadcast_text)

    def get_broadcast_text(message):
        text = message.text
        bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
        bot.register_next_step_handler(message, get_broadcast_file, text)

    def get_broadcast_file(message, text):
        file_id = None
        if message.text and message.text.lower() == 'нет':
            pass
        elif message.document:
            file_id = message.document.file_id
        else:
            bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте ещё раз.")
            return
        bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или 'нет'):")
        bot.register_next_step_handler(message, preview_broadcast, text, file_id)

    def preview_broadcast(message, text, file_id):
        link = message.text if message.text.lower() != 'нет' else ""
        broadcast_id = str(uuid.uuid4())
        try:
            with open(BROADCAST_FILE, "r") as f:
                broadcasts = json.load(f)
        except:
            broadcasts = {}
        broadcasts[broadcast_id] = {"text": text, "file_id": file_id, "link": link}
        with open(BROADCAST_FILE, "w") as f:
            json.dump(broadcasts, f)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Отправить сейчас", callback_data=f"send_now|{broadcast_id}"),
            InlineKeyboardButton("⏰ Запланировать на завтра", callback_data=f"send_later|{broadcast_id}")
        )
        final_text = f"📢 Предпросмотр рассылки:\n\n{text}"
        if link:
            final_text += f"\n\n🔗 {link}"
        if file_id:
            bot.send_document(message.chat.id, file_id, caption=final_text)
        else:
            bot.send_message(message.chat.id, final_text)
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
    def handle_send(call):
        action, broadcast_id = call.data.split("|", 1)
        with open(BROADCAST_FILE, "r") as f:
            broadcasts = json.load(f)
        broadcast = broadcasts.get(broadcast_id)
        if not broadcast:
            bot.send_message(call.message.chat.id, "❌ Не удалось найти рассылку.")
            return
        text = broadcast["text"]
        file_id = broadcast.get("file_id")
        link = broadcast.get("link")

        if action == "send_later":
            send_time = datetime.now() + timedelta(days=1)
            send_time = send_time.replace(hour=12, minute=0, second=0)
            schedule_broadcast(text, file_id, link, send_time)
            bot.send_message(call.message.chat.id, "🕓 Запланировано на завтра 12:00 МСК")
        else:
            do_broadcast(text, file_id, link)

    def schedule_broadcast(text, file_id, link, when):
        def task():
            time.sleep(max(0, (when - datetime.now()).total_seconds()))
            do_broadcast(text, file_id, link)
        threading.Thread(target=task).start()

    def do_broadcast(text, file_id, link):
        with open(USER_FILE, "r") as f:
            users = json.load(f)
        count = 0
        for user in users:
            try:
                full_text = text
                if link:
                    full_text += f"\n\n🔗 {link}"
                if file_id:
                    bot.send_document(user["id"], file_id, caption=full_text)
                else:
                    bot.send_message(user["id"], full_text)
                count += 1
            except Exception as e:
                print(f"Ошибка при отправке {user['id']}: {e}")
        print(f"✅ Рассылка завершена. Отправлено: {count}")
