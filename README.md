# homework_bot - Телеграм-бот
### Проверяет статус проверки домашней работы на платформе Яндекс.Практикум
Опрашивает API Практикума каждые десять минут на предмет изменения статуса.
Логирует и уведомляет в чате об ошибках возникающих в ходе работы.

## Как запустить:
* клонировать репозиторий и перейти в папку проекта
```
git clone https://github.com/KlavaD/homework_bot.git
cd homework_bot
```
* создать виртуальное окружение и установить зависимости
```
python -m venv venv
. venv/Scripts/activate (для Windows)
. venv/bin/activate (для linux)
pip install -r requirements.txt
```
* создать файл с переменными окружение .env
```
PRACTICUM_TOKEN='<your_token>'
TELEGRAM_TOKEN='<your_token>'
TELEGRAM_CHAT_ID=<your_chat_id>
```
* запустить
```
python homework.py
```