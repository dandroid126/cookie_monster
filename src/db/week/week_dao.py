import json

from src.constants import LOGGER
from src.db.db_manager import db_manager
from src.db.week.week_record import WeekRecord

TAG = "WeekDao"

class WeekDao:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_week_record_by_week(self, week: str):
        query = "SELECT * FROM week WHERE week=?"
        params = (week,)
        LOGGER.i(TAG, f"get_week_record_by_week(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        if val is not None:
            return WeekRecord(val[0], val[1], json.loads(val[2]))
        return None

    def insert_or_update_week_record(self, week_record: WeekRecord):
        query = "INSERT OR REPLACE INTO week(week, url, cookies) VALUES(?, ?, ?) RETURNING *"
        params = (week_record.week, week_record.url, json.dumps(week_record.cookies))
        LOGGER.i(TAG, f"insert_or_update_week_record(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        self.db_manager.connection.commit()
        if val is not None:
            return WeekRecord(val[0], val[1], json.loads(val[2]))
        return None

week_dao = WeekDao(db_manager)
