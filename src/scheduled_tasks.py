#! /usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Метод предназначенный для периодического выполнения, не зависимо от основной части проекта. Это необходимо для
отслеживания состояния api ключа приложения "ПривратникЪ".
Рекомендуемая частота выполнения данного скрипта: не менее 1 раза в день в дневное время.
"""


import argparse


import telegram.exceptions
import telegram.helpers
import telegram.texts
import gatekeeper
import settings


class CheckKeyError(Exception):
    pass


def key_alert(config_path: str | None) -> None:
    """
    Проверка состояния api ключа приложения ПривратникЪ и оповещение пользователя (владельца телефона) о необходимости
    его обновления
    :param config_path: (необязательный) Путь до файла конфигурации
    """

    def check_key() -> bool:
        """
        Проверка статуса действия api ключа приложения ПривратникЪ
        :exception CheckKeyError: Ошибка проверки состояния api ключа
        :return: Текущее состояние api ключа
        """
        config = settings.Settings(config_path)
        try:
            if not config.load():
                raise CheckKeyError('Loading gatekeeper configuration file failed!')
        except IOError:
            raise CheckKeyError('Reading gatekeeper configuration file failed!')
        if len(config.data.gatekeeper.key) == 0:
            return True
        api = gatekeeper.GatekeeperAPI(phone=config.data.gatekeeper.phone, key=config.data.gatekeeper.key)
        try:
            api.get_info()
        except gatekeeper.LogoutError:
            return True
        except gatekeeper.WrongServerAnswerError:
            raise CheckKeyError('Wrong gatekeeper server answer!')
        return False

    try:
        status = check_key()
    except CheckKeyError:
        status = False
    if status:
        try:
            config = settings.Settings(config_path)
            config.load()
        except IOError:
            print('[Scheduled tasks] Reading gatekeeper configuration file failed!')
            return None
        if config.data.telegram.phone_owner < 1:
            print('[Scheduled tasks] Telegram user id of phone number owner is not specified! Resign in required!')
            return None
        print('[Scheduled tasks] Api key excepted! Resign in required!')
        try:
            telegram.helpers.send_message(token=config.data.telegram.bot_token,
                                          chat_id=config.data.telegram.phone_owner,
                                          message=telegram.texts.SCHEDULED_MESSAGE)
        except ConnectionError or telegram.exceptions.WrongServerAnswerError:
            print('[Scheduled tasks] Sending message about requesting a new login failed!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gatekeeper scheduled tasks')
    parser.add_argument('-c', '--config', type=str, default=None, help='custom configuration file')
    key_alert(parser.parse_args().config)
