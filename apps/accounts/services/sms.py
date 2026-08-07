import logging
from typing import Protocol


logger = logging.getLogger('apps.accounts.sms')


class SmsSender(Protocol):
    def send(self, phone: str, message: str) -> None: ...


class ConsoleSmsSender:
    """Default stub until an SMS provider is chosen."""

    def send(self, phone: str, message: str) -> None:
        logger.info('SMS to %s: %s', phone, message)


def get_sms_sender() -> SmsSender:
    return ConsoleSmsSender()
