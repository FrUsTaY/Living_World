import uuid
from datetime import datetime

class Household:
    def __init__(self, home_id: str, creation_time: str, household_id: str = None, stress: float = 0.0):
        self.id = household_id or str(uuid.uuid4())
        self.home_id = home_id
        self.creation_time = creation_time
        self.stress = stress

    def to_dict(self):
        return {
            'id': self.id,
            'home_id': self.home_id,
            'creation_time': self.creation_time,
            'stress': self.stress
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            home_id=data.get('home_id'),
            creation_time=data.get('creation_time'),
            household_id=data.get('id'),
            stress=data.get('stress', 0.0)
        )
