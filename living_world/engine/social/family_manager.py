import uuid
from datetime import datetime
from living_world.engine.event_bus import bus

class FamilyManager:
    def __init__(self, simulation):
        self.simulation = simulation

    def create_family(self, npc_a, npc_b, time_dict):
        family_id = str(uuid.uuid4())
        npc_a.family_id = family_id
        npc_b.family_id = family_id

        if not hasattr(self.simulation, 'families'):
            self.simulation.families = []

        time_str = f"День {time_dict.get('day', 1)}, {time_dict.get('hour', 0):02d}:{time_dict.get('minute', 0):02d}"
        family = {'id': family_id, 'creation_time': time_str, 'is_active': 1}
        self.simulation.families.append(family)

        self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Брак", f"Вступил(а) в брак с {npc_b.first_name}", 1.0, 1.0)
        self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Брак", f"Вступил(а) в брак с {npc_a.first_name}", 1.0, 1.0)

        bus.publish("log_event", f"{npc_a.get_full_name()} и {npc_b.get_full_name()} создали семью!")
        bus.publish("family_created", family)

    def divorce_family(self, npc_a, npc_b, time_dict):
        target_family_id = npc_a.family_id
        npc_a.family_id = None
        npc_b.family_id = None

        if hasattr(self.simulation, 'families') and target_family_id is not None:
            for f in self.simulation.families:
                if f.get('id') == target_family_id and f.get('is_active', 1) == 1:
                    f['is_active'] = 0
                    break

        bus.publish("log_event", f"{npc_a.get_full_name()} и {npc_b.get_full_name()} развелись.")
