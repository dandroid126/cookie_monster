import os
import unittest

from src.db.week.week_record import WeekRecord
from src import utils
from src.db.db_manager import DbManager
from src.db.week.week_dao import WeekDao
from test import test_constants


class TestWeekDao(unittest.TestCase):
    def setUp(self):
        if os.path.exists(test_constants.TEST_DB_PATH):
            os.remove(test_constants.TEST_DB_PATH)
        self.db_manager = DbManager(test_constants.TEST_DB_PATH)
        self.week_dao = WeekDao(self.db_manager)

    def tearDown(self):
        self.db_manager.close()
        os.remove(test_constants.TEST_DB_PATH)

    def test_get_week_record_by_week(self):
        week = utils.get_week()
        url = "url"
        cookies = [{"key1": "value1"}, {"key2": "value2"}]
        week_record = WeekRecord(week, url, cookies)
        self.week_dao.insert_or_update_week_record(week_record)
        week_record = self.week_dao.get_week_record_by_week(week)
        self.assertIsNotNone(week_record)
        self.assertEqual(week_record.week, week)
        self.assertEqual(week_record.url, url)
        self.assertEqual(week_record.cookies, cookies)

if __name__ == '__main__':
    unittest.main()
