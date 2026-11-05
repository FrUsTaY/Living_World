import uuid
from typing import List, Optional
from living_world.city.district import District

class Building:
    def __init__(self, name, b_type, capacity, b_id=None, district_id=None):
        self.id = b_id or str(uuid.uuid4())
        self.name = name
        self.b_type = b_type # 'home', 'work', 'park', 'cafe', 'shop', 'public'
        self.capacity = capacity
        self.district_id = district_id

class City:
    def __init__(self):
        self.buildings: List[Building] = []
        self.districts: List[District] = []

    def add_building(self, building: Building, district_id: Optional[str] = None):
        if district_id:
            building.district_id = district_id
            district = self.get_district(district_id)
            if district:
                district.add_building(building.id)
        self.buildings.append(building)

    def add_district(self, district: District):
        self.districts.append(district)

    def get_district(self, district_id: str) -> Optional[District]:
        for d in self.districts:
            if d.id == district_id:
                return d
        return None

    def get_district_for_building(self, building_id: str) -> Optional[District]:
        b = self.get_building(building_id)
        if b and b.district_id:
            return self.get_district(b.district_id)
        for d in self.districts:
            if building_id in d.building_ids:
                return d
        return None

    def get_homes(self) -> List[Building]:
        return [b for b in self.buildings if b.b_type == 'home']

    def get_workplaces(self) -> List[Building]:
        return [b for b in self.buildings if b.b_type == 'work']

    def get_public_places(self) -> List[Building]:
        return [b for b in self.buildings if b.b_type in ['park', 'cafe', 'shop', 'public']]

    def get_places_by_type(self, b_type: str) -> List[Building]:
        return [b for b in self.buildings if b.b_type == b_type]

    def get_building(self, b_id: str) -> Optional[Building]:
        for b in self.buildings:
            if b.id == b_id:
                return b
        return None
