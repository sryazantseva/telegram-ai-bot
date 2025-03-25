def init_broadcast(bot):
    @bot.message_handler(commands=["рассылка"])
    def handle_broadcast(message):
        bot.send_message(message.chat.id, "Рассылка пока не настроена.")
