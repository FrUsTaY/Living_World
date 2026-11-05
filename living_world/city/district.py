import uuid
from typing import List, Optional

class District:
    """
    Район города (Центральный, Жилой, Промышленный, Пригород).
    Объединяет дома, предприятия и общественные пространства.
    """
    def __init__(self, name: str, district_type: str = "residential", district_id: Optional[str] = None):
        self.id = district_id or str(uuid.uuid4())
        self.name = name
        self.district_type = district_type  # 'center', 'residential', 'industrial', 'suburb'
        self.building_ids: List[str] = []

    def add_building(self, building_id: str):
        if building_id not in self.building_ids:
            self.building_ids.append(building_id)

    def remove_building(self, building_id: str):
        if building_id in self.building_ids:
            self.building_ids.remove(building_id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "district_type": self.district_type,
            "building_ids": list(self.building_ids)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'District':
        d = cls(name=data["name"], district_type=data.get("district_type", "residential"), district_id=data["id"])
        d.building_ids = list(data.get("building_ids", []))
        return d
