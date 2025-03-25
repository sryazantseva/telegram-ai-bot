def init_scenarios(bot):
    @bot.message_handler(commands=["сценарий"])
    def handle_scenario(message):
        bot.send_message(message.chat.id, "Сценарии пока не настроены.")
