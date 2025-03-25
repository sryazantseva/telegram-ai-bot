from datetime import datetime, timedelta

...

# Кнопки действия
markup = InlineKeyboardMarkup()
markup.add(
    InlineKeyboardButton("✅ Отправить сейчас", callback_data=f"send_now|{broadcast_id}"),
    InlineKeyboardButton("⏰ Запланировать на завтра", callback_data=f"ask_time|{broadcast_id}")
)
...

# Обработка inline-кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith("send_") or call.data.startswith("ask_time"))
def handle_send(call):
    action, broadcast_id = call.data.split("|", 1)

    with open(BROADCAST_FILE, "r") as f:
        broadcasts = json.load(f)
    broadcast = broadcasts.get(broadcast_id)

    if not broadcast:
        bot.send_message(call.message.chat.id, "❌ Не удалось найти рассылку.")
        return

    if action == "ask_time":
        bot.send_message(call.message.chat.id, "🕓 Введите время отправки завтра (в формате ЧЧ:ММ):")
        bot.register_next_step_handler(call.message, process_custom_time, broadcast_id)
    elif action == "send_now":
        do_broadcast(broadcast["text"], broadcast.get("file_id"), broadcast.get("link"))

# Обработка кастомного времени
def process_custom_time(message, broadcast_id):
    time_text = message.text.strip()
    try:
        hour, minute = map(int, time_text.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        tomorrow = datetime.now() + timedelta(days=1)
        send_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

        with open(BROADCAST_FILE, "r") as f:
            broadcasts = json.load(f)
        broadcast = broadcasts.get(broadcast_id)

        if broadcast:
            schedule_broadcast(broadcast["text"], broadcast.get("file_id"), broadcast.get("link"), send_time)
            bot.send_message(message.chat.id, f"📅 Запланировано на завтра в {send_time.strftime('%H:%M')} МСК")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка: рассылка не найдена.")
    except Exception:
        bot.send_message(message.chat.id, "⛔ Неверный формат. Введите, например, 14:30")

