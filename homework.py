import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

import exceptions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
file_handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5, encoding='windows-1251')
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s'
)
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        logger.info(f'мы начали отправку сообщения {message} в Telegram')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'отправлено сообщение {message}')
        return True
    except telegram.error.TelegramError(
            'При отправке сообщения произошла ошибка') as error:
        logger.error(error)
        return False


def get_api_answer(current_timestamp):
    """делает запрос."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    api_params_dict = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    try:
        logger.info(
            'Начали запрос к API {url}, {headers},{params}'.format(
                **api_params_dict))
        response = requests.get(**api_params_dict)

        if response.status_code != HTTPStatus.OK:
            raise exceptions.UrlNotAvailable(
                f'URL не доступен, {response.status_code}, {response.reason}')
        return response.json()
    except Exception as error:
        raise ConnectionError(
            'При запросе произошла ошибка {error},'
            ' {url}, {headers},{params}'.format(
                error=error,
                **api_params_dict))


def check_response(response):
    """проверяет ответ API на корректность."""
    logger.info('Начали проверку ответа от API ')
    if not isinstance(response, dict):
        raise TypeError('тип ответа от API не словарь')
    if 'homeworks' not in response:
        raise exceptions.ApiAnswerIsEmpty('Нет домашней работы для проверки')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise ValueError('homeworks не список')
    return homeworks


def parse_status(homework):
    """извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError('Нет имени домашки')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Для данного статуса нет вердикта')
    return (
        'Изменился статус проверки работы "{homework_name}".{verdict}'.format(
            homework_name=homework_name,
            verdict=HOMEWORK_VERDICTS[homework_status]
        ))


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = (
        ('practicum', PRACTICUM_TOKEN),
        ('telegram', TELEGRAM_TOKEN),
        ('chat', TELEGRAM_CHAT_ID),
    )
    flag = True
    for token_name, token in tokens:
        if not token:
            logger.critical(f'Нет токена {token_name}')
            flag = False

    return flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise KeyError()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    current_report = {
        'name': '',
        'message': ''
    }
    prev_report = {
        'name': '',
        'message': ''
    }
    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                current_report['name'] = homework['homework_name']
                current_report['message'] = parse_status(homework)
            else:
                current_report['message'] = 'Нет новых статусов'
            if current_report != prev_report:
                if send_message(bot, current_report['message']):
                    prev_report = current_report.copy()
                    current_timestamp = response.get(
                        'current_date', current_timestamp)
            else:
                logger.debug('Нет новых статусов')
        except exceptions.ApiAnswerIsEmpty as error:
            logger.exception(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['message'] = message
            logger.exception(message)
            if current_report != prev_report:
                send_message(bot, str(error))
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
