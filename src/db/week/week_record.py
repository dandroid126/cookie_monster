from dataclasses import dataclass

@dataclass
class WeekRecord:
    week: str
    url: str
    cookies: list[dict[str, str]]

    def __str__(self):
        return f"week: {self.week}, url: {self.url}, cookies: {str(self.cookies)}"
