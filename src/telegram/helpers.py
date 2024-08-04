# -*- coding: utf-8 -*-


"""
Вспомогательные методы для работы с telegram ботом
"""


import json
import time
import re


try:
    import requests
except ModuleNotFoundError:
    print('Module "requests" not found! Please install required modules from file "requirements.txt"')
    exit(1)


from . import exceptions
import logger


def send_message(token: str, chat_id: int, message: str, parse_mode: str = 'markdown') -> bool:
    """
    Отправка сообщения телеграм ботом
    :param token: Токен телеграм бота
    :param chat_id: id целевого чата
    :param message: Текст сообщения
    :param parse_mode: Режим форматирования текста (markdown / html)
    :exception ConnectionError: Ошибка соединения с серверами telegram
    :exception WrongAnswerError: Неверный ответ от сервера telegram
    :return: Статус отправленного сообщения
    """
    if not isinstance(token, str) or not isinstance(chat_id, int) or not isinstance(message, str) or \
            not isinstance(parse_mode, str):
        return False
    if token == "" or chat_id < 1 or message == "":
        return False
    if parse_mode.lower() not in ('markdown', 'html'):
        parse_mode = 'markdown'
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = \
        {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode
        }
    try:
        r = requests.post(url=url, data=data).json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError
    except json.decoder.JSONDecodeError:
        raise exceptions.WrongServerAnswerError
    return r.get('ok', False)


def check_token(token: str) -> bool:
    """
    Проверка токена телегам бота на валидность
    :param token: Токен бота, который необходимо проверить
    :exception ConnectionError: Ошибка соединения с сервером telegram
    :exception WrongAnswerError: Неверный ответ от сервера telegram
    :return: валидность токена
    """
    if not isinstance(token, str):
        return False
    if len(token) == '':
        return False
    if not re.search(r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$', token):
        return False
    try:
        return requests.get(f'https://api.telegram.org/bot{token}/getMe').json().get('ok', False)
    except requests.exceptions.ConnectionError:
        raise ConnectionError
    except json.decoder.JSONDecodeError:
        raise exceptions.WrongServerAnswerError


def get_user_id_by_message(token: str, message: str) -> int | None:
    """
    Метод для получения id пользователя, отправившего боту заранее заготовленное (указанное) сообщение
    :param token: Токен телеграм бота
    :param message: Текст сообщения, которое ожидается от пользователя
    :return: id пользователя telegram (None - ошибка)
    """
    if not isinstance(message, str):
        return None
    if len(message) == '':
        return None
    try:
        if not check_token(token):
            return None
    except ConnectionError:
        logger.Logger().error('[telegram helpers::get id by message] Connection to telegram server for check token '
                              'failed!')
        return None
    except exceptions.WrongServerAnswerError:
        logger.Logger().error('[telegram helpers::get id by message] Wrong telegram server answer for check token!')
        return None
    url = f'https://api.telegram.org/bot{token}/getUpdates'
    while True:
        try:
            data = requests.get(url).json()
        except requests.exceptions.ConnectionError:
            logger.Logger().error('[telegram::get id by message] Connection to telegram server for get updates failed!')
            time.sleep(1)
            continue
        except json.decoder.JSONDecodeError:
            raise exceptions.WrongServerAnswerError
        for update in data.get('result', list()):
            text = update.get('message', dict()).get('text', '')
            update_id = int(update.get('update_id', -1))
            user_id = int(update.get('message', dict()).get('from', dict()).get('id', 0))
            try:
                requests.post(url, data={'offset': update_id + 1})
            except requests.exceptions.ConnectionError:
                logger.Logger().error(f'[telegram::get id by message] Connection to telegram server for set update '
                                      f'({update_id}) status failed!')
                time.sleep(1)
                continue
            except json.decoder.JSONDecodeError:
                logger.Logger().error(f'[telegram::get id by message] Wrong server answer for set update ({user_id}) '
                                      f'status')
                time.sleep(1)
                continue
            if message.lower() == text.lower():
                return user_id
        time.sleep(1)
