import logging
import os
import sys

import requests
import telegram
import time
import exceptions

from dotenv import load_dotenv

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 5
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def send_message(bot, message):
    """ отправляет сообщение в Telegram чат """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Отправлено сообщение в телеграм')
    except exceptions.MassageDontSent:
        raise 'При отправке сообщения произошла ошибка'


def get_api_answer(current_timestamp):
    """ делает запрос """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise exceptions.UrlNotAvailable('URL не доступен')
        return response.json()
    except Exception:
        raise exceptions.ApiAnswerError('При запросе произошла ошибка')


def check_response(response):
    """ проверяет ответ API на корректность """
    if isinstance(response['homeworks'], list):
        return response['homeworks']
    else:
        raise TypeError('тип ответа не соответствует списку')


def parse_status(homework):
    """ извлекает из информации о конкретной
    домашней работе статус этой работы. """

    homework_name = homework['homework_name']
    try:
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}".{verdict}'
    except KeyError:
        raise 'ключ в ответе отсутствует в перечне ключей'


def check_tokens():
    """ Проверяет доступность переменных окружения """
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for token in tokens:
        if token is None or len(str(token)) == 0:
            return False

    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует переменная окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1661965200
    homeworks = []
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response and homeworks != check_response(response):
                homeworks = check_response(response)
                if len(homeworks) > 0:
                    send_message(bot, parse_status(homeworks[0]))
            current_timestamp = response['current_date']
        except exceptions.MassageDontSent as error:
            logging.error(error)
        except exceptions.UrlNotAvailable as error:
            logging.error(error)
        except exceptions.ApiAnswerError as error:
            logging.error(error)
        except TypeError as error:
            logging.error(error)
        except KeyError as error:
            logging.error(error)
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        else:
            time.sleep(RETRY_TIME)




if __name__ == '__main__':
    main()
