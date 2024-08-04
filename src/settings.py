# -*- coding: utf-8 -*-


"""
Классы для сохранения и загрузки настроек с данными для API привратникЪ'а и telegram бота.

Данные хранятся в json файле. По умолчанию файл настроек храниться в рабочей директории и называется gatekeeper.conf,
однако можно указать иной путь через переменную среды "GATEKEEPER_CONF" или с помощью аргумента в конструкторе объекта.

Пример файла настроек:
{
    "gatekeeper": {
        "phone": 79000000000,
        "key": "base64 encoded string"
    },
    "telegram": {
        "bot_token": "base64 encoded string",
        "access_list": [tg_id_1, tg_id_2, ...],
        "phone_owner": tg_id_3,
        "invite_codes": ["x", "y", "z"]
    },
    "logger": {
        "level": 1,
        "print_log"
        "force_use_file": false,
        "file_path": "/path/to/file.log"
    }
}

Описание значений:
- gatekeeper - настройки api привратника
    - phone - номер телефона, который будет использоваться в api привратника
    - key - base64 хеш ключа api привратника
- telegram - настройки telegram бота
    - bot_token - настройки необходимые для работы
    - access_list - список id пользователей, которые будут иметь доступ к функционалу бота
    - phone_owner - id пользователя имеющего доступ к номеру телефона, который используется в api привратника
    - invite_codes - список одноразовых кодов, которые будут использоваться для добавление нового пользователя в список
пользователей
- logger - (необязательно) настройки логирования
    - level - (необязательно) уровень логирования, принимаемые значения 0-5 (по умолчанию: 1)
    - print_log - (необязательно) дублирование записи лога в консоль (по умолчанию: false)
    - force_use_file - (необязательно) принудительная запись лога в файл (актуально для linux систем, по умолчанию: false)
    - file_path - (необязательно) путь до файла, куда будет писаться логи (по умолчанию: %current_dir%/gatekeeper.log)
"""


import dataclasses
import base64
import json
import os
import re


import logger


@dataclasses.dataclass
class GatekeeperData:
    phone: int
    key: str


@dataclasses.dataclass
class TelegramData:
    bot_token: str
    access_list: list
    phone_owner: int
    invite_codes: list


@dataclasses.dataclass
class SettingsData:
    gatekeeper: GatekeeperData
    telegram: TelegramData


