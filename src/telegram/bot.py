# -*- coding: utf-8 -*-


"""
Обработчики команд telegram бота.

Доступные команды:
* /start - Команда запуска бота
* /help - Команда для получения справки (списка доступных команд)
* /invite - Команда генерации кода приглашения
* /invite_XXXXX - Команда активации кода приглашения и добавление пользователя в список авторизованных
* /login - Авторизация пользователя в приложении привратник (запрос смс)
* /open_XXX - Отправка команды на открытие шлагбаума
* /video - Получение ссылок на трансляции с камер на шлагбаумах
* /block_XXXXXX - заблокировать пользователя с id XXXXXX
* /cancel_XXXXX - аннулировать команду приглашения с кодом XXXXX
"""


import random
import string
import re


try:
    import telebot
except ModuleNotFoundError:
    print('Module "PyTelegramBotAPI" not found! Please install required modules from file "requirements.txt"')
    exit(1)


from . import texts
import gatekeeper
import settings
import logger


def handlers(bot: telebot.TeleBot) -> None:

    def by_user(message: telebot.types.Message, user_str: bool = True) -> str:
        """
        Вспомогательный метод для логирования
        """
        if not isinstance(message, telebot.types.Message):
            return 'UNKNOWN'
        if message.from_user.username is None:
            res = ''
            if user_str:
                res = 'user '
            res += f'with id {message.from_user.id}'
            return res
        else:
            return f'@{message.from_user.username} (id: {message.from_user.id})'

    def load_config(func):
        """
        Декоратор-загрузчик настроек. Для использования необходимо применить данный декоратор ПОСЛЕ декоратора telebot'а
        """

        def updated_function(message: telebot.types.Message, *args, **kwargs):
            config = settings.Settings()
            if config.data is None:
                try:
                    if not config.load():
                        logger.Logger().error(f'[Telegram handlers::load config] Received message "{message.text}" by '
                                              f'{by_user(message)}. Configuration not loaded!')
                        return bot.reply_to(message, texts.CONFIGURATION_NOT_LOADED)
                except IOError as e:
                    logger.Logger().error(f'[Telegram handlers::load config] Received message "{message.text}" by '
                                          f'{by_user(message)}. Configuration not loaded!')
                    logger.Logger().debug(f'Exception text: {str(e)}')
                    return bot.reply_to(message, texts.CONFIGURATION_NOT_LOADED)
            return func(message, config, *args, **kwargs)

        return updated_function

    def no_auth(func):
        """
        Декоратор-фильтр, отсеивающий авторизованных пользователей, включая владельца номера. Для использования
        необходимо применить данный декоратор ПОСЛЕ декоратора load_config
        """

        def updated_function(message: telebot.types.Message, config: settings.Settings, *args, **kwargs):
            if config.data is None:
                logger.Logger().warning(f'[Telegram handlers::no auth] Received message "{message.text}" by '
                                        f'{by_user(message)}. Authentication check failed!')
                return bot.reply_to(message, texts.CONFIGURATION_NOT_LOADED)
            if message.from_user.id in config.data.telegram.access_list or \
               message.from_user.id == config.data.telegram.phone_owner:
                logger.Logger().warning(f'[Telegram handlers::no auth] Received message "{message.text}" by '
                                        f'authorized user {by_user(message, user_str=False)}')
                return lambda: None
            return func(message, config, *args, **kwargs)

        return updated_function

    def auth_only(func):
        """
        Декоратор-фильтр, отсеивающий неавторизованных пользователей. Для использования необходимо применить данный
        декоратор ПОСЛЕ декоратора load_config
        """

        def updated_function(message: telebot.types.Message, config: settings.Settings, *args, **kwargs):
            if config.data is None:
                logger.Logger().warning(f'[Telegram handlers::auth only] Received message "{message.text}" by '
                                        f'{by_user(message)}. Authentication check failed!')
                return bot.reply_to(message, texts.CONFIGURATION_NOT_LOADED)
            if message.from_user.id not in config.data.telegram.access_list and \
               message.from_user.id != config.data.telegram.phone_owner:
                logger.Logger().warning(f'[Telegram handlers::auth only] Received message "{message.text}" by '
                                        f'unauthorized user {by_user(message, user_str=False)}')
                return lambda: None
            return func(message, config, *args, **kwargs)

        return updated_function

    def owner_only(func):
        """
        Декоратор-фильтр, отсеивающий всех пользователей, кроме владельца номера. Для использования необходимо
        применить данный декоратор ПОСЛЕ декоратора load_config
        """

        def updated_function(message: telebot.types.Message, config: settings.Settings, *args, **kwargs):
            if config.data is None:
                logger.Logger().warning(f'[Telegram handlers::owner only] Received message "{message.text}" by '
                                        f'{by_user(message)}. Authentication check failed!')
                return bot.reply_to(message, texts.CONFIGURATION_NOT_LOADED)
            if message.from_user.id != config.data.telegram.phone_owner:
                logger.Logger().warning(f'[Telegram handlers::owner only] Received message "{message.text}" by '
                                        f'{by_user(message)}')
                return lambda: None
            return func(message, config, *args, **kwargs)

        return updated_function

    @bot.message_handler(regexp=r'/invite_\w{1,5}')
    @load_config
    @no_auth
    def activate_invite(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик активации пригласительных кодов и добавления пользователя в список авторизованных
        """
        if len(message.text.split()) > 1:
            if message.forward_from is None:
                logger.Logger().warning(f'[Telegram handlers::activate invite] Received wrong invite message by '
                                        f'{by_user(message)}')
                return bot.send_message(message.chat.id, texts.WRONG_INVITE_CODE)
            if bot.get_me().id != message.forward_from.id:
                logger.Logger().warning(f'[Telegram handlers::activate invite] Received wrong forwarded message by '
                                        f'{by_user(message)}')
                return bot.send_message(message.chat.id, texts.WRONG_INVITE_CODE)
        received_code = re.search(r'/invite_(\w{1,5})', message.text).groups()[0]
        if received_code not in config.data.telegram.invite_codes:
            logger.Logger().warning(f'[Telegram handlers::activate invite] Received wrong invite code ({received_code})'
                                    f' by {by_user(message)}')
            return bot.send_message(message.chat.id, texts.WRONG_INVITE_CODE)
        config.data.telegram.access_list.append(message.from_user.id)
        config.data.telegram.invite_codes.remove(received_code)
        try:
            if config.save():
                logger.Logger().info(f'[Telegram handlers::activate invite] User {by_user(message, user_str=False)} '
                                     f'added to access list (code:{received_code})')
                bot.send_message(message.chat.id, texts.INVITE_CODE_ACTIVATED)
                username = ''
                if message.from_user.username is not None:
                    username = ' @' + message.from_user.username
                return bot.send_message(config.data.telegram.phone_owner,
                                        texts.INVITE_CODE_ACTIVATED_OWNER.format(code=received_code,
                                                                                 username=username,
                                                                                 user_id=message.from_user.id))
            else:
                config.data.telegram.access_list.remove(message.from_user.id)
                config.data.telegram.invite_codes.remove(received_code)
                logger.Logger().error(f'[Telegram handlers::activate invite] User {by_user(message, user_str=False)} '
                                      f'NOT added to access list! Saving configuration file failed! (code: '
                                      f'{received_code})')
                return bot.send_message(message.chat.id, texts.INVITE_CODE_NOT_SAVED_CONF)
        except IOError as e:
            config.data.telegram.access_list.remove(message.from_user.id)
            config.data.telegram.invite_codes.remove(received_code)
            logger.Logger().error(f'[Telegram handlers::activate invite] User {by_user(message, user_str=False)} NOT '
                                  f'added to access list! Saving configuration file failed! (code: {received_code})')
            logger.Logger().debug(f'[Telegram handlers::activate invite] Exception text: {e}')
            return bot.send_message(message.chat.id, texts.INVITE_CODE_NOT_SAVED_CONF)

    @bot.message_handler(commands=['start', 'help'])
    @load_config
    @auth_only
    def start_and_help(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик команды справки
        """
        msg = texts.HELP_PREFIX
        if message.from_user.id == config.data.telegram.phone_owner:
            msg += texts.HELP_PHONE_OWNER
        try:
            api = gatekeeper.GatekeeperAPI(phone=config.data.gatekeeper.phone, key=config.data.gatekeeper.key)
            info = api.get_info()
            if len(info) > 0:
                msg += texts.HELP_GATES_LIST_PREFIX
                i = 1
                for gate in info:
                    msg += texts.HELP_GATE_LIST_ITEM.format(number=i, gate_name=gate.name)
                    i += 1
        except gatekeeper.WrongServerAnswerError:
            logger.Logger().error(f'[Telegram handlers::start/help] Wrong server answer for getting gates info. Request'
                                  f' by {by_user(message)}')
            return bot.send_message(message.chat.id, texts.HELP_WRONG_SERVER_ANSWER)
        except gatekeeper.LogoutError:
            logger.Logger().error(f'[Telegram handlers::start/help] Getting gates info failed. Login required. Request'
                                  f'by {by_user(message)}')
            if message.from_user.id == config.data.telegram.phone_owner:
                return bot.send_message(message.chat.id, texts.HELP_LOGIN_REQUIRED_OWNER)
            else:
                return bot.send_message(message.chat.id, texts.HELP_LOGIN_REQUIRED)
        except ConnectionError:
            logger.Logger().error(f'[Telegram handlers::start/help] Connection to gatekeeper server for getting gates '
                                  f'info failed. Request by {by_user(message)}')
            return bot.send_message(message.chat.id, texts.HELP_CONNECT_TO_SERVER_FAIL)
        msg += texts.HELP_VIDEO_LINKS
        msg = bot.send_message(message.chat.id, msg)
        bot.pin_chat_message(message.chat.id, msg.message_id)

    @bot.message_handler(commands=['video'])
    @load_config
    @auth_only
    def video(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик команды получения ссылок на трансляции с камер на шлагбаумах
        """
        try:
            api = gatekeeper.GatekeeperAPI(phone=config.data.gatekeeper.phone, key=config.data.gatekeeper.key)
            gates_info = api.get_info()
        except gatekeeper.WrongServerAnswerError:
            logger.Logger().error(f'[Telegram handlers::video] Wrong server answer for getting gates info. Request by '
                                  f'{by_user(message)}')
            return bot.send_message(message.chat.id, texts.VIDEO_WRONG_SERVER_ANSWER)
        except gatekeeper.LogoutError:
            logger.Logger().error(f'[Telegram handlers::video] Getting gates info failed. Login required. Request by '
                                  f'{by_user(message)}')
            if message.from_user.id == config.data.telegram.phone_owner:
                return bot.send_message(message.chat.id, texts.VIDEO_LOGIN_REQUIRED_OWNER)
            else:
                return bot.send_message(message.chat.id, texts.VIDEO_LOGIN_REQUIRED)
        except ConnectionError:
            logger.Logger().error(f'[Telegram handlers::video] Connection to gatekeeper server for getting gates info '
                                  f'failed. Request by {by_user(message)}')
            return bot.send_message(message.chat.id, texts.VIDEO_CONNECT_TO_SERVER_FAIL)
        if len(gates_info) < 1:
            logger.Logger().error(f'[Telegram handlers::video] Gatekeeper objects not available. Request by '
                                  f'{by_user(message)}')
            return bot.send_message(message.chat.id, texts.VIDEO_NO_OBJECTS)
        msg = texts.VIDEO_PREFIX
        for gate in gates_info:
            try:
                msg += texts.VIDEO_ITEM.format(link=api.get_stream_link(gate.id), name=gate.name)
            except gatekeeper.WrongServerAnswerError:
                logger.Logger().error(f'[Telegram handlers::video] Wrong server answer for get gate video link. Request'
                                      f' by {by_user(message)}')
                return bot.send_message(message.chat.id, texts.VIDEO_WRONG_SERVER_ANSWER)
            except gatekeeper.LogoutError:
                logger.Logger().error(f'[Telegram handlers::video] Getting gate video link failed. Login required. '
                                      f'Request by {by_user(message)}')
                if message.from_user.id == config.data.telegram.phone_owner:
                    return bot.send_message(message.chat.id, texts.VIDEO_LOGIN_REQUIRED_OWNER)
                else:
                    return bot.send_message(message.chat.id, texts.VIDEO_LOGIN_REQUIRED)
            except ConnectionError:
                logger.Logger().error(f'[Telegram handlers::video] Connection to gatekeeper server for getting gates '
                                      f'info failed.Request by {by_user(message)}')
                return bot.send_message(message.chat.id, texts.VIDEO_CONNECT_TO_SERVER_FAIL)
        logger.Logger().info(f'[Telegram handlers::video] Video links requested by {by_user(message)}')
        return bot.send_message(message.chat.id, msg)

    @bot.message_handler(regexp=r'^/open_\d{1,3}$')
    @load_config
    @auth_only
    def open_gate(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик команды открытия шлагбаума
        """
        gate_number = re.search(r'^/open_(\d{1,3})$', message.text)
        if not gate_number:
            logger.Logger().warning(f'[Telegram handlers::open gate] Bad open gate command. "{message.text}" by '
                                    f'{by_user(message)}')
            return bot.send_message(message.chat.id, texts.WRONG_OPEN_GATE_COMMAND)
        gate_number = int(gate_number.groups()[0])
        api = gatekeeper.GatekeeperAPI(phone=config.data.gatekeeper.phone, key=config.data.gatekeeper.key)
        try:
            gate_info = api.get_info()
        except gatekeeper.WrongServerAnswerError:
            logger.Logger().error('[Telegram handlers::open gate] Wrong server answer for getting gates info. Request '
                                  f'by {by_user(message)} for open gate №{gate_number}')
            return bot.send_message(message.chat.id, texts.OPEN_GATE_WRONG_SERVER_ANSWER)
        except gatekeeper.LogoutError:
            logger.Logger().error(f'[Telegram handlers::open gate] Getting gates info failed. Login required. Request '
                                  f'by {by_user(message)} for open gate №{gate_number}')
            if message.from_user.id == config.data.telegram.phone_owner:
                return bot.send_message(message.chat.id, texts.OPEN_GATE_LOGIN_REQUIRED_OWNER)
            else:
                return bot.send_message(message.chat.id, texts.OPEN_GATE_LOGIN_REQUIRED)
        except ConnectionError:
            logger.Logger().error(f'[Telegram handlers::open gate] Connection to gatekeeper server for getting gates '
                                  f'info failed. Request by {by_user(message)} for open gate №{gate_number}')
            return bot.send_message(message.chat.id, texts.OPEN_GATE_CONNECT_TO_SERVER_FAIL)
        if len(gate_info) == 0:
            logger.Logger().info(f'[Telegram handlers::open gate] No available gates found. Request by '
                                 f'{by_user(message)} for open gate №{gate_number}')
            return bot.send_message(message.chat.id, texts.CLEAN_GATE_LIST)
        if gate_number > len(gate_info) or gate_number < 1:
            logger.Logger().warning(f'[Telegram handlers::open gate] Received wrong gate number ({gate_number} by '
                                    f'{by_user(message)}')
            return bot.send_message(message.chat.id, texts.WRONG_GATE_NUMBER)
        gate = gate_info[gate_number - 1]
        try:
            if api.open_gate(gate.id):
                logger.Logger().info(f'[Telegram handlers::open gate] Gate №{gate_number} opened by {by_user(message)}')
                return bot.reply_to(message, texts.GATE_OPENED)
            else:
                logger.Logger().warning(f'[Telegram handlers::open gate] Gate №{gate_number} NOT opened by '
                                        f'{by_user(message)}')
                return bot.reply_to(message, texts.GATE_NOT_OPENED)
        except gatekeeper.WrongServerAnswerError:
            logger.Logger().error(f'[Telegram handlers::open gate] Wrong server answer for open gate ({gate_number}) by'
                                  f' {by_user(message)}')
            return bot.send_message(message.chat.id, texts.OPEN_GATE_WRONG_SERVER_ANSWER)
        except gatekeeper.LogoutError:
            logger.Logger().error(f'[Telegram handlers::open gate] Open gate ({gate_number}) failed. Login required. '
                                  f'Request by {by_user(message)}')
            if message.from_user.id == config.data.telegram.phone_owner:
                return bot.send_message(message.chat.id, texts.OPEN_GATE_LOGIN_REQUIRED_OWNER)
            else:
                return bot.send_message(message.chat.id, texts.OPEN_GATE_LOGIN_REQUIRED)
        except ConnectionError:
            logger.Logger().error(f'[Telegram handlers::open gate] Connection to gatekeeper server for open gate '
                                  f'({gate_number}) failed. Request by {by_user(message)}')
            return bot.send_message(message.chat.id, texts.OPEN_GATE_CONNECT_TO_SERVER_FAIL)

    @bot.message_handler(commands=['login'])
    @load_config
    @owner_only
    def login(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик входа в приложение привратник (запрос смс)
        """
        config.data.gatekeeper.key = ''
        try:
            if not config.save():
                logger.Logger().error('[Telegram handlers::login] Clear gatekeeper key in configuration file failed!')
                return bot.send_message(message.from_user.id, texts.REQUIRE_SMS_CODE_FAILED)
        except IOError as e:
            logger.Logger().error('[Telegram handlers::login] Clear gatekeeper key in configuration file failed!')
            logger.Logger().debug(f'Exception text: {e}')
            return bot.send_message(message.from_user.id, texts.REQUIRE_SMS_CODE_FAILED)
        api = gatekeeper.GatekeeperAPI(phone=config.data.gatekeeper.phone)
        api.request_sms_code()
        logger.Logger().info('[Telegram handlers::login] Required sms code for gatekeeper')
        return bot.send_message(message.chat.id, texts.REQUIRED_SMS_CODE)

    @bot.message_handler(regexp=r'^\d{5}$')
    @load_config
    @owner_only
    def sms(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик sms кодов для получения api ключа приложения ПривратникЪ
        """
        if not config.data.gatekeeper.key != '':
            return None
        api = gatekeeper.GatekeeperAPI(phone=config.data.gatekeeper.phone)
        try:
            if api.request_api_key(message.text):
                config.data.gatekeeper.key = api.key
                try:
                    if config.save():
                        logger.Logger().info('[Telegram handlers::sms] Gatekeeper api key updated!')
                        return bot.send_message(message.chat.id, texts.API_KEY_UPDATED)
                    else:
                        logger.Logger().error('[Telegram handlers::sms] Gatekeeper api key not saved to configuration '
                                              'file!')
                        logger.Logger().debug(f'[Telegram handlers::sms] API key: {api.key}')
                        return bot.send_message(message.chat.id, texts.API_KEY_NOT_SAVED_CONF)
                except IOError as e:
                    logger.Logger().error('[Telegram handlers::sms] Gatekeeper api key not saved to configuration '
                                          'file!')
                    logger.Logger().debug(f'[Telegram handlers::sms] Exception text: {e}')
                    logger.Logger().debug(f'[Telegram handlers::sms] API key: {api.key}')
                    return bot.send_message(message.chat.id, texts.API_KEY_NOT_SAVED_CONF)
            else:
                logger.Logger().error('[Telegram handlers::sms] SMS code not accepted!')
                return bot.send_message(message.chat.id, texts.API_KEY_NOT_ACCEPTED)
        except gatekeeper.WrongServerAnswerError:
            logger.Logger().error('[Telegram handlers::sms] Wrong server answer for update gatekeeper api key!')
            return bot.send_message(message.chat.id, texts.API_KEY_WRONG_SERVER_ANSWER)
        except ConnectionError:
            logger.Logger().error('[Telegram handlers::sms] Connection gatekeeper api key failed by connection error!')
            return bot.send_message(message.chat.id, texts.API_KEY_CONNECTION_ERROR)

    @bot.message_handler(commands=['invite'])
    @load_config
    @owner_only
    def invite(message: telebot.types.Message, config: settings.Settings):
        """
        Обработчик генерации кодов приглашения
        """
        if len(config.data.telegram.invite_codes) > 50:
            logger.Logger().error('[Telegram handlers::invite] Requested generate an invite code although count of '
                                  'codes has reached maximum!')
            return bot.send_message(message.from_user.id, texts.INVITE_CODES_LIST_LEN_MAX)
        code = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(5))
        config.data.telegram.invite_codes.append(code)
        try:
            if config.save():
                logger.Logger().info(f'[Telegram handlers::invite] Generated new invite code: {code}')
                msg = bot.send_message(message.chat.id, texts.INVITE_CODE_GEN.format(code=code))
                return bot.reply_to(msg, texts.CANCEL_INVITE_CODE_GEN.format(code=code))
            else:
                config.data.telegram.invite_codes.remove(code)
                logger.Logger().error('[Telegram handlers::invite] Generated invite code not saved in configuration '
                                      'file!')
                return bot.send_message(message.chat.id, texts.INVITE_CODE_GEN_NOT_SAVED_CONF)
        except IOError as e:
            logger.Logger().error(f'[Telegram handlers::invite] Generated invite code not saved in configuration file!')
            logger.Logger().debug(f'[Telegram handlers::invite] Exception text: {e}')
            return bot.send_message(message.chat.id, texts.INVITE_CODE_GEN_NOT_SAVED_CONF)

    @bot.message_handler(regexp=r'^/block_\d{1,20}$')
    @load_config
    @owner_only
    def block(message: telebot.types.Message, config: settings.Settings):
        user_id = re.search(r'^/block_(\d{1,20})$', message.text).groups()[0]
        try:
            user_id = int(user_id)
        except ValueError:
            logger.Logger().error(f'[Telegram handlers::block] Convert user id ({user_id}) to integer failed!')
            return bot.send_message(message.chat.id, texts.BLOCK_USER_ID_CONVERT_ERROR)
        if user_id not in config.data.telegram.access_list:
            logger.Logger().warning(f'[Telegram handlers::block] Received block request for user with id {user_id}. '
                                    f'User id not found in configuration file!')
            return bot.send_message(message.chat.id, texts.BLOCK_USER_NOT_EXIST.format(user_id=user_id))
        config.data.telegram.access_list.remove(user_id)
        try:
            if config.save():
                logger.Logger().info(f'[Telegram handlers::block] User with id {user_id} blocked!')
                bot.send_message(message.chat.id, texts.BLOCK_USER_DONE.format(user_id=user_id))
            else:
                config.data.telegram.access_list.append(user_id)
                logger.Logger().error(f'[Telegram handlers::block] User with id {user_id} not blocked! Saving '
                                      f'configuration file failed!')
                return bot.send_message(message.chat.id, texts.BLOCK_USER_NOT_SAVED_CONF.format(user_id=user_id))
        except IOError as e:
            config.data.telegram.access_list.append(user_id)
            logger.Logger().error(f'[Telegram handlers::block] User with id {user_id} not blocked! Saving '
                                  f'configuration file failed!')
            logger.Logger().debug(f'[Telegram handlers::block] Exception text: {e}')
            return bot.send_message(message.chat.id, texts.BLOCK_USER_NOT_SAVED_CONF.format(user_id=user_id))

    @bot.message_handler(regexp=r'^/cancel_\w{1,5}$')
    @load_config
    @owner_only
    def cancel(message: telebot.types.Message, config: settings.Settings):
        """
        Аннулирование кода (команды) приглашения
        """
        invite_code = re.search(r'^/cancel_(\w{1,5})$', message.text).groups()[0]
        if invite_code not in config.data.telegram.invite_codes:
            logger.Logger().error(f'[Telegram handlers::cancel] Invite code {invite_code} not found in configuration '
                                  f'file!')
            return bot.send_message(message.chat.id, texts.CANCEL_INVITE_NOT_EXIST.format(code=invite_code))
        config.data.telegram.invite_codes.remove(invite_code)
        try:
            if config.save():
                logger.Logger().info(f'[Telegram handlers::cancel] Invite code {invite_code} removed from list')
                return bot.send_message(message.chat.id, texts.CANCEL_INVITE_DONE.format(code=invite_code))
            else:
                config.data.telegram.invite_codes.append(invite_code)
                logger.Logger().error(f'[Telegram handlers::cancel] Invite code {invite_code} not removed! Saving '
                                      f'configuration file failed!')
                return bot.send_message(message.chat.id, texts.CANCEL_INVITE_NOT_SAVED_CONF.format(code=invite_code))
        except IOError as e:
            config.data.telegram.invite_codes.append(invite_code)
            logger.Logger().error(f'[Telegram handlers::cancel] Invite code {invite_code} not removed! Saving '
                                  f'configuration file failed!')
            logger.Logger().debug(f'[Telegram handlers::block] Exception text: {e}')
            return bot.send_message(message.chat.id, texts.CANCEL_INVITE_NOT_SAVED_CONF.format(code=invite_code))
