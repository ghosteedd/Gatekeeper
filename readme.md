# Gatekeeper

![](https://img.shields.io/appveyor/build/gruntjs/grunt.svg)![](https://img.shields.io/badge/platform-any-lightgrey)![](https://img.shields.io/badge/python-3.10+-blue)![](https://img.shields.io/badge/version-1.2-yellow)

Данный проект содержит реализацию API мобильного приложения "[ПривратникЪ](https://privratnik.net/)", работа с которым осуществляется через телеграм бота.

Основная задача, которую решает данный проект - управление шлагбаумами, используя одну учетную запись в приложении "ПривратникЪ". Т.е. все лица, которые прошли процесс аутентификации (прислали пригласительную команду) могут открывать все шлагбаумы, доступные владельцу номера в оригинальном приложении.

![](https://i.imgur.com/oSkm2jr.gif)

## Функционал бота

Для управления ботом используется нижеследующий набор команд:

* `/start` или `/help` - получение списка доступных команд (в соответствии с привилегиями пользователя)
* `/open_XXX` - открытие шлагбаума № `XXX`
* `/video` - получение ссылок на видео трансляции со шлагбаумов (для просмотра в vlc или аналогичных программах)
* `/invite` - генерация команды (сообщения) приглашения для нового пользователя (доступно **только** владельцу номера телефона)
* `/login` - запрос sms для авторизации в приложении "ПривратникЪ" (доступно **только** владельцу номера телефона)
* `/block_YYY` - заблокировать пользователя с id `YYY` (доступно **только** владельцу номера телефона)
* `/cancel_ZZZ` - аннулировать команду приглашения с кодом `ZZZ` (доступно **только** владельцу номера телефона)

Так же, для контроля актуальности ключа доступа к приложению имеется скрипт `scheduled_tasks.py`, который необходимо периодически запускать.

## Первый запуск

### Подготовка среды

Для windows систем откройте командную строку и выполните следующие команды:
```cmd
cd %gatekeeper_path%
%python_path% -m venv venv
venv\Scripts\activate
```
Для linux систем команды будут следующие (пример для debian):
```bash
apt install python3-venv
cd %gatekeeper_path%
python3 -m venv venv
source ./venv/bin/activate
```
### Установка зависимостей

Для запуска скрипта (-ов) необходимо установить зависимости из файла `requirements.txt` с помощью pip:

* windows: `%python_path% -m pip install -r requirements.txt`
* windows (venv):  `venv\Scripts\pip.exe install -r requirements.txt`
* debian: `apt install python3-pip && python3 -m pip install -r requirements.txt --break-system-packages`
* debian (venv): `./venv/bin/python3 -m pip -r requirements.txt`

### Настройка бота

После подготовки среды, вам будет необходимо создать файл конфигурации. Для этого необходимо запустить скрипт `main.py` с ключем `-s`:

* windows: `%python_path% src\main.py -s`
* windows (venv): `venv\Scripts\python.exe src\main.py -s`
* debian: `python3 src/main.py -s`
* debian (venv): `./venv/bin/python3 src/main.py -s`

Если вы хотите использовать нестандартный путь до файла конфигурации, добавьте к вышеописанной команде  `-c %путь_до_файла_конфигурации%`.

В случае, если вы всё сделали правильно, у вас будут запрошены след. данные:

* номер телефона для приложения "ПривратникЪ" (формат телефона: `+79000000000`)
* код из sms
* токен телеграм бота (для получения напишите [@botfather](https://t.me/BotFather) команду `/newbot` и следуйте инструкции)

После ввода и валидации ваших данных будет необходимо чтоб владелец номера телефона (аккаунта в приложении "ПривратникЪ")  написал вашему боту команду `/own`. Это требуется для определения его `telegram user id`. По окончанию процедуры будет создан файл конфигурации, с 1 авторизованным пользователем - владельцем номера (аккаунта) в приложении "ПривратникЪ".

### Запуск бота

После того, как вы создадите конфигурационный файл, вы можете запустить своего бота одной из след. команд:

* windows: `%python_path% src\main.py`
* windows (venv): `venv\Scripts\python.exe src\main.py`
* debian: `python3 src/main.py`
* debian (venv): `./venv/bin/python3 src/main.py`

Если вы хотите использовать нестандартный путь до файла конфигурации, добавьте к вышеописанной команде  `-c %путь_до_файла_конфигурации%`.


## Разворачивание продуктовой среды

### Пример для debian

После создания окружения (см. раздел выше), создайте файл демона командой:

```bash
nano /etc/systemd/system/gatekeeper.service
```

со следующим содержанием:

```bash
[Unit]
Description=Gatekeeper telegram bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=%gatekeeper_path%
Environment=VIRTUAL_ENV=/%gatekeeper_path%/venv
Environment=PYTHONPATH=/%gatekeeper_path%
ExecStart=%gatekeeper_path%/venv/bin/python %gatekeeper_path%/src/main.py
RestartSec=10
Restart=always
 
[Install]
WantedBy=default.target
```

Если вы хотите использовать нестандартный путь до файла конфигурации, добавьте к параметру `ExecStart` текст  `-c "%путь_до_файла_конфигурации%"`.

После создания файла активируйте и запустите бот:

```bash
systemctl daemon-reload
systemctl enable gatekeeper.service
systemctl start gatekeeper.service
```

После запуска проверьте состояние бота командой `systemctl status gatekeeper.service`. Вы должны увидеть примерно следующие:

![](https://i.imgur.com/OFpolU8.jpeg)

Теперь, когда основная часть бота успешно развернута, нужно добавить в cron периодическую проверку валидности API токена. Для этого, заходим в настройки cron'а командой:

```bash
crontab -e
```

и добавляем в конец строчку:

```
0  12 *  *  * %gatekeeper_path%/venv/bin/pyton3 %gatekeeper_path%/src/scheduled_tasks.py -c %gatekeeper_path%/gatekeeper.conf
```

Теперь каждый день, в 12:00 будет осуществляться проверка API токена.

## Лицензии

Используя данный бот вы соглашаетесь со следующими лицензиями:
* [PSF licence](https://docs.python.org/3/license.html#psf-license-agreement-for-python-release)
* [Apache licence](https://github.com/psf/requests/blob/main/LICENSE)
* [GNU GPL v2.0](https://github.com/eternnoir/pyTelegramBotAPI/blob/master/LICENSE)

(C) Nikolay Sysoev, ghosteedd, 2024
