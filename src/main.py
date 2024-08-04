#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import re
import os


try:
    import syslog
    del syslog
    SYSLOG_AVAILABLE = True
except ModuleNotFoundError:
    import pathlib
    SYSLOG_AVAILABLE = False


try:
    import telebot
except ModuleNotFoundError:
    print('Module "PyTelegramBotAPI" not found! Please install required modules from file "requirements.txt"')
    exit(1)


import telegram.exceptions
import telegram.helpers
import telegram.bot
import gatekeeper
import settings
import logger


def setup(config_path: str | None = None) -> None:
    """
    Интерактивный метод для создания файла конфигурации
    :param config_path: Путь до будущего файла конфигурации
    """
    if config_path is None:
        config_path = settings.Settings().file_path
    if os.path.exists(config_path) and os.path.isfile(config_path):
        if os.path.exists(config_path + '.old') and os.path.isfile(config_path + '.old'):
            print('Файл конфигурации уже существует!')
            return None
        try:
            os.rename(config_path, config_path + '.old')
        except Exception as e:
            print(f'Ошибка переименования старого файла конфигурации! Проверьте права на запись/чтение и запустите '
                  f'установку заново. (Текст ошибки: {e})')
            return None
        try:
            f = open(config_path, 'w')
            f.close()
            os.remove(config_path)
        except Exception as e:
            print(f'Ошибка тестовой записи в конфигурационный файл! Проверьте права на запись/чтение и запустите '
                  f'установку заново. (Текст ошибки: {e})')
            return None
    print('Добро пожаловать в первоначальную настройку бота-посредника приложения "ПривратникЪ"!')
    print('Для начала давай войдем в аккаунт приложения "ПривратникЪ".')
    while True:
        phone = input('Введи номер телефона: ')
        if phone == '':
            print('Ввод номера телефона нельзя пропустить!')
            continue
        phone = re.sub(r'[+\-() ]', '', phone)
        if len(phone) not in (10, 11):
            print('Неверное значение номера телефона!')
            continue
        try:
            phone = int(phone)
        except ValueError:
            print('Неверное значение номера телефона!')
            continue
        break
    api = gatekeeper.GatekeeperAPI(phone=phone)
    try:
        if api.request_sms_code():
            print('Запрошено sms с кодом для проведения авторизации.')
        else:
            print('Ошибка при запросе sms для проведения авторизации! Попробуй произвести установку заново через 5 '
                  'минут.')
            return None
    except gatekeeper.WrongServerAnswerError:
        print('При запросе sms кода сервер приложения "ПривратникЪ" вернул неверный ответ! Попробуй произвести '
              'установку заново.')
        return None
    except ConnectionError:
        print('Ошибка подключения к серверу приложения "ПривратникЪ" для запроса sms кода. Попробуй произвести '
              'установку заново.')
        return None
    while True:
        code = input('Введи код из sms: ')
        if code == '':
            print('Ввод кода из sms нельзя пропустить!')
            continue
        if len(code) != 5:
            print('Неверное значение кода из sms!')
            continue
        try:
            int(code)
        except ValueError:
            print('Неверное значение кода из sms!')
            continue
        break
    try:
        if api.request_api_key(code):
            print('Авторизация прошла успешно.')
        else:
            print('Ошибка авторизации! Попробуй произвести установку заново.')
            return None
    except ValueError:
        print('Неверное значение кода из sms! Попробуй произвести установку заново.')
        return None
    except gatekeeper.WrongServerAnswerError:
        print('При попытке получения api ключа приложения "ПривратникЪ", сервер вернул неверный ответ! Попробуй '
              'произвести установку заново')
        return None
    except ConnectionError:
        print('Ошибка подключения к серверу приложения "ПривратникЪ" для получения api ключа! Попробуй произвести '
              'установку заново.')
        return None
    gatekeeper_configuration = settings.GatekeeperData(phone=api.phone, key=api.key)
    print('Отлично! Теперь приступим к настройке телеграм бота.')
    while True:
        token = input('Введи токен бота: ')
        if token == '':
            print('Ввод токена телеграм бота нельзя пропустить!')
            continue
        if not re.search(r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$', token):
            print('Неверный формат токена телеграм бота!')
            continue
        try:
            if telegram.helpers.check_token(token):
                break
            else:
                print('Неверный токен бота!')
                continue
        except ConnectionError:
            print('Ошибка подключения к серверу телеграм! Попробуй произвести установку заново.')
            return None
        except telegram.exceptions.WrongServerAnswerError:
            print('Сервер телеграма вернул неверный ответ! Попробуй произвести установку заново.')
            return None
    print('И последний пункт. Отправь боту сообщение "/own", если ты являешься владельцем ранее введенного номера, '
          'иначе попроси владельца его отправить.')
    phone_owner = telegram.helpers.get_user_id_by_message(token, '/own')
    if phone_owner is None:
        print('Ошибка получения id пользователя телеграм. Попробуй произвести установку заново.')
        return None
    telegram_configuration = settings.TelegramData(bot_token=token,
                                                   access_list=list(),
                                                   phone_owner=phone_owner,
                                                   invite_codes=list())
    config = settings.Settings(config_path)
    try:
        config.data = settings.SettingsData(gatekeeper=gatekeeper_configuration, telegram=telegram_configuration)
    except (TypeError or ValueError):
        print('Ошибка задания значений конфигурационных параметров! Попробуйте выполнить установку заново.')
        return None
    print('Супер! Сохраняем конфигурацию. . .')
    try:
        if config.save():
            print('Файл конфигурации сохранен! Приятного использования!')
            return None
        else:
            print('Ошибка сохранения файла конфигурации! Проверь доступ к файлу на чтение/запись, указанные значения и '
                  'произведи установку заново.')
            return None
    except IOError:
        print('Ошибка сохранения файла конфигурации! Проверь доступ к файлу на чтение/запись и произведи установку '
              'заново.')
        return None


def main(config_path: str | None = None) -> None:
    """
    :param config_path: Путь до файла конфигурации
    """
    if config_path is None:
        config_path = settings.Settings().file_path
    if not SYSLOG_AVAILABLE:
        logger.Logger(file_path=pathlib.Path(config_path).stem + '.log')
    if not os.path.exists(config_path):
        logger.Logger().critical('[Main] Configuration file not found!')
        return None
    try:
        f = open(config_path, 'r+')
        f.close()
    except Exception as e:
        logger.Logger().critical(f'[Main] Configuration file cannot be read! Exception text: {e}')
        return None
    config = settings.Settings(file_path=config_path)
    try:
        if not config.load():
            logger.Logger().critical('[Main] Configuration file not loaded!')
            return None
    except IOError:
        logger.Logger().critical(f'[Main] Configuration file cannot be read!')
        return None
    bot = telebot.TeleBot(config.data.telegram.bot_token)
    telegram.bot.handlers(bot)
    bot.infinity_polling(skip_pending=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gatekeeper telegram bot')
    parser.add_argument('-s', '--setup', action='store_true', help='setup dialog')
    parser.add_argument('-c', '--config', type=str, default=None, help='path to the configuration file')
    args = parser.parse_args()
    if args.setup:
        setup(args.config)
    else:
        main(args.config)
