import json
import sys
from datetime import datetime, timezone
from typing import Final

import requests
from bs4 import BeautifulSoup

from src.constants import LOGGER
from src.db.job.job_dao import job_dao
from src.db.job.job_record import JobRecord, JobType
from src.db.week.week_dao import WeekDao, week_dao
from src.db.week.week_record import WeekRecord

TAG = "Utils"

_BASE_URL: Final = "https://crumblcookies.com/"
_BUILD_ID_REPLACE: Final = "{{build_id}}"
_URL: Final = f"https://crumblcookies.com/_next/data/{_BUILD_ID_REPLACE}/en-US.json"
_URL_SCRIPT_ID: Final = "__NEXT_DATA__"
_BUILD_ID: Final = "buildId"

def get_week() -> str:
    """
    Get the current week

    Returns:
        str: The current week
    """

    # We are using this to cache the cookies by week.
    # Cookies are posted every Monday at midnight UTC.
    # Coincidentally, Monday is the first day of the week when using %W, so we don't need to anything.
    return datetime.now(timezone.utc).strftime("%Y-%W")


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


def get_cookies(week_dao: WeekDao = week_dao) -> list[dict[str, str]]:
    """
    Get the cookies for the week

    Args: week_dao: The week dao. If none is provided, the default singleton will be used

    Returns:
        list[dict[str, str]]: The cookie details
    """

    week = get_week()
    week_record = week_dao.get_week_record_by_week(week)
    if week_record is None:
        LOGGER.i(TAG, "Fetching cookies from website")
        url = get_cookies_url()
        r = requests.get(url)
        cookies = r.json()["pageProps"]["products"]["cookies"]
        week_record = WeekRecord(week, url, cookies)
        week_dao.insert_or_update_week_record(week_record)
    else:
        LOGGER.i(TAG, "Using cached cookies")
        cookies = week_record.cookies
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
    deleted_week = week_dao.delete_week_record_by_week(week)
    if deleted_week is not None:
        LOGGER.w(TAG, f"{deleted_week} was deleted")
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