class Settings:
    __instance = None
    __initialized: bool = False

    __DEFAULT_FILE_PATH: str = 'gatekeeper.conf'

    _data: SettingsData | None = None
    _file_path: str

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, file_path: str | None = None, autoload: bool = False):
        """
        :param file_path: Путь до файла настроек
        :param autoload: Загрузка настроек при инициализации объекта
        :exception IOError: Ошибка чтения файла настроек
        """
        if self.__initialized:
            return
        self.__initialized = True
        if not isinstance(file_path, str):
            if os.environ.get('GATEKEEPER_CONF') is None:
                self._file_path = self.__DEFAULT_FILE_PATH
            else:
                self._file_path = os.environ.get('GATEKEEPER_CONF')
        else:
            if len(file_path) == 0:
                self._file_path = self.__DEFAULT_FILE_PATH
            else:
                self._file_path = file_path
        self._data = None
        if autoload:
            self.load()

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def data(self) -> SettingsData | None:
        return self._data

    @data.setter
    def data(self, value: SettingsData) -> None:
        """
        :exception TypeError: Ошибка в типе данных одного из значений
        :exception ValueError: Ошибка в данных одного из значений
        """
        if not isinstance(value, SettingsData):
            raise TypeError('Wrong root value type')
        if not isinstance(value.gatekeeper, GatekeeperData) or not isinstance(value.telegram, TelegramData):
            raise TypeError('Wrong gatekeeper or telegram data type')
        if not isinstance(value.gatekeeper.phone, int) or not isinstance(value.gatekeeper.key, str):
            raise TypeError('Wrong gatekeeper phone/key data type')
        if len(str(value.gatekeeper.phone)) not in (10, 11) or len(value.gatekeeper.key) not in (0, 32):
            raise ValueError('Wrong gatekeeper phone/key data')
        if not isinstance(value.telegram.bot_token, str) or not isinstance(value.telegram.access_list, list) or \
           not isinstance(value.telegram.phone_owner, int) or not isinstance(value.telegram.invite_codes, list):
            raise TypeError('Wrong telegram data type')
        if not re.search(r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$', value.telegram.bot_token):
            raise ValueError('Wrong telegram bot token')
        for user_id in value.telegram.access_list:
            if not isinstance(user_id, int):
                raise TypeError('Wrong type of telegram user id (access list)')
        for code in value.telegram.invite_codes:
            if not isinstance(code, str):
                raise TypeError('Wrong type of telegram invite code')
            if len(code) == 0:
                value.telegram.invite_codes.remove(code)
        self._data = value

    def save(self) -> bool:
        """
        Сохранение данных в конфигурационный файл
        :return: True - данные сохранены, False - ошибка в данных/пути до файла
        :exception IOError: Ошибка записи файла
        """
        if self.data is None or self._file_path is None or self._file_path == '':
            return False
        data = {
                'gatekeeper': {
                    'phone': self.data.gatekeeper.phone,
                    'key': base64.b64encode(self.data.gatekeeper.key.encode()).decode()
                },
                'telegram': {
                    'bot_token': base64.b64encode(self.data.telegram.bot_token.encode()).decode(),
                    'access_list': self.data.telegram.access_list,
                    'phone_owner': self.data.telegram.phone_owner,
                    'invite_codes': self.data.telegram.invite_codes
                },
                'logger': {
                    'level': logger.Logger().log_level.value,
                    'print_log': logger.Logger().print_log,
                    'force_use_file': logger.Logger().force_use_file_log,
                    'file_path': logger.Logger().file_path
                }
        }
        try:
            with open(self._file_path, 'w') as f:
                json.dump(data, f)
            return True
        except Exception as e:
            raise IOError(str(e))

    def load(self) -> bool:
        """
        Загрузка данных из конфигурационного файла
        :return: True - настройки сохранены. False - ошибка в данных/пути до файла
        :exception IOError: Ошибка чтения файла настроек
        """
        if self._file_path is None:
            return False
        if not os.path.exists(self._file_path) or not os.path.isfile(self._file_path):
            return False
        try:
            with open(self._file_path, 'r') as f:
                json_data = json.load(f)
        except Exception as e:
            raise IOError(str(e))
        try:
            token = base64.b64decode(json_data.get('telegram', dict()).get('bot_token').encode()).decode()
            key = base64.b64decode(json_data.get('gatekeeper', dict()).get('key').encode()).decode()
        except Exception as e:
            raise IOError(str(e))
        telegram_data = TelegramData(bot_token=token,
                                     access_list=json_data.get('telegram', dict()).get('access_list'),
                                     phone_owner=json_data.get('telegram', dict()).get('phone_owner'),
                                     invite_codes=json_data.get('telegram', dict()).get('invite_codes'))
        gatekeeper_data = GatekeeperData(phone=json_data.get('gatekeeper', dict()).get('phone'),
                                         key=key)
        try:
            self.data = SettingsData(gatekeeper=gatekeeper_data, telegram=telegram_data)
        except (TypeError or ValueError) as e:
            raise IOError(str(e))
        if isinstance(json_data.get('logger'), dict):
            log_level = json_data.get('logger').get('level', 1)
            if isinstance(log_level, int):
                if 0 <= log_level <= 5:
                    logger.Logger().log_level = logger.LogLevel(log_level)
            print_log = json_data.get('logger').get('print_log')
            if isinstance(print_log, bool):
                logger.Logger().print_log = print_log
            force_use_file = json_data.get('logger').get('force_use_file')
            if isinstance(force_use_file, bool):
                logger.Logger().force_use_file_log = force_use_file
            log_file_path = json_data.get('logger').get('file_path')
            if isinstance(log_file_path, str) and log_file_path != '':
                logger.Logger().file_path = log_file_path
        return True
