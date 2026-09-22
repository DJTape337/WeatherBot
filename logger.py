import logging
import sys
from logging.handlers import RotatingFileHandler
from sys import exc_info

def log_info(logger, user_id, info):
    """
    Логируем информацию о работе программы
    :param logger: логгер
    :param user_id: id пользователя
    :param info: информация о работе программы
    :return: None
    """
    logger.info(f'Пользователь {user_id}. {info}')

def log_error(logger, user_id, e):
    logger.error(f'Пользователь {user_id}. Ошибка: {e}',
                 extra={'user_id': user_id},
                 exc_info=True
                 )


def setup_logger(name='bot', level=logging.DEBUG, log_file='bot.log'):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(level)
    logger.propagate = False
    fmt = "%(asctime)s | %(name)s | %(levelname) -8s | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

bot_logger = setup_logger()