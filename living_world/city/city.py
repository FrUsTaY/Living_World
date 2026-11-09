import uuid
from typing import List, Optional
from living_world.city.district import District

class Building:
    def __init__(self, name, b_type, capacity, b_id=None, district_id=None, x: float = 0.0, y: float = 0.0, condition: float = 100.0):
        self.id = b_id or str(uuid.uuid4())
        self.name = name
        self.b_type = b_type # 'home', 'work', 'park', 'cafe', 'shop', 'public'
        self.capacity = capacity
        self.district_id = district_id
        self.x = float(x)
        self.y = float(y)
        self.condition = float(condition)

class City:
    def __init__(self):
        self.buildings: List[Building] = []
        self.districts: List[District] = []
        self._cultural_cache: Optional[List[Building]] = None

    def add_building(self, building: Building, district_id: Optional[str] = None):
        self._cultural_cache = None
        if district_id:
            building.district_id = district_id
            district = self.get_district(district_id)
            if district:
                district.add_building(building.id)
        self.buildings.append(building)

    def get_cultural_buildings(self) -> List[Building]:
        if getattr(self, '_cultural_cache', None) is not None and getattr(self, '_cultural_cache_buildings', None) == self.buildings:
            return self._cultural_cache
        cult_types = {'library', 'cinema', 'theater', 'stadium', 'club', 'park', 'sports'}
        keywords = ('библиотек', 'кино', 'театр', 'стадион', 'парк', 'музей')
        res = []
        for b in self.buildings:
            if getattr(b, 'b_type', '') in cult_types:
                res.append(b)
            elif any(w in b.name.lower() for w in keywords):
                res.append(b)
        self._cultural_cache = res
        self._cultural_cache_buildings = list(self.buildings)
        return res

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

    def calculate_distance(self, b_id_1: str, b_id_2: str) -> float:
        b1 = self.get_building(b_id_1)
        b2 = self.get_building(b_id_2)
        if not b1 or not b2:
            return 0.0
        import math
        return math.sqrt((b1.x - b2.x)**2 + (b1.y - b2.y)**2)
