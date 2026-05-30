from typing import Optional

from src.constants import LOGGER
from src.db.db_manager import DbManager, db_manager
from src.db.cookie.cookie_record import CookieRecord

# Keeping these here for reference, but don't use them because formatted strings in queries are bad.
# TABLE_NAME = 'cookies'
# COLUMN_COOKIE_ID = 'cookieId'
# COLUMN_NAME = 'name'
# COLUMN_DESCRIPTION = 'description'
# COLUMN_NEW_AERIAL_IMAGE = 'newAerialImage'
# COLUMN_WEEK = 'week'

TAG = "CookieDao"

class CookieDao:
    def __init__(self, db_manager: DbManager):
        self.db_manager = db_manager

    def get_cookies_by_week(self, week: str) -> list[CookieRecord]:
        query = "SELECT cookieId, name, description, newAerialImage, week FROM cookies WHERE week=?"
        params = (week,)
        LOGGER.i(TAG, f"get_cookies_by_week(): executing {query} with params {params}")
        vals = self.db_manager.cursor.execute(query, params).fetchall()
        return [CookieRecord(val[0], val[1], val[2], val[3], val[4]) for val in vals]

    def insert_cookie(self, cookie_record: CookieRecord) -> Optional[CookieRecord]:
        query = "INSERT INTO cookies(cookieId, name, description, newAerialImage, week) VALUES(?, ?, ?, ?, ?) RETURNING *"
        params = (cookie_record.cookieId, cookie_record.name, cookie_record.description, cookie_record.newAerialImage, cookie_record.week)
        LOGGER.i(TAG, f"insert_cookie(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        self.db_manager.connection.commit()
        if val is not None:
            return CookieRecord(val[0], val[1], val[2], val[3], val[4])
        return None

    def insert_cookies(self, cookie_records: list[CookieRecord]) -> list[CookieRecord]:
        return [inserted for inserted in (self.insert_cookie(cookie_record) for cookie_record in cookie_records) if inserted is not None]

    def delete_cookies_by_week(self, week: str) -> list[CookieRecord]:
        query = "DELETE FROM cookies WHERE week=? RETURNING *"
        params = (week,)
        LOGGER.i(TAG, f"delete_cookies_by_week(): executing {query} with params {params}")
        vals = self.db_manager.cursor.execute(query, params).fetchall()
        self.db_manager.connection.commit()
        return [CookieRecord(val[0], val[1], val[2], val[3], val[4]) for val in vals]

cookie_dao = CookieDao(db_manager)
