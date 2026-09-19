from telebot import TeleBot, custom_filters
from telebot.types import (Message, ReplyKeyboardMarkup, InlineKeyboardMarkup,
                           KeyboardButton, InlineKeyboardButton)
from telebot.storage import StateMemoryStorage
import config
from telebot.states.sync.middleware import StateMiddleware
from telebot.states import State, StatesGroup
from logger import bot_logger, log_state, log_info
from dbase import create_model, create_user, create_request, update_user_data, get_user_data
from weather_api import get_forecast

state_storage = StateMemoryStorage()
bot = TeleBot(config.token, state_storage=state_storage, use_class_middlewares=True)
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

class StatesSetup(StatesGroup):
    awaiting_name = State()
    awaiting_city = State()
    user_ready = State()
    confirm_reset = State()

def get_data(*args, chat_id, user_id):
    if len(args) > 1:
        out = tuple()
        with bot.retrieve_data(chat_id=chat_id, user_id=user_id) as data:
            for arg in args:
                d = data.get(arg)
                out += tuple(d)
        return out
    else:
        with bot.retrieve_data(chat_id=chat_id, user_id=user_id) as data:
            out = data.get(args[0])
            return out

def get_ids(message: Message):
    """
    Получаем id пользователя и чата из сообщения
    :param message: сообщение пользователя
    :return: id пользователя, id чата
    """
    user_id = message.from_user.id
    chat_id = message.chat.id
    return user_id, chat_id

def gen_menu_markup():
    markup = InlineKeyboardMarkup()
    btn_onetime_forecast = InlineKeyboardButton('Прогноз', callback_data='onetime')
    btn_cfg_autoforecast = InlineKeyboardButton('Настроить автоматический прогноз',
                                                callback_data='cfg_auto')
    btn_help = InlineKeyboardButton('Поддержка', callback_data='help')
    btn_reset = InlineKeyboardButton('Сбросить данные пользователя', callback_data='reset')
    markup.row(btn_onetime_forecast)
    markup.row(btn_cfg_autoforecast)
    markup.row(btn_help)
    markup.row(btn_reset)
    return markup

def gen_cities_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keys_list = list(config.cities_coords.keys())
    for i in range(0, len(keys_list), 2):
        pair = keys_list[i:i+2]
        formatted = [s[0].upper() + s[1:] for s in pair]
        markup.row(*formatted)
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
    update_user_data(user_id=user_id, datatype='username', data=name)
    log_info(bot_logger, user_id=user_id, info='Обновлено имя в базе данных.')
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
        msg = bot.send_message(chat_id, text=f'Отлично, бот готов к работе!')
        bot.register_next_step_handler(msg, send_menu)
def send_menu(message: Message):
    user_id, chat_id = get_ids(message)
    name = get_data('name', chat_id=chat_id, user_id=user_id)
    bot.send_message(chat_id,
                     f'Привет, {name}! '
                     f'Я - бот, который поможет тебе узнать прогноз погоды'
                     f' на неделю, а так же автоматически присылать прогноз'
                     f'погоды каждый день в установленное тобой время.'
                     f' Если у тебя возникли проблемы с ботом, нажми  кнопку "поддержка"',
                     reply_markup=gen_menu_markup())

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

@bot.callback_query_handler(func=lambda call: True)
def handle_menu_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    lat, lon = get_data('lat', 'lon', chat_id=chat_id, user_id=user_id)
    if call.data == 'onetime':
        onetime_forecast(chat_id, user_id, lat, lon)

def onetime_forecast(chat_id, user_id, lat, lon):
    forecast = get_forecast(user_id, lat=lat, lon=lon)
    temp = forecast['current']['temp']
    wspeed = forecast['current']['wspeed']
    prec = forecast['current']['prec']
    precprob = forecast['current']['precprob']
    cur_text = (f'Погода сейчас:\n'
                f'Температура: {temp} градусов\n'
                f'Скорость ветра: {wspeed} м\\с\n'
                f'Количество осадков: {prec} мм'
                f'Вероятность осадков в ближайшее время: {precprob}%\n')
    match temp:
        case x if 20 < x < 30:
            cur_text += 'Сегодня тепло! Можно выйти на улицу в лёгкой одежде.'
        case x if x >= 30:
            cur_text += 'Сегодня жарко! При выходе на улицу остерегайтесь перегрева.'
        case x if 7 < x <=20:
            cur_text += 'Сегодня прохладно!'
        case x if x <= 7:
            cur_text += 'Сегодня холодно! Позаботьтесь о том, чтобы не замёрзнуть на улице.'
    match wspeed:
        case x if x <= 3.3:
            cur_text += 'Ветра почти нет.'
        case x if 3.3 < x <= 7.9:
            cur_text += 'Умеренный ветер.'
        case x if 7.9 < x <= 13.8:
            cur_text += 'Сильный ветер. Соблюдайте осторожность при выходе на улицу.'
        case x if 13.8 < x < 24:
            cur_text += 'Очень сильный ветер. Выходите из дома только при крайней необходимости.'
        case x if x >= 24:
            cur_text += 'На улице ураган! Крайне не рекомендуется выходить из дома.'
    match prec:
        case x if x < 2.5:
            cur_text += 'Наблюдаются слабые осадки.'
        case x if 2.5 <= x < 10:
            cur_text += 'Наблюдаются умеренные осадки'
        case x if x > 10:
            cur_text += 'Сильные осадки! Будьте осторожны.'
    bot.send_message(chat_id=chat_id, text=cur_text)
    daily_text = 'Прогноз погоды на 7 дней:\n'
    for day in forecast['daily']:
        text = (f'{day[0]}:\n'
                f'Минимальная температура: {day[1]} градусов\n'
                f'Максимальная температура: {day[2]} градусов\n'
                f'Минимальная скорость ветра: {day[3]} м\\с\n'
                f'Максимальная скорость ветра: {day[4]} м\\с\n'
                f'Предполагаемая сумма осадков: {day[5]} мм\n\n')
        daily_text += text
    markup = ReplyKeyboardMarkup(resize_keyboard= True, one_time_keyboard= True)
    menu_but = KeyboardButton('Меню')
    markup.add(menu_but)
    bot.send_message(chat_id, daily_text, reply_markup=markup)



if __name__ == '__main__':
    create_model()
    bot.infinity_polling()