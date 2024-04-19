class EndpointStatusException(Exception):
    """Ошибка обращения к эндпоинту."""

    pass


class InvalidStatusException(Exception):
    """Некорректный статус проверки домашнего задания."""

    pass


class APIKeysException(Exception):
    """В ответе API отсутсвует ожидаемый ключ."""

    pass
