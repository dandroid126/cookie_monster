import json
import sys
from datetime import datetime, timedelta
from typing import Final, Optional

import requests
from bs4 import BeautifulSoup

from src.constants import LOGGER
from src.db.cookie.cookie_dao import CookieDao, cookie_dao
from src.db.cookie.cookie_record import CookieRecord
from src.db.job.job_dao import job_dao
from src.db.job.job_record import JobRecord, JobType
from src.db.week.week_dao import WeekDao, week_dao
from src.db.week.week_record import WeekRecord
from src.env_util import env_util

TAG = "Utils"

_BASE_URL: Final = "https://crumblcookies.com/"
_BUILD_ID_REPLACE: Final = "{{build_id}}"
_URL: Final = f"https://crumblcookies.com/_next/data/{_BUILD_ID_REPLACE}/en-US.json"
_URL_SCRIPT_ID: Final = "__NEXT_DATA__"
_BUILD_ID: Final = "buildId"

def get_week(now: Optional[datetime] = None) -> str:
    """
    Get the week string for the given moment (defaults to now).

    Args:
        now: The moment to compute the week for. If None, the current time is used.

    Returns:
        str: The week
    """

    # We are using this to cache the cookies by week.

    time = env_util.TIME.split(":")
    now = now if now is not None else datetime.now(env_util.TIMEZONE)
    reset_time = now.replace(hour=int(time[0]), minute=int(time[1]), second=0, microsecond=0)
    weekday = now.weekday()
    time = now.time()
    LOGGER.i(TAG, f"Current weekday: {weekday}, time: {time}")
    isocalendar = now.isocalendar()

    # If the current time is after the time specified in the environment file, then use next week's week number
    week_number = now.isocalendar()[1] - 1 if weekday < env_util.DAY_OF_WEEK or (weekday == env_util.DAY_OF_WEEK and now.time() < reset_time.time()) else now.isocalendar()[1]

    # make sure we aren't going over 52 weeks.
    carry_out = week_number // 52
    week_number = (week_number % 52) + 1
    LOGGER.i(TAG, f"week number: {week_number}")
    return f"{isocalendar[0] + carry_out}-{week_number}"


def get_previous_week() -> str:
    """
    Get the week string for the week before the current one.

    Returns:
        str: The previous week
    """
    return get_week(datetime.now(env_util.TIMEZONE) - timedelta(weeks=1))


def get_cookies_url() -> str:
    """
    Get the url for the cookies

    Returns:
        str: The url for the cookies
    """

    r = requests.get(_BASE_URL)
    soup = BeautifulSoup(r.text, "html.parser")
    next_data = soup.find(id=_URL_SCRIPT_ID, type="application/json")
    build_id = json.loads(str(next_data.contents[0]))[_BUILD_ID]
    return _URL.replace(_BUILD_ID_REPLACE, build_id)


def fetch_cookies(week: str) -> tuple[str, list[CookieRecord]]:
    """
    Fetch the current cookies from the website without caching them.

    Args:
        week: The week to associate the fetched cookies with

    Returns:
        tuple[str, list[CookieRecord]]: The url the cookies were fetched from and the cookie details
    """
    url = get_cookies_url()
    r = requests.get(url)
    items = r.json()["pageProps"]["products"]["rotatingMenu"]["items"]
    cookies = [
        CookieRecord(dessert["cookieId"], dessert["name"], dessert["description"] or "", dessert["newAerialImage"], week)
        for dessert in (item["dessert"] for item in items)
    ]
    return url, cookies


def cache_cookies(week: str, url: str, cookies: list[CookieRecord], week_dao: WeekDao = week_dao, cookie_dao: CookieDao = cookie_dao) -> None:
    """
    Cache the cookies for the week.

    Args:
        week: The week the cookies belong to
        url: The url the cookies were fetched from
        cookies: The cookies to cache
        week_dao: The week dao. If none is provided, the default singleton will be used
        cookie_dao: The cookie dao. If none is provided, the default singleton will be used
    """
    week_dao.insert_or_update_week_record(WeekRecord(week, url))
    cookie_dao.insert_cookies(cookies)


def are_cookies_same(cookies: list[CookieRecord], other_cookies: list[CookieRecord]) -> bool:
    """
    Determine whether two sets of cookies represent the same lineup, compared by cookieId.

    Returns:
        bool: True if both lists contain exactly the same cookieIds, False otherwise
    """
    return {cookie.cookieId for cookie in cookies} == {cookie.cookieId for cookie in other_cookies}


def get_cookies(week_dao: WeekDao = week_dao, cookie_dao: CookieDao = cookie_dao) -> list[CookieRecord]:
    """
    Get the cookies for the week

    Args:
        week_dao: The week dao. If none is provided, the default singleton will be used
        cookie_dao: The cookie dao. If none is provided, the default singleton will be used

    Returns:
        list[CookieRecord]: The cookie details
    """

    week = get_week()
    cookies = cookie_dao.get_cookies_by_week(week)
    if not cookies:
        LOGGER.i(TAG, "Fetching cookies from website")
        url, cookies = fetch_cookies(week)
        cache_cookies(week, url, cookies, week_dao, cookie_dao)
    else:
        LOGGER.i(TAG, "Using cached cookies")
    return cookies


def create_post_cookies_job() -> JobRecord:
    """
    Create a job to post the cookies

    Returns:
        JobRecord: The job
    """
    incomplete_post_cookie_jobs = job_dao.get_incomplete_jobs_by_type(JobType.POST_COOKIES)
    if len(incomplete_post_cookie_jobs) > 0:
        LOGGER.w(TAG, f"Job already exists: {len(incomplete_post_cookie_jobs)}")
        return incomplete_post_cookie_jobs[0]
    return job_dao.create_job(JobType.POST_COOKIES)

def clear_cache() -> bool:
    week = get_week()
    deleted_cookies = cookie_dao.delete_cookies_by_week(week)
    deleted_week = week_dao.delete_week_record_by_week(week)
    if deleted_cookies:
        LOGGER.w(TAG, f"{len(deleted_cookies)} cookies and {deleted_week} were deleted")
        return True
    return False

if __name__ == "__main__":
    # If this script is run as main, then it will create a job
    if len(sys.argv) < 2:
        LOGGER.e(TAG, "Usage: python utils.py <command>")
        exit(1)
    if sys.argv[1] == "post_cookies":
        create_post_cookies_job()
    else:
        LOGGER.e(TAG, "Unknown command")
        exit(1)
