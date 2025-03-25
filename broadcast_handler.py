import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BROADCAST_FILE = "broadcasts.json"       # Финальные рассылки
TEMP_BROADCAST_FILE = "temp_broadcasts.json"  # Временные черновики
USER_FILE = "user_db.json"

def load_temp_broadcast():
    try:
        with open(TEMP_BROADCAST_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_temp_broadcast(data):
    with open(TEMP_BROADCAST_FILE, "w") as f:
        json.dump(data, f)

def init_broadcast(bot, admin_id):
    @bot.message_handler(commands=["рассылка"])
    def handle_broadcast(message):
        if message.from_user.id != admin_id:
            return
        bot.send_message(message.chat.id, "📣 Введите текст для рассылки:")
        bot.register_next_step_handler(message, get_broadcast_text)

    def get_broadcast_text(message):
        text = message.text
        broadcast_id = str(uuid.uuid4())
        draft = {"text": text, "file_id": None, "media_type": None, "link": ""}
        temp_data = load_temp_broadcast()
        temp_data[broadcast_id] = draft
        save_temp_broadcast(temp_data)
        bot.send_message(message.chat.id, "📎 Прикрепите файл (или напишите 'нет'):")
        bot.register_next_step_handler(message, get_broadcast_file, broadcast_id)

    def get_broadcast_file(message, broadcast_id):
        temp_data = load_temp_broadcast()
        draft = temp_data.get(broadcast_id)
        file_id = None
        media_type = None
        if message.text and message.text.lower() == 'нет':
            pass
        elif message.document:
            file_id = message.document.file_id
            media_type = "document"
        elif message.audio:
            file_id = message.audio.file_id
            media_type = "audio"
        elif message.video:
            file_id = message.video.file_id
            media_type = "video"
        elif message.photo:
            file_id = message.photo[-1].file_id
            media_type = "photo"
        else:
            bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте ещё раз.")
            return
        draft["file_id"] = file_id
        draft["media_type"] = media_type
        temp_data[broadcast_id] = draft
        save_temp_broadcast(temp_data)
        bot.send_message(message.chat.id, "🔗 Вставьте ссылку (или напишите 'нет'):")
        bot.register_next_step_handler(message, get_broadcast_link, broadcast_id)

    def get_broadcast_link(message, broadcast_id):
        link = message.text if message.text.lower() != "нет" else ""
        temp_data = load_temp_broadcast()
        draft = temp_data.get(broadcast_id)
        draft["link"] = link
        temp_data[broadcast_id] = draft
        save_temp_broadcast(temp_data)
        send_broadcast_preview(message.chat.id, draft, broadcast_id)

    def send_broadcast_preview(chat_id, draft, broadcast_id):
        text = draft["text"]
        link = draft.get("link", "")
        file_id = draft.get("file_id")
        media_type = draft.get("media_type")
        preview_text = f"📢 <b>Предпросмотр рассылки</b>\n\n{text}"
        if link:
            preview_text += f"\n\n🔗 <a href='{link}'>Перейти по ссылке</a>"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✏️ Изменить текст", callback_data=f"edit_text|{broadcast_id}"))
        markup.add(InlineKeyboardButton("✏️ Изменить файл", callback_data=f"edit_file|{broadcast_id}"))
        markup.add(InlineKeyboardButton("✏️ Изменить ссылку", callback_data=f"edit_link|{broadcast_id}"))
        markup.add(InlineKeyboardButton("❌ Удалить черновик", callback_data=f"delete_broadcast|{broadcast_id}"))
        markup.add(InlineKeyboardButton("✅ Сохранить", callback_data=f"save_broadcast|{broadcast_id}"))
        if file_id:
            if media_type == "photo":
                bot.send_photo(chat_id, file_id, caption=preview_text, parse_mode="HTML", reply_markup=markup)
            elif media_type == "audio":
                bot.send_audio(chat_id, file_id, caption=preview_text, parse_mode="HTML", reply_markup=markup)
            elif media_type == "video":
                bot.send_video(chat_id, file_id, caption=preview_text, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_document(chat_id, file_id, caption=preview_text, parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(chat_id, preview_text, parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_text"))
    def edit_text(call):
        _, broadcast_id = call.data.split("|", 1)
        msg = bot.send_message(call.message.chat.id, "✏️ Введите новый текст для рассылки:")
        bot.register_next_step_handler(msg, update_text, broadcast_id)

    def update_text(message, broadcast_id):
        new_text = message.text
        temp_data = load_temp_broadcast()
        if broadcast_id in temp_data:
            temp_data[broadcast_id]["text"] = new_text
            save_temp_broadcast(temp_data)
            send_broadcast_preview(message.chat.id, temp_data[broadcast_id], broadcast_id)
        else:
            bot.send_message(message.chat.id, "❌ Черновик не найден.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_file"))
    def edit_file(call):
        _, broadcast_id = call.data.split("|", 1)
        msg = bot.send_message(call.message.chat.id, "📎 Прикрепите новый файл (или напишите 'нет' для удаления):")
        bot.register_next_step_handler(msg, update_file, broadcast_id)

    def update_file(message, broadcast_id):
        temp_data = load_temp_broadcast()
        if broadcast_id not in temp_data:
            bot.send_message(message.chat.id, "❌ Черновик не найден.")
            return
        draft = temp_data[broadcast_id]
        file_id = None
        media_type = None
        if message.text and message.text.lower() == 'нет':
            draft["file_id"] = None
            draft["media_type"] = None
        elif message.document:
            file_id = message.document.file_id
            media_type = "document"
        elif message.audio:
            file_id = message.audio.file_id
            media_type = "audio"
        elif message.video:
            file_id = message.video.file_id
            media_type = "video"
        elif message.photo:
            file_id = message.photo[-1].file_id
            media_type = "photo"
        else:
            bot.send_message(message.chat.id, "❌ Неверный тип файла. Попробуйте ещё раз.")
            return
        draft["file_id"] = file_id
        draft["media_type"] = media_type
        temp_data[broadcast_id] = draft
        save_temp_broadcast(temp_data)
        send_broadcast_preview(message.chat.id, draft, broadcast_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_link"))
    def edit_link(call):
        _, broadcast_id = call.data.split("|", 1)
        msg = bot.send_message(call.message.chat.id, "🔗 Введите новую ссылку (или 'нет' для удаления):")
        bot.register_next_step_handler(msg, update_link, broadcast_id)

    def update_link(message, broadcast_id):
        new_link = message.text if message.text.lower() != "нет" else ""
        temp_data = load_temp_broadcast()
        if broadcast_id in temp_data:
            temp_data[broadcast_id]["link"] = new_link
            save_temp_broadcast(temp_data)
            send_broadcast_preview(message.chat.id, temp_data[broadcast_id], broadcast_id)
        else:
            bot.send_message(message.chat.id, "❌ Черновик не найден.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_broadcast"))
    def delete_broadcast(call):
        _, broadcast_id = call.data.split("|", 1)
        temp_data = load_temp_broadcast()
        if broadcast_id in temp_data:
            del temp_data[broadcast_id]
            save_temp_broadcast(temp_data)
            bot.send_message(call.message.chat.id, "🗑️ Черновик удалён.")
        else:
            bot.send_message(call.message.chat.id, "❌ Черновик не найден.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("save_broadcast"))
    def save_broadcast(call):
        _, broadcast_id = call.data.split("|", 1)
        temp_data = load_temp_broadcast()
        if broadcast_id not in temp_data:
            bot.send_message(call.message.chat.id, "❌ Черновик не найден.")
            return
        try:
            with open(BROADCAST_FILE, "r") as f:
                broadcasts = json.load(f)
        except:
            broadcasts = {}
        broadcasts[broadcast_id] = temp_data[broadcast_id]
        with open(BROADCAST_FILE, "w") as f:
            json.dump(broadcasts, f)
        del temp_data[broadcast_id]
        save_temp_broadcast(temp_data)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Отправить сейчас", callback_data=f"send_now|{broadcast_id}"))
        markup.add(InlineKeyboardButton("🕰 Указать время на завтра", callback_data=f"send_custom_time|{broadcast_id}"))
        bot.send_message(call.message.chat.id, "✅ Черновик сохранён. Выберите время отправки:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("send_now"))
    def send_now(call):
        _, broadcast_id = call.data.split("|", 1)
        try:
            with open(BROADCAST_FILE, "r") as f:
                broadcasts = json.load(f)
        except:
            broadcasts = {}
        broadcast = broadcasts.get(broadcast_id)
        if not broadcast:
            bot.send_message(call.message.chat.id, "❌ Рассылка не найдена.")
            return
        do_broadcast(broadcast)
        bot.send_message(call.message.chat.id, "✅ Рассылка отправлена!")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("send_custom_time"))
    def send_custom_time(call):
        _, broadcast_id = call.data.split("|", 1)
        bot.send_message(call.message.chat.id, "🕰 Введите время в формате ЧЧ:ММ для завтрашнего дня (МСК):")
        bot.register_next_step_handler(call.message, schedule_custom_time, broadcast_id)

    def schedule_custom_time(message, broadcast_id):
        try:
            hours, minutes = map(int, message.text.strip().split(":"))
            now = datetime.now()
            send_time = now + timedelta(days=1)
            send_time = send_time.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            with open(BROADCAST_FILE, "r") as f:
                broadcasts = json.load(f)
            broadcast = broadcasts.get(broadcast_id)
            if broadcast:
                schedule_broadcast(broadcast, send_time)
                bot.send_message(message.chat.id, f"📅 Рассылка запланирована на завтра в {send_time.strftime('%H:%M')} МСК")
            else:
                bot.send_message(message.chat.id, "❌ Рассылка не найдена.")
        except Exception as e:
            bot.send_message(message.chat.id, "❌ Неверный формат времени. Попробуйте ещё раз (например: 15:30)")

    def schedule_broadcast(broadcast, when):
        def task():
            time.sleep(max(0, (when - datetime.now()).total_seconds()))
            do_broadcast(broadcast)
        threading.Thread(target=task).start()

    def do_broadcast(broadcast):
        text = broadcast["text"]
        file_id = broadcast.get("file_id")
        media_type = broadcast.get("media_type")
        link = broadcast.get("link")
        try:
            with open(USER_FILE, "r") as f:
                users = json.load(f)
        except:
            users = []
        count = 0
        for user in users:
            try:
                final_text = text
                if link:
                    final_text += f"\n\n🔗 {link}"
                if file_id:
                    if media_type == "photo":
                        bot.send_photo(user["id"], file_id, caption=final_text)
                    elif media_type == "audio":
                        bot.send_audio(user["id"], file_id, caption=final_text)
                    elif media_type == "video":
                        bot.send_video(user["id"], file_id, caption=final_text)
                    else:
                        bot.send_document(user["id"], file_id, caption=final_text)
                else:
                    bot.send_message(user["id"], final_text)
                count += 1
            except Exception as e:
                print(f"Ошибка при отправке пользователю {user['id']}: {e}")
        print(f"✅ Рассылка завершена. Отправлено: {count}")
