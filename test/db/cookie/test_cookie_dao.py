import os
import unittest

from src import utils
from src.db.cookie.cookie_dao import CookieDao
from src.db.cookie.cookie_record import CookieRecord
from src.db.db_manager import DbManager
from test import test_constants


class TestCookieDao(unittest.TestCase):
    def setUp(self):
        if os.path.exists(test_constants.TEST_DB_PATH):
            os.remove(test_constants.TEST_DB_PATH)
        self.db_manager = DbManager(test_constants.TEST_DB_PATH)
        self.cookie_dao = CookieDao(self.db_manager)

    def tearDown(self):
        self.db_manager.close()
        os.remove(test_constants.TEST_DB_PATH)

    def _make_cookie(self, cookie_id: str, week: str) -> CookieRecord:
        return CookieRecord(cookie_id, f"name-{cookie_id}", f"description-{cookie_id}", f"image-{cookie_id}", week)

    def test_insert_and_get_cookies_by_week(self):
        week = utils.get_week()
        cookie = self._make_cookie("cookie-1", week)
        self.cookie_dao.insert_cookie(cookie)
        cookies = self.cookie_dao.get_cookies_by_week(week)
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies[0], cookie)

    def test_get_cookies_by_week_empty(self):
        self.assertEqual(self.cookie_dao.get_cookies_by_week(utils.get_week()), [])

    def test_insert_cookies(self):
        week = utils.get_week()
        cookies = [self._make_cookie("cookie-1", week), self._make_cookie("cookie-2", week)]
        self.cookie_dao.insert_cookies(cookies)
        self.assertEqual(self.cookie_dao.get_cookies_by_week(week), cookies)

    def test_cookie_can_belong_to_multiple_weeks(self):
        cookie_week_1 = self._make_cookie("shared-cookie", "2025-1")
        cookie_week_2 = self._make_cookie("shared-cookie", "2025-2")
        self.cookie_dao.insert_cookies([cookie_week_1, cookie_week_2])
        self.assertEqual(self.cookie_dao.get_cookies_by_week("2025-1"), [cookie_week_1])
        self.assertEqual(self.cookie_dao.get_cookies_by_week("2025-2"), [cookie_week_2])

    def test_delete_cookies_by_week(self):
        self.cookie_dao.insert_cookies([self._make_cookie("cookie-1", "2025-1"), self._make_cookie("cookie-2", "2025-1")])
        self.cookie_dao.insert_cookie(self._make_cookie("cookie-3", "2025-2"))
        deleted = self.cookie_dao.delete_cookies_by_week("2025-1")
        self.assertEqual(len(deleted), 2)
        self.assertEqual(self.cookie_dao.get_cookies_by_week("2025-1"), [])
        self.assertEqual(len(self.cookie_dao.get_cookies_by_week("2025-2")), 1)

if __name__ == '__main__':
    unittest.main()
