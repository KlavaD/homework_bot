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

RETRY_TIME = 5
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
        logger.info('мы начали отправку сообщения в Telegram')
        bot.send_message(TELEGRAM_CHAT_ID, message)
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
            'При запросе произошла ошибка {url}, {headers},{params}'.format(
                **api_params_dict))


def check_response(response):
    """проверяет ответ API на корректность."""
    logger.info('Начали проверку ответа от API ')
    if not isinstance(response, dict):
        raise TypeError('тип ответа от API не словарь')
    if len(response['homeworks']) == 0:
        raise exceptions.ApiAnswerIsEmpty('Нет домашней работы для проверки')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не список')
    return homeworks


def parse_status(homework):
    """извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError('Нет имени домашки')
    homework_status = homework.get('status')
    if not HOMEWORK_VERDICTS[homework_status]:
        raise ValueError('Для данного статуса нет вердикта')
    return 'Изменился статус проверки работы "{homework_name}".{verdict}'.format(
        homework_name=homework_name, verdict=HOMEWORK_VERDICTS[homework_status])


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = (
        ('practicum', PRACTICUM_TOKEN),
        ('telegram', TELEGRAM_TOKEN),
        ('chat', TELEGRAM_CHAT_ID),
    )
    flag = True
    for token_name, token in tokens:
        if token is None or len(str(token)) == 0:
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
        'message': '',
        'error': ''
    }
    prev_report = {
        'name': '',
        'message': '',
        'error': ''
    }
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) > 0:
                verdict = parse_status(homeworks[0])
                current_report['name'] = homeworks[0]['homework_name']
                current_report['message'] = verdict
                if current_report != prev_report:
                    if send_message(bot, verdict):
                        prev_report = current_report.copy()
                current_timestamp = response.get('current_date')
            else:
                logger.debug('Нет новых статусов')

        except exceptions.ApiAnswerIsEmpty as error:
            current_report['error'] = str(error)
            if current_report != prev_report:
                if send_message(bot, str(error)):
                    prev_report = current_report.copy()
            logger.error(error)

        except Exception as error:
            current_report['error'] = str(error)
            if current_report != prev_report:
                if send_message(bot, str(error)):
                    prev_report = current_report.copy()
            logger.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
