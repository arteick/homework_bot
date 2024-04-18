import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (APIKeysException, EndpointStatusException,
                        EnvVariableException, InvalidStatusException)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('bot_logs.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    try:
        for var in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
            if not var:
                raise EnvVariableException(
                    'Проверьте переменные окружения: '
                    'PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID'
                )
    except EnvVariableException as error:
        logger.critical(
            f'Сбой в работе программы: {error}. '
            f'Работа программы принудительно остановлена.'
        )
        sys.exit()


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено')
    except telegram.error.TelegramError as error:
        logger.error(
            f'Ошибка при отправке сообщения: '
            f'{error}'
        )


def get_api_answer(timestamp: int):
    """Делает запрос к API сервиса Практикум.Домашка."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp})
        if response.status_code != HTTPStatus.OK:
            raise EndpointStatusException(
                'Код ответа API не соответствует ожидаемому. '
                f'{response.status_code}'
            )
        return response.json()
    except requests.RequestException as error:
        message = (
            f'Ошибка обработки запроса: {error}'
        )
        logger.error(message)


def check_response(response):
    """Проверяет ответ API на наличие ожидаемых ключей."""
    if type(response) is not dict:
        raise TypeError(
            f'Тип данных ответа API не соответствует ожидаемому. '
            f'{type(response)}'
        )

    if not response.get('homeworks') and response.get('homeworks') != []:
        raise APIKeysException(
            'В ответе API отсутствует ключ - homeworks'
        )

    elif response.get('homeworks') == []:
        raise IndexError(
            'Ошибка при извлечении последнего домашнего задания. '
            'Возможно, бот только что был запущен.'
        )

    homework_type = type(response.get('homeworks'))
    if homework_type is not list:
        raise TypeError(
            f'Тип данных под ключом homeworks не соответствует ожидаемому. '
            f'{homework_type}'
        )


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise APIKeysException(
            'В ответе API отсутвует ключ homework_name'
        )
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        raise InvalidStatusException(
            f'В ответе API был получен неожиданный статус '
            f'проверки д/з {status}'
        )

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    prev_hw_status = None

    while True:
        try:

            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')[0]
            if prev_hw_status != (
                homework.get('status'), homework.get('homework_name')
            ):
                bot_message = parse_status(homework)
                prev_hw_status = (
                    homework.get('status'), homework.get('homework_name')
                )
                send_message(bot, bot_message)

        except EndpointStatusException as error:
            logger.error(error)
        except APIKeysException as error:
            logger.error(error)
        except TypeError as error:
            logger.error(error)
        except InvalidStatusException as error:
            logger.error(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.critical(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
