import uuid

class Building:
    def __init__(self, name, b_type, capacity, b_id=None):
        self.id = b_id or str(uuid.uuid4())
        self.name = name
        self.b_type = b_type # 'home', 'work'
        self.capacity = capacity

class City:
    def __init__(self):
        self.buildings = []

    def add_building(self, building):
        self.buildings.append(building)

    def get_homes(self):
        return [b for b in self.buildings if b.b_type == 'home']

    def get_workplaces(self):
        return [b for b in self.buildings if b.b_type == 'work']
