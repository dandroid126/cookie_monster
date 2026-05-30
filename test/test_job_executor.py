import unittest
from unittest.mock import MagicMock, patch

from src.job_executor import JobExecutor
from src.db.cookie.cookie_record import CookieRecord
from src.db.job.job_record import JobState


class FakeCookieDao:
    """A minimal stand-in for CookieDao that returns preconfigured cookies per week."""

    def __init__(self, cookies_by_week):
        self.cookies_by_week = cookies_by_week

    def get_cookies_by_week(self, week):
        return self.cookies_by_week.get(week, [])


def make_executor():
    # Bypass __init__ so we don't spin up a thread / require a running event loop
    executor = JobExecutor.__new__(JobExecutor)
    executor.is_running = True
    executor.healthy = True
    executor.client = MagicMock()
    return executor


def cookie(cookie_id, week):
    return CookieRecord(cookie_id, f"name-{cookie_id}", f"description-{cookie_id}", f"image-{cookie_id}", week)


class TestGetFreshCookies(unittest.TestCase):
    @patch("src.job_executor.utils.get_week", return_value="2025-2")
    def test_returns_cached_cookies(self, _mock_get_week):
        cached = [cookie("a", "2025-2")]
        cookie_dao = FakeCookieDao({"2025-2": cached})
        result = make_executor()._get_fresh_cookies(MagicMock(), cookie_dao)
        self.assertEqual(result, cached)

    @patch("src.job_executor.utils.cache_cookies")
    @patch("src.job_executor.utils.fetch_cookies")
    @patch("src.job_executor.utils.get_previous_week", return_value="2025-1")
    @patch("src.job_executor.utils.get_week", return_value="2025-2")
    def test_fetches_and_caches_when_not_stale(self, _gw, _gpw, mock_fetch, mock_cache):
        previous = [cookie("a", "2025-1")]
        fresh = [cookie("b", "2025-2")]
        mock_fetch.return_value = ("url", fresh)
        cookie_dao = FakeCookieDao({"2025-2": [], "2025-1": previous})

        result = make_executor()._get_fresh_cookies(MagicMock(), cookie_dao)

        self.assertEqual(result, fresh)
        mock_cache.assert_called_once()

    @patch("src.job_executor.STALE_COOKIE_MAX_RETRY_DURATION", 0)
    @patch("src.job_executor.utils.cache_cookies")
    @patch("src.job_executor.utils.fetch_cookies")
    @patch("src.job_executor.utils.get_previous_week", return_value="2025-1")
    @patch("src.job_executor.utils.get_week", return_value="2025-2")
    def test_gives_up_when_stale(self, _gw, _gpw, mock_fetch, mock_cache):
        previous = [cookie("a", "2025-1")]
        # Fetched cookies have the same cookieIds as last week -> Crumbl is still stale
        stale = [cookie("a", "2025-2")]
        mock_fetch.return_value = ("url", stale)
        cookie_dao = FakeCookieDao({"2025-2": [], "2025-1": previous})

        result = make_executor()._get_fresh_cookies(MagicMock(), cookie_dao)

        self.assertIsNone(result)
        mock_cache.assert_not_called()

    @patch("src.job_executor.utils.cache_cookies")
    @patch("src.job_executor.utils.fetch_cookies")
    @patch("src.job_executor.utils.get_previous_week", return_value="2025-1")
    @patch("src.job_executor.utils.get_week", return_value="2025-2")
    def test_posts_when_no_previous_week_data(self, _gw, _gpw, mock_fetch, mock_cache):
        # No previous week cookies stored -> never considered stale
        fresh = [cookie("a", "2025-2")]
        mock_fetch.return_value = ("url", fresh)
        cookie_dao = FakeCookieDao({"2025-2": [], "2025-1": []})

        result = make_executor()._get_fresh_cookies(MagicMock(), cookie_dao)

        self.assertEqual(result, fresh)
        mock_cache.assert_called_once()


class TestPostCookies(unittest.TestCase):
    @patch("src.job_executor.SIGNAL_UTIL")
    def test_gives_up_and_notifies_owners_when_stale(self, mock_signal):
        mock_signal.is_interrupted = False
        executor = make_executor()
        executor._get_fresh_cookies = MagicMock(return_value=None)
        executor._notify_guild_owners = MagicMock()

        state = executor._post_cookies(MagicMock(), MagicMock(), MagicMock(), MagicMock())

        self.assertEqual(state, JobState.COMPLETED)
        executor._notify_guild_owners.assert_called_once()

    @patch("src.job_executor.SIGNAL_UTIL")
    def test_returns_none_when_interrupted(self, mock_signal):
        mock_signal.is_interrupted = True
        executor = make_executor()
        executor._get_fresh_cookies = MagicMock(return_value=None)
        executor._notify_guild_owners = MagicMock()

        state = executor._post_cookies(MagicMock(), MagicMock(), MagicMock(), MagicMock())

        self.assertIsNone(state)
        executor._notify_guild_owners.assert_not_called()

    def test_notifies_bot_manager_and_aborts_on_error(self):
        executor = make_executor()
        executor._get_fresh_cookies = MagicMock(side_effect=RuntimeError("simulated parsing error"))
        executor._notify_bot_manager = MagicMock()

        state = executor._post_cookies(MagicMock(), MagicMock(), MagicMock(), MagicMock())

        self.assertEqual(state, JobState.ABORTED)
        self.assertFalse(executor.healthy)
        executor._notify_bot_manager.assert_called_once()

    def test_completes_on_success(self):
        executor = make_executor()
        executor._get_fresh_cookies = MagicMock(return_value=[cookie("a", "2025-2")])
        gca_dao = MagicMock()
        gca_dao.get_all_guild_channel_associations.return_value = []

        state = executor._post_cookies(MagicMock(), MagicMock(), MagicMock(), gca_dao)

        self.assertEqual(state, JobState.COMPLETED)


if __name__ == "__main__":
    unittest.main()
