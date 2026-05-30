import asyncio
import threading
import time
from typing import Optional

from discord import Client

from src import constants
from src import utils
from src.constants import LOGGER
from src.constants import SIGNAL_UTIL
from src.db.cookie.cookie_dao import CookieDao
from src.db.cookie.cookie_record import CookieRecord
from src.db.db_manager import DbManager
from src.db.guild_channel_association.guild_channel_association_dao import GuildChannelAssociationDao
from src.db.job.job_dao import JobDao
from src.db.job.job_record import JobState, JobType
from src.db.week.week_dao import WeekDao
from src.env_util import env_util

TAG = "JobExecutor"
SLEEP_DELAY = 60 # One minute

# How long to wait between attempts when Crumbl is still showing last week's cookies
STALE_COOKIE_RETRY_DELAY = 5 * 60  # Five minutes
# How long to keep retrying before giving up when Crumbl is still showing last week's cookies
STALE_COOKIE_MAX_RETRY_DURATION = 2 * 60 * 60  # Two hours

STALE_COOKIE_MESSAGE = "This week's cookies were not posted because Crumbl is still showing last week's cookies. They appear to be running late updating their menu."

class JobExecutor:
    def __init__(self, client: Client):
        self.is_running = False
        self.healthy = True
        self.client = client
        self.start()

    def start(self):
        """
        Start the job executor
        """
        self.is_running = True
        loop = asyncio.get_running_loop()
        thread = threading.Thread(target=self._loop, args=(loop, ))
        thread.start()

    def stop(self):
        """
        Stop the job executor
        """
        self.is_running = False

    def _loop(self, loop):
        """
        Main loop for the job executor

        Args:
            loop: The asyncio event loop
        """
        db_manager = DbManager(constants.DB_PATH)
        job_dao = JobDao(db_manager)
        week_dao = WeekDao(db_manager)
        cookie_dao = CookieDao(db_manager)
        guild_channel_association_dao = GuildChannelAssociationDao(db_manager)
        JobExecutor.clean_up_in_progress_jobs(job_dao)
        while not SIGNAL_UTIL.is_interrupted and self.is_running:
            LOGGER.d(TAG, "job_executor is processing jobs...")
            job = job_dao.get_oldest_queued_job()
            while job is not None:
                LOGGER.d(TAG, f"job_executor is processing job: {job.type}")
                job_dao.update_job_state(job.id, JobState.IN_PROGRESS)
                # TODO: Each job should be its own class that knows how to execute.
                # Have a parent class with an execute method. Each job type should be a child class.
                if job.type == JobType.POST_COOKIES:
                    result_state = self._post_cookies(loop, week_dao, cookie_dao, guild_channel_association_dao)
                    if result_state is None:
                        # We were interrupted (shutting down) before we could finish.
                        # Leave the job in progress so it gets cleaned up and retried on the next run.
                        break
                    job_dao.update_job_state(job.id, result_state)
                else:
                    job_dao.update_job_state(job.id, JobState.COMPLETED)
                job = job_dao.get_oldest_queued_job()
            LOGGER.d(TAG, "No jobs to process")
            SIGNAL_UTIL.wait(SLEEP_DELAY)
        self.stop()
        LOGGER.i(TAG, "JobExecutor stopped")

    def _post_cookies(self, loop, week_dao: WeekDao, cookie_dao: CookieDao, guild_channel_association_dao: GuildChannelAssociationDao) -> Optional[JobState]:
        """
        Execute a POST_COOKIES job: resolve this week's cookies (waiting out a late Crumbl
        update if necessary) and post them to every associated channel.

        Args:
            loop: The asyncio event loop the discord client is running on
            week_dao: The week dao
            cookie_dao: The cookie dao
            guild_channel_association_dao: The guild channel association dao

        Returns:
            The resulting JobState (COMPLETED on success or stale give-up, ABORTED on error),
            or None if the executor was interrupted before it could finish (so the job should
            be left in progress).
        """
        try:
            cookies = self._get_fresh_cookies(week_dao, cookie_dao)
            if cookies is None:
                if SIGNAL_UTIL.is_interrupted or not self.is_running:
                    return None
                # We gave up because Crumbl is still showing last week's cookies.
                LOGGER.w(TAG, "Giving up on posting cookies: Crumbl is still showing last week's cookies")
                self._notify_guild_owners(loop, STALE_COOKIE_MESSAGE)
                return JobState.COMPLETED
            guild_channel_associations = guild_channel_association_dao.get_all_guild_channel_associations()
            for guild_channel_association in guild_channel_associations:
                channel = self.client.get_channel(guild_channel_association.channel_id)
                for cookie in cookies:
                    message = f'{cookie.name.strip()} - {cookie.description.strip()}\n{cookie.newAerialImage.strip()}\n\n'
                    asyncio.run_coroutine_threadsafe(channel.send(message), loop).result()
            return JobState.COMPLETED
        except Exception as e:
            LOGGER.e(TAG, f"Failed to post cookies: {e}")
            self.healthy = False
            self._notify_bot_manager(loop, e)
            return JobState.ABORTED

    def _get_fresh_cookies(self, week_dao: WeekDao, cookie_dao: CookieDao) -> Optional[list[CookieRecord]]:
        """
        Resolve the cookies to post for the current week.

        If the cookies are already cached for the week, they are returned directly. Otherwise
        the cookies are fetched from Crumbl. Crumbl is sometimes late updating their menu (they
        are supposed to update 10 minutes before the cron job runs, but can be up to 30 minutes
        late), so if the freshly fetched cookies are identical to last week's, we wait and retry
        for up to STALE_COOKIE_MAX_RETRY_DURATION before giving up.

        Args:
            week_dao: The week dao
            cookie_dao: The cookie dao

        Returns:
            The cookies to post, or None if we gave up because Crumbl is still showing last
            week's cookies, or because the executor was interrupted while waiting.
        """
        week = utils.get_week()
        cached_cookies = cookie_dao.get_cookies_by_week(week)
        if cached_cookies:
            LOGGER.i(TAG, "Using cached cookies")
            return cached_cookies

        previous_cookies = cookie_dao.get_cookies_by_week(utils.get_previous_week())
        deadline = time.monotonic() + STALE_COOKIE_MAX_RETRY_DURATION
        while not SIGNAL_UTIL.is_interrupted and self.is_running:
            url, cookies = utils.fetch_cookies(week)
            if not (previous_cookies and utils.are_cookies_same(cookies, previous_cookies)):
                utils.cache_cookies(week, url, cookies, week_dao, cookie_dao)
                return cookies
            if time.monotonic() >= deadline:
                return None
            LOGGER.w(TAG, f"Crumbl is still showing last week's cookies. Retrying in {STALE_COOKIE_RETRY_DELAY} seconds.")
            SIGNAL_UTIL.wait(STALE_COOKIE_RETRY_DELAY)
        return None

    def _notify_guild_owners(self, loop, message: str):
        """
        Send a direct message to the owner of every guild the bot is in.

        Args:
            loop: The asyncio event loop the discord client is running on
            message: The message to send
        """
        try:
            asyncio.run_coroutine_threadsafe(self._send_message_to_guild_owners(message), loop).result()
        except Exception as e:
            LOGGER.e(TAG, f"Failed to notify guild owners: {e}")

    async def _send_message_to_guild_owners(self, message: str):
        for guild in self.client.guilds:
            try:
                owner = guild.owner or await self.client.fetch_user(guild.owner_id)
                if owner is not None:
                    await owner.send(message)
            except Exception as e:
                LOGGER.e(TAG, f"Failed to notify owner of guild {guild}: {e}")

    def _notify_bot_manager(self, loop, error: Exception):
        """
        Direct message the bot manager that an error on our end prevented cookies from being posted.

        Args:
            loop: The asyncio event loop the discord client is running on
            error: The error that prevented the cookies from being posted
        """
        if env_util.BOT_MANAGER_USER_ID is None:
            LOGGER.w(TAG, "BOT_MANAGER_USER_ID is not set; cannot notify the bot manager")
            return
        message = f"Cookies were not posted because of an error on the bot's end: {error}"
        try:
            asyncio.run_coroutine_threadsafe(self._send_message_to_bot_manager(message), loop).result()
        except Exception as e:
            LOGGER.e(TAG, f"Failed to notify bot manager: {e}")

    async def _send_message_to_bot_manager(self, message: str):
        user = await self.client.fetch_user(env_util.BOT_MANAGER_USER_ID)
        if user is not None:
            await user.send(message)

    @staticmethod
    def clean_up_in_progress_jobs(job_dao: JobDao):
        """
        Clean up in progress jobs

        Args:
            job_dao: The job dao
        """
        jobs = job_dao.get_all_in_progress_jobs()
        for job in jobs:
            job_dao.update_job_state(job.id, JobState.ABORTED)