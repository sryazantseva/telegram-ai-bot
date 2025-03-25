import telebot
import os
import json
from broadcast_handler import init_broadcast
from scenario_handler import init_scenarios

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(BOT_TOKEN)

# Запускаем обработчики рассылок и сценариев
init_broadcast(bot, ADMIN_ID)
init_scenarios(bot)

# Проверка пинга
@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.send_message(message.chat.id, "Привет! Я бот Академии 🌿 Напиши /ping для проверки.")

@bot.message_handler(commands=["ping"])
def handle_ping(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")

bot.polling()

