from dataclasses import dataclass

@dataclass
class CookieRecord:
    cookieId: str
    name: str
    description: str
    newAerialImage: str
    week: str

    def __str__(self):
        return f"cookieId: {self.cookieId}, name: {self.name}, description: {self.description}, newAerialImage: {self.newAerialImage}, week: {self.week}"
