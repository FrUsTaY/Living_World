import uuid
from datetime import datetime
import json

class Household:
    def __init__(self, home_id: str, creation_time: str, household_id: str = None, stress: float = 0.0,
                 appliances: list = None, pet: dict = None, home_comfort: float = 40.0):
        self.id = household_id or str(uuid.uuid4())
        self.home_id = home_id
        self.creation_time = creation_time
        self.stress = stress
        self.appliances = appliances if appliances is not None else []
        self.pet = pet
        self.home_comfort = float(home_comfort)

    def to_dict(self):
        return {
            'id': self.id,
            'home_id': self.home_id,
            'creation_time': self.creation_time,
            'stress': self.stress,
            'appliances': self.appliances,
            'pet': self.pet,
            'home_comfort': self.home_comfort
        }

    @classmethod
    def from_dict(cls, data):
        appliances = data.get('appliances', [])
        if isinstance(appliances, str):
            try:
                appliances = json.loads(appliances)
            except Exception:
                appliances = []

        pet = data.get('pet')
        if isinstance(pet, str):
            try:
                pet = json.loads(pet)
            except Exception:
                pet = None

        return cls(
            home_id=data.get('home_id'),
            creation_time=data.get('creation_time'),
            household_id=data.get('id'),
            stress=float(data.get('stress', 0.0)),
            appliances=appliances if isinstance(appliances, list) else [],
            pet=pet if isinstance(pet, dict) else None,
            home_comfort=float(data.get('home_comfort', 40.0))
        )
