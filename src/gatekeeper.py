# -*- coding: utf-8 -*-


"""
Реализация API приложения "ПривратникЪ" (https://privratnik.net).
Стоит понимать: Данное API было получено путем перехвата трафика android приложения. Оно не является публичным и не
документировано. Владелец приложения может изменить данное API в любой момент, а следовательно автор данной реализации
не несёт никакой ответственности за её работоспособность и предоставляет её "как есть".

Порядок работы:

1. Инициализация объекта класса GatekeeperAPI (в конструктор можно передать номер телефона и/или api ключ)

2. Задание номера телефона и/или api ключа, если этого не было сделано ранее (obj.phone=. . ., obj.key=. . .)

Формат номера телефона (int):
* 89000000000
* 79000000000
* 9000000000

3. Если api ключ отсутствует - запрос смс с кодом авторизации (request_sms_code)

3.1. Передача кода из смс серверу и получение api ключа (request_api_key)

4. Проверка наличия доступных объектов (get_info)

5. Если имеются доступные объекты -> открытие необходимого шлагбаума, указав его id (obj.open_gate(obj.get_info()[X].id)

Пример использования:
    import gatekeeper

    api = gatekeeper.GatekeeperAPI()
    api.phone = 79000000000
    api.request_sms_code()
    sms_code = input('Enter sms code:')
    api.request_api_key(sms_code)
    print('Phone:' + api.phone)
    print('API key:' + api.key)
    gates = api.get_info()
    if len(gates) == 0:
        print('Empty object list')
    else:
        api.open_gate(gates[0].id)
        print('Stream URL:' + api.get_stream_link(gates[0].id))
"""


import dataclasses


try:
    import requests
except ModuleNotFoundError:
    print('Module "requests" not found!')
    exit(1)


class WrongServerAnswerError(ConnectionError):
    pass


class LogoutError(Exception):
    pass


@dataclasses.dataclass
class Coordinates:
    x: float
    y: float


@dataclasses.dataclass
class Gate:
    id: int
    coordinates: Coordinates
    address: str
    numbers: tuple
    name: str


