from typing import Dict, Any, Optional

class EducationalInstitution:
    def __init__(self, id: str, inst_type: str, name: str, capacity: int, building_id: str):
        self.id = id
        self.type = inst_type  # "kindergarten", "school", "college", "university"
        self.name = name
        self.capacity = capacity
        self.building_id = building_id
        self.enrolled_npcs = set()

    def has_available_capacity(self) -> bool:
        return len(self.enrolled_npcs) < self.capacity

    def enroll(self, npc_id: str) -> bool:
        if self.has_available_capacity():
            self.enrolled_npcs.add(npc_id)
            return True
        return False

    def unenroll(self, npc_id: str):
        if npc_id in self.enrolled_npcs:
            self.enrolled_npcs.remove(npc_id)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            data['id'],
            data['type'],
            data['name'],
            data['capacity'],
            data['building_id']
        )

class EducationProgram:
    def __init__(self, id: str, institution_id: str, name: str, prog_type: str, duration: int, requirements: Dict[str, Any] = None):
        self.id = id
        self.institution_id = institution_id
        self.name = name
        self.type = prog_type # "full_time", "part_time"
        self.duration = duration # в годах (симуляционных)
        self.requirements = requirements or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        import json
        reqs = data.get('requirements', '{}')
        if isinstance(reqs, str):
            try:
                reqs = json.loads(reqs)
            except:
                reqs = {}
        return cls(
            data['id'],
            data['institution_id'],
            data['name'],
            data['type'],
            data['duration'],
            reqs
        )

class EducationHistoryRecord:
    def __init__(self, npc_id: str, institution_id: str, program_id: str, start_date: str, status: str, end_date: Optional[str] = None, qualification: Optional[str] = None, id: int = None):
        self.id = id
        self.npc_id = npc_id
        self.institution_id = institution_id
        self.program_id = program_id
        self.start_date = start_date
        self.end_date = end_date
        self.status = status # "Окончил", "Отчислен", "Обучается", "Бросил"
        self.qualification = qualification

    def to_dict(self):
        return {
            "id": self.id,
            "npc_id": self.npc_id,
            "institution_id": self.institution_id,
            "program_id": self.program_id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "qualification": self.qualification
        }
