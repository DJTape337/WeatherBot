from telebot import TeleBot, custom_filters
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
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
    user_ready = State()
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
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    half = len(config.cities_coords) // 2
    row = []
    indexes =
    for key in list(config.cities_coords.keys())[:half]:
        city = key[0].upper() + key[1:]
    return markup


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
    log_state(bot_logger, user_id, 'awaiting_name')
    create_user(user_id)
    log_info(bot_logger, user_id, 'Создана запись о пользователе.')


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
    log_state(bot_logger, user_id, 'awaiting_city')
    msg = bot.send_message(chat_id=chat_id,
                     text=f'Отлично, {name[0].upper() + name[1:]}! '
                          f'С именем определились, теперь выбери свой город:',
                     reply_markup=gen_cities_markup())

@bot.message_handler(state=StatesSetup.awaiting_city)
def input_city(message: Message):
    user_id, chat_id = get_ids(message)
    city = message.text.lower()
    if not city in config.cities_coords.keys():
        bot.send_message(chat_id, 'К сожалению, данного города пока нет в нашей'
                         ' базе данных. Пожалуйста, выбери город из списка.')
        return
    else:
        update_user_data(user_id = user_id,
                         datatype='city',
                         data = city)
        log_info(bot_logger, user_id, f'Установлен город: {city}')
        lat, lon = config.cities_coords[city]
        bot.add_data(user_id=user_id,
                     chat_id=chat_id,
                     lat=lat,
                     lon=lon)
        bot.set_state(user_id=user_id,
                      chat_id=chat_id,
                      state=StatesSetup.user_ready)
        log_state(bot_logger, user_id, 'user_ready')

@bot.message_handler(state=StatesSetup.awaiting_name,
                     content_types=[
    "text",
    "audio",
    "document",
    "photo",
    "sticker",
    "video",
    "video_note",
    "voice",
    "location",
    "contact",
    "new_chat_members",
    "left_chat_member",
    "new_chat_title",
    "new_chat_photo",
    "delete_chat_photo",
    "group_chat_created",
    "supergroup_chat_created",
    "channel_chat_created",
    "migrate_to_chat_id",
    "migrate_from_chat_id",
    "pinned_message"
])

def wrong_name(message: Message):
    user_id, chat_id = get_ids(message)
    bot.send_message(chat_id=chat_id,
                     text='Кажется, ты отправил не текст. '
                          'Пожалуйста, отправь своё имя в виде текста.')


if __name__ == '__main__':
    create_model()
    bot.infinity_polling()