import os
import unittest

from src.db.job.job_record import JobType, JobState
from src.db.db_manager import DbManager
from src.db.job.job_dao import JobDao
from test import test_constants

class TestJobDao(unittest.TestCase):

    def setUp(self):
        if os.path.exists(test_constants.TEST_DB_PATH):
            os.remove(test_constants.TEST_DB_PATH)
        self.db_manager = DbManager(test_constants.TEST_DB_PATH)
        self.job_dao = JobDao(self.db_manager)

    def tearDown(self):
        self.db_manager.close()
        os.remove(test_constants.TEST_DB_PATH)

    def test_create_job(self):
        job = self.job_dao.create_job(JobType.POST_COOKIES)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)

    def test_get_job_by_id(self):
        job = self.job_dao.create_job(JobType.POST_COOKIES)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)

        job = self.job_dao.get_job_by_id(job.id)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)

    def test_get_oldest_queued_job(self):
        job = self.job_dao.create_job(JobType.POST_COOKIES)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)

        job = self.job_dao.get_oldest_queued_job()
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)
        self.assertEqual(job.state, JobState.QUEUED)

    def test_update_job_state(self):
        job = self.job_dao.create_job(JobType.POST_COOKIES)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)

        job = self.job_dao.update_job_state(job.id, JobState.IN_PROGRESS)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)
        self.assertEqual(job.state, JobState.IN_PROGRESS)

        job = self.job_dao.update_job_state(job.id, JobState.COMPLETED)
        self.assertIsNotNone(job)
        self.assertEqual(job.type, JobType.POST_COOKIES)
        self.assertEqual(job.state, JobState.COMPLETED)


if __name__ == '__main__':
    unittest.main()
