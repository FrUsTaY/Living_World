import uuid
from datetime import datetime
from living_world.engine.event_bus import bus

class FamilyManager:
    def __init__(self, simulation):
        self.simulation = simulation
        bus.subscribe("npc_died", self._on_npc_died)

    def _on_npc_died(self, data):
        npc = data.get("npc")
        if not npc: return

        # Find all living relatives
        relatives = set()

        # 1. Parents
        for parent in self.get_parents(npc.id):
            if parent.is_alive:
                relatives.add(parent)

        # 2. Children
        for child in self.get_children(npc.id):
            if child.is_alive:
                relatives.add(child)

        # 3. Siblings
        for sibling in self.get_siblings(npc.id):
            if sibling.is_alive:
                relatives.add(sibling)

        # 4. Spouse (partner in active family)
        if npc.family_id:
            spouses = [n for n in self.simulation.npcs if n.family_id == npc.family_id and n.id != npc.id and n.is_alive]
            for spouse in spouses:
                relatives.add(spouse)

        for relative in relatives:
            self.simulation.memory_manager.add_memory(
                relative.id,
                npc.id,
                "Смерть близкого",
                f"Умер(ла) {npc.first_name}",
                significance=1.0,
                valence=-1.0
            )

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

    def get_parents(self, npc_id):
        npc = next((n for n in self.simulation.npcs if n.id == npc_id), None)
        if not npc:
            return []

        parents = []
        if getattr(npc, 'mother_id', None):
            mother = next((n for n in self.simulation.npcs if n.id == npc.mother_id), None)
            if mother: parents.append(mother)

        if getattr(npc, 'father_id', None):
            father = next((n for n in self.simulation.npcs if n.id == npc.father_id), None)
            if father: parents.append(father)

        return parents

    def get_children(self, npc_id):
        children = []
        for npc in self.simulation.npcs:
            if getattr(npc, 'mother_id', None) == npc_id or getattr(npc, 'father_id', None) == npc_id:
                children.append(npc)
        return children

    def get_siblings(self, npc_id):
        npc = next((n for n in self.simulation.npcs if n.id == npc_id), None)
        if not npc:
            return []

        mother_id = getattr(npc, 'mother_id', None)
        father_id = getattr(npc, 'father_id', None)

        if not mother_id and not father_id:
            return []

        siblings = []
        for other in self.simulation.npcs:
            if other.id == npc_id:
                continue

            other_mother_id = getattr(other, 'mother_id', None)
            other_father_id = getattr(other, 'father_id', None)

            is_sibling = False
            if mother_id and other_mother_id == mother_id:
                is_sibling = True
            elif father_id and other_father_id == father_id:
                is_sibling = True

            if is_sibling:
                siblings.append(other)

        return siblings
