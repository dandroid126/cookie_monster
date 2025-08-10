from src.constants import LOGGER


class LoggedRuntimeError(Exception):
    def __init__(self, tag, message):
        self.message = message
        LOGGER.e(tag, self.message)
