import uuid
from datetime import datetime

class Household:
    def __init__(self, home_id: str, creation_time: str, household_id: str = None):
        self.id = household_id or str(uuid.uuid4())
        self.home_id = home_id
        self.creation_time = creation_time

    def to_dict(self):
        return {
            'id': self.id,
            'home_id': self.home_id,
            'creation_time': self.creation_time
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            home_id=data.get('home_id'),
            creation_time=data.get('creation_time'),
            household_id=data.get('id')
        )
