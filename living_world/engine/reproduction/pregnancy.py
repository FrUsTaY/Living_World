from datetime import datetime
import uuid

class Pregnancy:
    def __init__(self, mother_id: str, father_id: str, start_date: datetime, expected_birth_date: datetime, status: str = "active", preg_id: str = None):
        self.id = preg_id or str(uuid.uuid4())
        self.mother_id = mother_id
        self.father_id = father_id
        self.start_date = start_date
        self.expected_birth_date = expected_birth_date
        self.status = status

    def to_dict(self):
        return {
            'id': self.id,
            'mother_id': self.mother_id,
            'father_id': self.father_id,
            'start_date': self.start_date.isoformat(),
            'expected_birth_date': self.expected_birth_date.isoformat(),
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            mother_id=data['mother_id'],
            father_id=data['father_id'],
            start_date=datetime.fromisoformat(data['start_date']),
            expected_birth_date=datetime.fromisoformat(data['expected_birth_date']),
            status=data['status'],
            preg_id=data['id']
        )
