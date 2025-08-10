import asyncio
import threading

from discord import Client

from src import constants
from src import utils
from src.constants import LOGGER
from src.db.db_manager import DbManager
from src.db.guild_channel_association.guild_channel_association_dao import GuildChannelAssociationDao
from src.db.job.job_dao import JobDao
from src.db.job.job_record import JobState, JobType
from src.db.week.week_dao import WeekDao
from src.signal_util import signal_util

TAG = "JobExecutor"
SLEEP_DELAY = 60 # One minute
# TODO: Delete this. This is for testing.
# SLEEP_DELAY = 5 # One minute

class JobExecutor:
    def __init__(self, client: Client):
        self.is_running = False
        self.client = client
        self.start()

    def start(self):
        self.is_running = True
        loop = asyncio.get_running_loop()
        thread = threading.Thread(target=self._loop, args=(loop, ))
        thread.start()

    def stop(self):
        self.is_running = False

    def _loop(self, loop):
        db_manager = DbManager(constants.DB_PATH)
        job_dao = JobDao(db_manager)
        week_dao = WeekDao(db_manager)
        guild_channel_association_dao = GuildChannelAssociationDao(db_manager)
        JobExecutor.clean_up_in_progress_jobs(job_dao)
        while not signal_util.is_interrupted and self.is_running:
            LOGGER.d(TAG, "job_executor is processing jobs...")
            job = job_dao.get_oldest_queued_job()
            while job is not None:
                LOGGER.d(TAG, f"job_executor is processing job: {job.type}")
                job_dao.update_job_state(job.id, JobState.IN_PROGRESS)
                # TODO: Each job should be its own class that knows how to execute.
                # Have a parent class with an execute method. Each job type should be a child class.
                if job.type == JobType.POST_COOKIES:
                    cookies = utils.get_cookies(week_dao)
                    guild_channel_associations = guild_channel_association_dao.get_all_guild_channel_associations()
                    for guild_channel_association in guild_channel_associations:
                        channel = self.client.get_channel(guild_channel_association.channel_id)
                        for cookie in cookies:
                            message = f'{cookie["name"].strip()} - {cookie["description"].strip()}\n{cookie["newAerialImage"].strip()}\n\n'
                            asyncio.run_coroutine_threadsafe(channel.send(message), loop).result()
                job_dao.update_job_state(job.id, JobState.COMPLETED)
                job = job_dao.get_oldest_queued_job()
            LOGGER.d(TAG, "No jobs to process")
            signal_util.wait(SLEEP_DELAY)
        self.stop()
        LOGGER.i(TAG, "JobExecutor stopped")

    @staticmethod
    def clean_up_in_progress_jobs(job_dao: JobDao):
        jobs = job_dao.get_all_in_progress_jobs()
        for job in jobs:
            job_dao.update_job_state(job.id, JobState.ABORTED)