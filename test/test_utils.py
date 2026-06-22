import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytz

from src import utils
from src.constants import LOGGER
from src.db.cookie.cookie_record import CookieRecord
from src.env_util import env_util


TAG = "TestUtils"

class TestUtils(unittest.TestCase):
    def test_get_cookies(self):
        cookies = utils.get_cookies()
        self.assertTrue(len(cookies) > 0)
        for cookie in cookies:
            assert cookie.cookieId
            assert cookie.name
            # A cookie's description may legitimately be empty (Crumbl sometimes returns null),
            # so only assert it is a non-None string rather than truthy.
            assert cookie.description is not None
            assert cookie.newAerialImage
            assert cookie.week

    @patch('src.utils.datetime')
    def test_get_previous_week(self, mock_datetime):
        timezone = pytz.timezone("US/Pacific")
        now = datetime(2025, 12, 24, 13, 17, 16, 0, tzinfo=timezone)
        mock_datetime.now.return_value = now
        yesterday = now - timedelta(days=1)
        env_util.DAY_OF_WEEK = yesterday.weekday()
        env_util.TIME = yesterday.strftime("%H:%M")
        env_util.TIMEZONE = timezone

        # get_previous_week() should be the week computed for 7 days before now
        self.assertEqual(utils.get_previous_week(), utils.get_week(now - timedelta(weeks=1)))
        # ...and it should not equal the current week
        self.assertNotEqual(utils.get_previous_week(), utils.get_week())

    @patch('src.utils.get_cookies_url', return_value="https://example.com/cookies.json")
    @patch('src.utils.requests.get')
    def test_fetch_cookies_defaults_null_description_to_empty_string(self, mock_get, _mock_url):
        # Crumbl sometimes returns a rotating menu item with a null description.
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pageProps": {
                "products": {
                    "rotatingMenu": {
                        "items": [
                            {"dessert": {"cookieId": "1", "name": "Has Description", "description": "yum", "newAerialImage": "image-1"}},
                            {"dessert": {"cookieId": "2", "name": "No Description", "description": None, "newAerialImage": "image-2"}},
                        ]
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        _, cookies = utils.fetch_cookies("2025-1")

        self.assertEqual(len(cookies), 2)
        self.assertEqual(cookies[0].description, "yum")
        # The null description should be coalesced to an empty string so it does not violate the NOT NULL constraint.
        self.assertEqual(cookies[1].description, "")

    def test_are_cookies_same(self):
        def cookie(cookie_id, week):
            return CookieRecord(cookie_id, "name", "description", "image", week)

        week_a = [cookie("1", "2025-1"), cookie("2", "2025-1")]
        # Same cookieIds, even across a different week and order, are considered the same lineup
        week_b = [cookie("2", "2025-2"), cookie("1", "2025-2")]
        week_c = [cookie("1", "2025-2"), cookie("3", "2025-2")]

        self.assertTrue(utils.are_cookies_same(week_a, week_b))
        self.assertFalse(utils.are_cookies_same(week_a, week_c))
        self.assertFalse(utils.are_cookies_same(week_a, []))

    @patch('src.utils.datetime')
    def test_get_week_after_day(self, mock_datetime):
        # Setup
        timezone = pytz.timezone("US/Pacific")
        now = datetime(2025, 12, 24, 13, 17, 16, 0, tzinfo=timezone)
        mock_datetime.now.return_value = now
        yesterday = now - timedelta(days=1)
        env_util.DAY_OF_WEEK = yesterday.weekday()
        env_util.TIME = yesterday.strftime("%H:%M")
        env_util.TIMEZONE = timezone

        # Execute
        week = utils.get_week()

        # Verify
        expected_week = "2026-1"
        LOGGER.i(TAG, f"expected_week: {expected_week}; week: {week}")
        assert week == expected_week

        # Unset
        # env_util = original_env_util

    @patch('src.utils.datetime')
    def test_get_week_before_day(self, mock_datetime):
        # Setup
        timezone = pytz.timezone("US/Pacific")
        now = datetime(2025, 12, 24, 13, 17, 16, 0, tzinfo=timezone)
        mock_datetime.now.return_value = now
        tomorrow = now + timedelta(days=1)
        env_util.DAY_OF_WEEK = tomorrow.weekday()
        env_util.TIME = tomorrow.strftime("%H:%M")
        env_util.TIMEZONE = timezone

        # Execute
        week = utils.get_week()

        # Verify
        expected_week = "2025-52"
        LOGGER.i(TAG, f"expected_week: {expected_week}; week: {week}")
        assert week == expected_week

    @patch('src.utils.datetime')
    def test_get_week_after_time(self, mock_datetime):
        # Setup
        timezone = pytz.timezone("US/Pacific")
        now = datetime(2025, 12, 24, 13, 17, 16, 0, tzinfo=timezone)
        mock_datetime.now.return_value = now
        one_hour_ago = now - timedelta(hours=1)
        env_util.DAY_OF_WEEK = one_hour_ago.weekday()
        env_util.TIME = one_hour_ago.strftime("%H:%M")
        env_util.TIMEZONE = timezone

        # Execute
        week = utils.get_week()

        # Verify
        expected_week = "2026-1"
        LOGGER.i(TAG, f"expected_week: {expected_week}; week: {week}")
        assert week == expected_week

    @patch('src.utils.datetime')
    def test_get_week_before_time(self, mock_datetime):
        # Setup
        timezone = pytz.timezone("US/Pacific")
        now = datetime(2025, 12, 24, 13, 17, 16, 0, tzinfo=timezone)
        mock_datetime.now.return_value = now
        one_hour_from_now = now + timedelta(hours=1)
        env_util.DAY_OF_WEEK = one_hour_from_now.weekday()
        env_util.TIME = one_hour_from_now.strftime("%H:%M")
        env_util.TIMEZONE = timezone

        # Execute
        week = utils.get_week()
        # Verify
        expected_week = "2025-52"
        LOGGER.i(TAG, f"expected_week: {expected_week}; week: {week}")
        assert week == expected_week
