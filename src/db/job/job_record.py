from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class JobType(Enum):
    UNKNOWN = 0
    POST_COOKIES = 1

class JobState(Enum):
    ABORTED = -1
    QUEUED = 0
    IN_PROGRESS = 1
    COMPLETED = 2

@dataclass
class JobRecord:
    id: int
    type: JobType
    created_at: datetime
    state: JobState