class GatekeeperAPI:
    """
    ПривратникЪ API
    """

    __URL = 'https://api.privratnik.net:44590/app/api.php'
    __HEADERS = {'Accept': 'application/json',
                 'Accept-Encoding': 'gzip, deflate, br',
                 'User-Agent': 'okhttp/4.9.2',
                 'Connection': 'close'}

    _phone: int | None = None
    _api_key: str | None = None
    _gates: list | None = None

    @property
    def phone(self) -> int | None:
        return self._phone

    @phone.setter
    def phone(self, value: int):
        if not isinstance(value, int):
            raise TypeError('Phone is not a number!')
        phone_str = str(value)
        if len(phone_str) == 10:
            phone_str = '7' + phone_str
        if len(phone_str) != 11:
            raise ValueError('Wrong phone number length!')
        if phone_str[0] == '8':
            phone_str = '7' + phone_str[1:]
        self._phone = int(phone_str)

    @property
    def key(self) -> str | None:
        return self._api_key

    @key.setter
    def key(self, value: str):
        if not isinstance(value, str):
            raise TypeError('Api key is not a string!')
        if len(value) != 32:
            raise ValueError('Wrong api key length!')
        self._api_key = value

    def __init__(self, phone: int | None = None, key: str | None = None):
        if phone is not None:
            self.phone = phone
        if key is not None:
            self.key = key

    def request_sms_code(self) -> bool:
        """
        Запрос смс с кодом для авторизации
        :exception TypeError: Не указан номер телефона
        :exception ConnectionError: Ошибка отправки запроса
        :exception WrongServerAnswerError: Неверный код ответа/неверное значение ответа от сервера
        :return: True - код отправлен, False - код не отправлен, используйте предыдущий
        """
        if self._phone is None:
            raise TypeError('Please set phone number')
        try:
            req = requests.post(self.__URL, headers=self.__HEADERS, files={'number': (None, self._phone)})
        except Exception as e:
            raise ConnectionError(str(e))
        if req.status_code != 200:
            raise WrongServerAnswerError('Wrong status code')
        if len(req.text) == 0:
            raise WrongServerAnswerError('Empty response')
        try:
            resp = req.json()
        except Exception as e:
            raise WrongServerAnswerError(f'Wrong response ({str(e)})')
        if resp.get('state', 0) == 1:
            return True
        return False

    def request_api_key(self, sms_code: str) -> bool:
        """
        Запрос API ключа
        :param sms_code: Код из смс (строкой)
        :exception TypeError: Не указан номер телефона/неверный тип кода из смс
        :exception ValueError: Неверное значение кода из смс
        :exception ConnectionError: Ошибка отправки запроса серверу
        :exception WrongServerAnswerError: Неверный код ответа/неверное значение ответа от сервера
        :return: True - ключ получен, False - ошибка авторизации
        """
        if self._phone is None:
            raise TypeError('Please set phone number')
        if not isinstance(sms_code, str):
            raise TypeError('Wrong sms code type')
        try:
            int(sms_code)
        except ValueError:
            raise ValueError('Wrong sms code value')
        if len(sms_code) != 5:
            raise ValueError('Wrong sms code length')
        try:
            req = requests.post(self.__URL, headers=self.__HEADERS, files={'number': (None, self._phone),
                                                                           'smsCode': (None, sms_code)})
        except Exception as e:
            raise ConnectionError(str(e))
        if req.status_code != 200:
            raise WrongServerAnswerError('Wrong status code')
        if len(req.text) == 0:
            raise WrongServerAnswerError('Empty response')
        try:
            key = req.json().get('key', 0)
        except Exception as e:
            raise WrongServerAnswerError(f'Wrong response ({str(e)})')
        if key == 0:
            return False
        self._api_key = key
        return True

    def get_info(self) -> list:
        """
        Получение информации о доступных объектах
        :exception TypeError: Неверное значение номера телефона/API ключа
        :exception ConnectionError: Ошибка отправки запроса серверу
        :exception WrongServerAnswerError: Неверный код ответа/неверное значение ответа от сервера
        :exception LogoutError: API ключ аннулирован
        :return: Список объектов Gate с информацией о доступных объектах
        """
        if not isinstance(self._phone, int):
            raise TypeError('Wrong phone number')
        if not isinstance(self._api_key, str):
            raise TypeError('Wrong api key')
        try:
            req = requests.post(self.__URL, headers=self.__HEADERS, files={'barrier': (None, ''),
                                                                           'login': (None, self._phone),
                                                                           'key': (None, self._api_key)})
        except Exception as e:
            raise ConnectionError(str(e))
        if req.status_code != 200:
            raise WrongServerAnswerError('Wrong status code')
        if len(req.text) == 0:
            raise WrongServerAnswerError('Empty response')
        try:
            resp = req.json()
        except Exception as e:
            raise WrongServerAnswerError(f'Wrong response ({str(e)})')
        if not isinstance(resp, list):
            if resp.get('login', 'X') == '0':
                raise LogoutError
            return list()
        result = list()
        if self._gates is None:
            self._gates = list()
        else:
            self._gates.clear()
        for item in resp:
            try:
                gate_id = int(item.get('id', 0))
            except ValueError:
                gate_id = 0
            self._gates.append(gate_id)
            gate = Gate(id=gate_id,
                        coordinates=Coordinates(x=item.get('coordinate_X', 0.0), y=item.get('coordinate_Y', 0.0)),
                        address=item.get('address', ''),
                        numbers=(item.get('number'), item.get('number2')),
                        name=item.get('user_info'))
            result.append(gate)
        return result

    def open_gate(self, gate_id: int) -> bool:
        """
        Открытие шлагбаума
        :param gate_id: id шлагбаума
        :exception TypeError: Неверное значение номера телефона/API ключа
        :exception ConnectionError: Ошибка отправки запроса серверу
        :exception WrongServerAnswerError: Неверный код ответа/неверное значение ответа от сервера
        :exception LogoutError: API ключ приложения аннулирован
        :return: True - шлагбаум поднят, False - ошибка
        """
        if not isinstance(self._phone, int):
            raise TypeError('Wrong phone number')
        if not isinstance(self._api_key, str):
            raise TypeError('Wrong api key')
        if self._gates is None:
            self.get_info()
        if gate_id not in self._gates or gate_id < 1:
            return False
        try:
            req = requests.post(self.__URL, headers=self.__HEADERS, files={'barrier_id': (None, gate_id),
                                                                           'command': (None, 'open'),
                                                                           'login': (None, self._phone),
                                                                           'key': (None, self._api_key)})
        except Exception as e:
            raise ConnectionError(str(e))
        if req.status_code != 200:
            raise WrongServerAnswerError('Wrong status code')
        if len(req.text) == 0:
            raise WrongServerAnswerError('Empty response')
        try:
            resp = req.json()
        except Exception as e:
            raise WrongServerAnswerError(f'Wrong response ({str(e)})')
        if resp.get('state', 0) == 1:
            return True
        else:
            return False

    def get_stream_link(self, gate_id: int) -> str:
        """
        Ссылка на видеопоток с камеры на шлагбауме
        :param gate_id: id шлагбаума
        :exception TypeError: Неверное значение номера телефона/API ключа
        :exception ConnectionError: Ошибка отправки запроса серверу
        :exception WrongServerAnswerError: Неверный код ответа/неверное значение ответа от сервера
        :exception LogoutError: API ключ аннулирован
        :return: ссылка на видео поток с камеры на шлагбауме или пустая строка в случае ошибки
        """
        if not isinstance(self._phone, int):
            raise TypeError('Wrong phone number')
        if not isinstance(self._api_key, str):
            raise TypeError('Wrong api key')
        if self._gates is None:
            self.get_info()
        if gate_id not in self._gates or gate_id < 1:
            return ''
        try:
            req = requests.post(self.__URL, headers=self.__HEADERS, files={'barrier_id': (None, gate_id),
                                                                           'cam': (None, ''),
                                                                           'login': (None, self._phone),
                                                                           'key': (None, self._api_key)})
        except Exception as e:
            raise ConnectionError(str(e))
        if req.status_code != 200:
            raise WrongServerAnswerError('Wrong status code')
        if len(req.text) == 0:
            raise WrongServerAnswerError('Empty response')
        try:
            resp = req.json()
        except Exception as e:
            raise WrongServerAnswerError(f'Wrong response ({str(e)})')
        if not isinstance(resp, list):
            return ''
        else:
            resp = resp[0]
        if isinstance(resp, list):
            resp = resp[0]
        video_id = resp.get('id')
        token = resp.get('token')
        server = resp.get('domain')
        if video_id is not None and token is not None and server is not None:
            return f'https://{server}/{video_id}/mpegts?token={token}'
        return ''
