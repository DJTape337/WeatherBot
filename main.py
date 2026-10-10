import re
from re import fullmatch

import schedule
from telebot import TeleBot, custom_filters
from telebot.types import (Message, ReplyKeyboardMarkup, InlineKeyboardMarkup,
                           KeyboardButton, InlineKeyboardButton)
import time
from threading import Thread
from telebot.storage import StateMemoryStorage
import config
from telebot.states.sync.middleware import StateMiddleware
from telebot.states import State, StatesGroup
from logger import bot_logger, log_info, log_error
from dbase import (create_model, create_user, create_request, update_user_data,
                   create_help_request, User)
from weather_api import get_forecast
from datetime import datetime

#TODO: > надо поставить Redis
state_storage = StateMemoryStorage()
bot = TeleBot(config.token, state_storage=state_storage, use_class_middlewares=True)
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

class StatesSetup(StatesGroup):
    awaiting_name = State()
    awaiting_city = State()
    awaiting_help_message = State()
    configuring_time = State()
    user_ready = State()
    requested_reset = State()
    del_not = State()

def get_data(*args, chat_id, user_id):
    if len(args) > 1:
        out = tuple()
        with bot.retrieve_data(chat_id=chat_id, user_id=user_id) as data:
            for arg in args:
                d = data.get(arg)
                out = out + tuple([d])
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

def menu_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    menu_but = KeyboardButton('/menu')
    markup.add(menu_but)
    return markup

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

def sheduled_forecast():
    now = datetime.now().strftime('%H:%M')
    now_hour = datetime.now().hour
    if now_hour >= 21 or now_hour < 7:
        hello = 'Доброй ночи'
    elif 17 < now_hour < 21:
        hello = 'Добрый вечер'
    elif 12 <= now_hour <= 17:
        hello = 'Добрый день'
    else:
        hello = 'Доброе утро'
    users = User.select().where(
        (User.is_subscribed == True) &
        (User.subscriprion_time == now)
    )
    for user in users:
        city = user.city
        chat_id, user_id = user.chat_id, user.user_id
        if not city or not city in config.cities_coords:
            continue
        lat, lon = config.cities_coords[city]
        bot.send_message(chat_id, f'{hello}, {user.username}!\n'
                                  f'Вот твой прогноз погоды:')
        onetime_forecast(chat_id=chat_id,
                         user_id=user_id,
                         lat=lat,
                         lon=lon)


@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    user_id, chat_id = get_ids(message)
    log_info(bot_logger, user_id, 'Бот запущен.')
    bot.send_message(chat_id=chat_id, text='Привет. Я - бот, предназначенный'
                                                   ' для получения погодных сводок в твоём городе.\n'
                                                   'Я могу присылать сводку о погоде в твоём городе, '
                                                   'а так же автоматически присылать её в установленное тобой время.'
                                                   '\nДля продолжения скажи, как я могу тебя называть?')
    bot.set_state(user_id=user_id,
                  state=StatesSetup.awaiting_name,
                  chat_id=chat_id)
    log_info(bot_logger, user_id, 'Установлено состояние awaiting_name')
    create_user(user_id, chat_id)
    log_info(bot_logger, user_id, 'Создана запись о пользователе в базе данных.')


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
    log_info(bot_logger, user_id, 'Установлено состояние awaiting_city')
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
        log_info(bot_logger, user_id, 'Установлено состояние user_ready')
        bot.send_message(chat_id, text=f'Отлично, бот готов к работе!', reply_markup=menu_button())

