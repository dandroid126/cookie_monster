import os
from typing import Final

from logger import Logger

SCRIPT_PATH: Final = os.path.realpath(__file__)
DIR_PATH: Final = f"{os.path.dirname(SCRIPT_PATH)}/../"
OUT_PATH: Final = f"{DIR_PATH}/out/"
LOGGER: Final = Logger(OUT_PATH)
DB_PATH: Final = f"{OUT_PATH}/cookie_monster.db"
