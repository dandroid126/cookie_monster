from datetime import datetime
from typing import Optional

from dateutil import parser

from src.constants import LOGGER
from src.db.db_manager import DbManager, db_manager
from src.db.job.job_record import JobRecord, JobState, JobType

# Keeping these here for reference, but don't use them because formatted strings in queries are bad.
# TABLE_NAME = 'job'
# COLUMN_ID = 'id'
# COLUMN_TYPE = 'type'
# COLUMN_CREATED_AT = 'created_at'
# COLUMN_STATE = 'state'

TAG = "JobDao"

class JobDao:
    def __init__(self, db_manager: DbManager):
        self.db_manager = db_manager

    def create_job(self, job_type: JobType) -> Optional[JobRecord]:
        query = "INSERT INTO job(type, created_at, state) VALUES(?, ?, ?) RETURNING *"
        job_created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (job_type.value, job_created_at, JobState.QUEUED.value)
        LOGGER.i(TAG, f"insert_or_update_job(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        self.db_manager.connection.commit()
        if val is not None:
            return JobRecord(int(val[0]), JobType(val[1]), parser.parse(val[2]), JobState(val[3]))
        return None

    def get_job_by_id(self, job_id: int) -> Optional[JobRecord]:
        query = "SELECT * FROM job WHERE id=?"
        params = (job_id,)
        LOGGER.i(TAG, f"get_job_by_id(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        if val is not None:
            return JobRecord(int(val[0]), JobType(val[1]), parser.parse(val[2]), JobState(val[3]))
        return None

    def get_incomplete_jobs_by_type(self, job_type: JobType) -> list[JobRecord]:
        query = "SELECT * FROM job WHERE type=? AND state IN (?, ?) ORDER BY created_at ASC"
        params = (job_type.value, JobState.QUEUED.value, JobState.IN_PROGRESS.value)
        LOGGER.i(TAG, f"get_jobs_by_type(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchall()
        return [JobRecord(int(val[0]), JobType(val[1]), parser.parse(val[2]), JobState(val[3])) for val in val]

    def get_all_in_progress_jobs(self) -> list[JobRecord]:
        query = "SELECT * FROM job WHERE state=? ORDER BY created_at ASC"
        params = (JobState.IN_PROGRESS.value,)
        LOGGER.i(TAG, f"get_jobs_by_type(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchall()
        return [JobRecord(int(val[0]), JobType(val[1]), parser.parse(val[2]), JobState(val[3])) for val in val]

    def get_oldest_queued_job(self) -> Optional[JobRecord]:
        query = "SELECT * FROM job WHERE state=? ORDER BY created_at ASC LIMIT 1"
        params = (JobState.QUEUED.value,)
        LOGGER.i(TAG, f"get_oldest_queued_job(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        if val is not None:
            return JobRecord(int(val[0]), JobType(val[1]), parser.parse(val[2]), JobState(val[3]))
        return None

    def update_job_state(self, job_id: int, job_state: JobState):
        query = "UPDATE job SET state=? WHERE id=? RETURNING *"
        params = (job_state.value, job_id)
        LOGGER.i(TAG, f"update_job_state(): executing {query} with params {params}")
        val = self.db_manager.cursor.execute(query, params).fetchone()
        self.db_manager.connection.commit()
        if val is not None:
            return JobRecord(int(val[0]), JobType(val[1]), parser.parse(val[2]), JobState(val[3]))
        return None

job_dao = JobDao(db_manager)
