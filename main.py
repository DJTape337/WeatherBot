from telebot import TeleBot, custom_filters
from telebot.types import Message
from telebot.storage import StateMemoryStorage
import config
from telebot.states.sync.middleware import StateMiddleware
from telebot.states import State, StatesGroup

state_storage = StateMemoryStorage()
bot = TeleBot(config.token, state_storage=state_storage, use_class_middlewares=True)
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

class StatesSetup(StatesGroup):
    awaiting_name = State()
    awaiting_city = State()
    confirm_reset = State()

@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    bot.send_message(chat_id=message.chat.id, text='Привет. Я - бот, предназначенный'
                                                   ' для получения погодных сводок в твоём городе.\n'
                                                   'Я могу присылать сводку о погоде в твоём городе, '
                                                   'а так же автоматически присылать её в установленное тобой время.'
                                                   'Для продолжения скажи, как я могу тебя называть?')
    bot.set_state(user_id=message.from_user.id,
                  state=StatesSetup.awaiting_name,
                  chat_id=message.chat.id)
    print(bot.get_state(message.from_user.id, message.chat.id))

if __name__ == '__main__':
    bot.infinity_polling()