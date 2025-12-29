import os
from typing import Optional

import pytz
from dotenv import load_dotenv

from src.day_of_week import DayOfWeek
from src.errors import LoggedRuntimeError
from src.constants import LOGGER

TAG = "EnvUtil"

class EnvUtil:
    DEFAULT_TIMEZONE = "US/Pacific"
    _DISCORD_TOKEN = "DISCORD_TOKEN"
    _DAY_OF_WEEK = "DAY_OF_WEEK"
    _TIME = "TIME"
    _TIMEZONE = "TIMEZONE"

    _ENVIRONMENT_VARIABLE_NAMES = [_DISCORD_TOKEN, _DAY_OF_WEEK, _TIME, _TIMEZONE]

    def __init__(self, dotenv_path: Optional[str] = None):
        for environment_variable_name in self._ENVIRONMENT_VARIABLE_NAMES:
            if os.environ.get(environment_variable_name):
                del os.environ[environment_variable_name]
        load_dotenv(dotenv_path=dotenv_path)
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        self.DAY_OF_WEEK = os.getenv('DAY_OF_WEEK')
        self.TIME = os.getenv('TIME')
        self.TIMEZONE = os.getenv('TIMEZONE')

        if self.TOKEN is None:
            raise LoggedRuntimeError(TAG, "TOKEN not found. Check that .env file exists in src dir and that its contents are correct")
        if self.DAY_OF_WEEK is None:
            LOGGER.e(TAG, "DAY_OF_WEEK not found. Using default value of 6 (Sunday)")
            self.DAY_OF_WEEK = 6
        else:
            self.DAY_OF_WEEK = int(self.DAY_OF_WEEK)
            assert type(DayOfWeek(self.DAY_OF_WEEK)) == DayOfWeek
        if self.TIME is None:
            LOGGER.e(TAG, "TIME not found. Using default value of 17:00")
            self.TIME = "17:00"
        if self.TIMEZONE is None:
            LOGGER.e(TAG, f"TIMEZONE not found. Using default value of {self.DEFAULT_TIMEZONE}")
            self.TIMEZONE = pytz.timezone(self.DEFAULT_TIMEZONE)
        else:
            self.TIMEZONE = pytz.timezone(self.TIMEZONE)

env_util = EnvUtil()