@bot.message_handler(state=StatesSetup.user_ready, commands=['menu'])
def send_menu(message: Message):
    user_id, chat_id = get_ids(message)
    name = get_data('name', chat_id=chat_id, user_id=user_id)
    bot.send_message(chat_id,
                     f'Привет, {name}!'
                     f'\nТы можешь узнать прогноз погоды'
                     f' на неделю, а так же автоматически присылать прогноз'
                     f'погоды каждый день в установленное тобой время.'
                     f'\nЕсли у тебя возникли проблемы с ботом, нажми  кнопку "поддержка"',
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
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    lat, lon = get_data('lat', 'lon', chat_id=chat_id, user_id=user_id)
    match call.data:
        case 'onetime':
            onetime_forecast(chat_id, user_id, lat, lon)
        case 'cfg_auto':
            user = User.get(User.user_id == user_id)
            #TODO: > сделать так, чтобы кнопки не работали несколько раз подряд
            markup = InlineKeyboardMarkup()
            btn_cfg = InlineKeyboardButton('Настроить время уведомлений', callback_data='cfg_time')
            markup.row(btn_cfg)
            if user.is_subscribed:
                btn_del_not = InlineKeyboardButton('Отменить уведомления', callback_data='del_not')
                markup.row(btn_del_not)
            bot.send_message(chat_id, 'Выберите действие.', reply_markup=markup)
        case 'help':
            bot.send_message(chat_id=chat_id, text='Пришлите сообщение для поддержки и мы ответим в этот чат'
                                                   'в ближайшее время.')
            bot.set_state(user_id=user_id,
                          chat_id=chat_id,
                          state=StatesSetup.awaiting_help_message)
            log_info(bot_logger, user_id, 'Установлено состояние awaiting_help_message')
        case 'reset':
            bot.set_state(user_id=user_id,
                          chat_id=chat_id,
                          state=StatesSetup.requested_reset)
            log_info(bot_logger, user_id, 'Установлено состояние requested_reset')
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            btn_y = KeyboardButton('Да')
            btn_n = KeyboardButton('Нет')
            markup.add(btn_y, btn_n)
            bot.send_message(chat_id, 'Вы уверены, что хотите сбросить данные пользователя?',
                             reply_markup=markup)
        case 'cfg_time':
            #TODO: >проверить, нужно ли доделать
            bot.set_state(user_id=user_id,
                          chat_id=chat_id,
                          state=StatesSetup.configuring_time)
            log_info(bot_logger, user_id, 'Установлено состояние configuring_time')
            bot.send_message(chat_id, 'Введите время в формате ЧЧ:ММ')
        case 'del_not':
            #TODO: > доделать
            bot.set_state(user_id=user_id, chat_id=chat_id,
                          state=StatesSetup.del_not)
            log_info(bot_logger, user_id, 'Установлено состояние del_not')
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(KeyboardButton('Да'))
            markup.add(KeyboardButton('Нет'))
            bot.send_message(chat_id, 'Вы уверены, что хотите отключить уведомления?',
                             reply_markup=markup)

@bot.message_handler(state=StatesSetup.del_not)
def confirm_del_not(message: Message):
    user_id, chat_id = get_ids(message)
    if message.text.lower() == 'да':
        update_user_data(user_id, 'is_subscribed', False)
        log_info(bot_logger, user_id, 'Установлено состояние user_ready')
        bot.send_message(chat_id, 'Вы отписались от рассылки!', reply_markup=menu_button())
    elif message.text.lower() == 'нет':
        bot.send_message(chat_id, 'Хорошо, подписку оставили.')
    else:
        bot.send_message(chat_id, 'Пожалуйста, ответьте "да" или "нет".')
        return
    bot.set_state(user_id=user_id,
                  chat_id=chat_id,
                  state=StatesSetup.user_ready)


@bot.message_handler(state=StatesSetup.configuring_time)
def input_time(message: Message):
    user_id, chat_id = get_ids(message)
    text = message.text.strip()
    pattern = re.compile(r'^(([01]?\d|2[0-3]):([0-5]\d)$)')
    if not re.fullmatch(pattern, text):
        bot.send_message(chat_id, 'Пожалуйста, введите время напоминания'
                                          ' в соответствии с шаблоном ЧЧ:ММ')
        return
    update_user_data(user_id,
                     'is_subscribed', True)
    update_user_data(user_id, 'subscription_time', text)
    log_info(bot_logger, user_id, 'Настроены автоматические уведомления.')
    bot.set_state(user_id=user_id,
                  chat_id=chat_id,
                  state=StatesSetup.user_ready)


@bot.message_handler(state=StatesSetup.requested_reset)
def confirm_reset(message: Message):
    user_id, chat_id =get_ids(message)
    text = message.text
    while True:
        if text.lower() == 'да':
            bot.set_state(chat_id=chat_id, user_id=user_id,
                          state=StatesSetup.awaiting_name)
            log_info(bot_logger, user_id, 'Подтверждён сброс. Установлено состояние awaiting_name')
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            name = get_data('name', chat_id=chat_id, user_id=user_id)
            markup.add(KeyboardButton(name))
            bot.send_message(chat_id, 'Пожалуйста, введите имя:', reply_markup=markup)
            break
        elif text.lower() == 'нет':
            break
        else:
            bot.send_message(chat_id, 'Пожалуйста, подтвердите сброс данных пользователя.')

@bot.message_handler(state=StatesSetup.awaiting_help_message)
def help_message(message: Message):
    user_id, chat_id = get_ids(message)
    text = message.text
    create_help_request(user_id, text)
    bot.set_state(user_id=user_id, chat_id=chat_id, state=StatesSetup.user_ready)
    bot.send_message(chat_id, 'Сообщение поддержке отправлено.', reply_markup=menu_button())


def onetime_forecast(chat_id, user_id, lat, lon):
    forecast = get_forecast(user_id, city=get_data('city', user_id=user_id, chat_id=chat_id),
                            lat=lat, lon=lon)
    if forecast == 'TimeoutError' or forecast == 'StatusError':
        bot.send_message(chat_id=chat_id, text='Произошла ошибка при запросе. '
                                               'Пожалуйста, повторите попытку.')
        log_error(bot_logger, user_id, forecast)
        return
    temp = forecast['current']['temp']
    wspeed = forecast['current']['wspeed']
    prec = forecast['current']['prec']
    precprob = forecast['current']['precprob']
    cur_text = (f'Погода сейчас:\n'
                f'Температура: {temp} градусов\n'
                f'Скорость ветра: {wspeed} м\\с\n'
                f'Количество осадков: {prec} мм\n'
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
            cur_text += ' Ветра почти нет.'
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
    bot.send_message(chat_id=chat_id, text=daily_text, reply_markup=menu_button())






if __name__ == '__main__':
    create_model()
    schedule.every(1).minutes.do(sheduled_forecast())
    while True:
        schedule.run_pending()
        time.sleep(1)
    bot.infinity_polling()