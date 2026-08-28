import logging
import sys
from logging.handlers import RotatingFileHandler

def log_state(logger, user_id, state):
    """
    Логируем состояние бота
    :param logger: логгер
    :param user_id: id пользователя, для которого установлено состояние
    :param state: установленное состояние бота
    :return: None
    """
    logger.info(f'Пользователь {user_id}. Установлено состояние {state}')


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