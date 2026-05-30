from dataclasses import dataclass

@dataclass
class WeekRecord:
    week: str
    url: str

    def __str__(self):
        return f"week: {self.week}, url: {self.url}"
