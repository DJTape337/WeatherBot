from telebot import TeleBot, custom_filters
from telebot.types import Message
from telebot.storage import StateMemoryStorage
import config
from telebot.states.sync.middleware import StateMiddleware
from telebot.states import State, StatesGroup
from logger import bot_logger, log_state, log_info
from dbase import create_model, create_user, create_request, update_user_data, get_user_data

state_storage = StateMemoryStorage()
bot = TeleBot(config.token, state_storage=state_storage, use_class_middlewares=True)
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

class StatesSetup(StatesGroup):
    awaiting_name = State()
    awaiting_city = State()
    confirm_reset = State()

def get_ids(message: Message):
    """
    Получаем id пользователя и чата из сообщения
    :param message: сообщение пользователя
    :return: id пользователя, id чата
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    return user_id, chat_id

def gen_cities_markup():
    return


@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    user_id, chat_id = get_ids(message)
    log_info(bot_logger, user_id, 'Бот запущен.')
    bot.send_message(chat_id=chat_id, text='Привет. Я - бот, предназначенный'
                                                   ' для получения погодных сводок в твоём городе.\n'
                                                   'Я могу присылать сводку о погоде в твоём городе, '
                                                   'а так же автоматически присылать её в установленное тобой время.'
                                                   'Для продолжения скажи, как я могу тебя называть?')
    bot.set_state(user_id=user_id,
                  state=StatesSetup.awaiting_name,
                  chat_id=chat_id)
    log_state(bot_logger, user_id, bot.get_state(user_id=user_id, chat_id=chat_id))
    create_user(user_id)
    bot_logger.info(bot_logger, user_id, 'Создана запись о пользователе.')


@bot.message_handler(state=StatesSetup.awaiting_name, content_types=['text'])
def input_name(message: Message):
    name = message.text
    user_id, chat_id = get_ids(message)
    bot.add_data(user_id=user_id,
                 chat_id=chat_id,
                 name=name)
    log_info(bot_logger, user_id, 'Установлено имя.')
    bot.set_state(user_id=user_id,
                  state=StatesSetup.awaiting_city,
                  chat_id=chat_id)
    log_state(bot_logger, user_id, bot.get_state(user_id=user_id, chat_id=chat_id))
    bot.send_message(chat_id=chat_id,
                     text=f'Отлично, {name}! С именем определились, теперь выбери свой город:',
                     reply_markup=gen_cities_markup())

if __name__ == '__main__':
    create_model()
    bot.infinity_polling()