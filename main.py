from telebot import TeleBot, custom_filters
from telebot.types import Message
from telebot.storage import StateMemoryStorage
import config
from telebot.states.sync.middleware import StateMiddleware
from telebot.states import State, StatesGroup
from logger import bot_logger, log_state

state_storage = StateMemoryStorage()
bot = TeleBot(config.token, state_storage=state_storage, use_class_middlewares=True)
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

class StatesSetup(StatesGroup):
    awaiting_name = State()
    awaiting_city = State()
    confirm_reset = State()

def get_ids(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    return user_id, chat_id

def gen_cities_markup():


@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    user_id, chat_id = get_ids(message)
    bot_logger.info(f'Пользователь {message.from_user.id}. Бот запущен')
    bot.send_message(chat_id=chat_id, text='Привет. Я - бот, предназначенный'
                                                   ' для получения погодных сводок в твоём городе.\n'
                                                   'Я могу присылать сводку о погоде в твоём городе, '
                                                   'а так же автоматически присылать её в установленное тобой время.'
                                                   'Для продолжения скажи, как я могу тебя называть?')
    bot.set_state(user_id=user_id,
                  state=StatesSetup.awaiting_name,
                  chat_id=chat_id)
    log_state(bot_logger, user_id, bot.get_state(user_id=user_id, chat_id=chat_id))

@bot.message_handler(state=StatesSetup.awaiting_name, content_types=['text'])
def input_name(message: Message):
    name = message.text
    user_id, chat_id = get_ids(message)
    bot.add_data(user_id=user_id,
                 chat_id=chat_id,
                 name=name)
    bot_logger.info(f'Пользователь {user_id}. Установлено имя')
    bot.set_state(user_id=user_id,
                  state=StatesSetup.awaiting_city,
                  chat_id=chat_id)
    log_state(bot_logger, user_id, bot.get_state(user_id=user_id, chat_id=chat_id))
    bot.send_message(f'Отлично, {name}! С именем определились, теперь выбери свой город.')




if __name__ == '__main__':
    bot.infinity_polling()