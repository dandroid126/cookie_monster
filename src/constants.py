import os
from typing import Final

from dandroid126_utils.logger import Logger
from dandroid126_utils.signal_util import SignalUtil

APP_NAME = "cookie_monster"
SCRIPT_PATH: Final = os.path.realpath(__file__)
DIR_PATH: Final = f"{os.path.dirname(SCRIPT_PATH)}/../"
OUT_PATH: Final = f"{DIR_PATH}/out/"
LOGGER: Final = Logger(APP_NAME, OUT_PATH)
SIGNAL_UTIL: Final = SignalUtil(LOGGER, 1)
DB_PATH: Final = f"{OUT_PATH}/{APP_NAME}.db"
