import uuid
from datetime import datetime
from living_world.engine.event_bus import bus

class FamilyManager:
    def __init__(self, simulation):
        self.simulation = simulation

    def process_family_ticks(self):
        # We don't need to check this often. Once a day or every few hours is enough.
        # Let's say we check occasionally when called (e.g., from SocialManager every 60 ticks)

        # Look for potential partners
        for npc_a in self.simulation.npcs:
            if npc_a.family_id is not None:
                continue # Already in a family
            if npc_a.age < 18:
                continue

            # Find a partner they have high romantic interest and trust with
            rels_a = self.simulation.relationship_manager.get_all_relationships_for(npc_a.id)
            for rel_a_b in rels_a:
                if rel_a_b['romantic_interest'] > 70 and rel_a_b['trust'] > 60:
                    npc_b = next((n for n in self.simulation.npcs if n.id == rel_a_b['target_npc_id']), None)
                    if npc_b and npc_b.family_id is None and npc_b.age >= 18:
                        rel_b_a = self.simulation.relationship_manager.get_relationship(npc_b.id, npc_a.id)
                        if rel_b_a['romantic_interest'] > 70 and rel_b_a['trust'] > 60:
                            # Both like each other enough. Boldness determines who proposes.
                            if npc_a.traits['boldness'] > npc_b.traits['boldness']:
                                self._propose(npc_a, npc_b)
                            else:
                                self._propose(npc_b, npc_a)
                            break # Only one proposal per tick for npc_a

    def _propose(self, proposer, target):
        # Determine success. Since stats are already high, chance is very high.
        # But we can add a small random factor or check tension.
        rel_target_proposer = self.simulation.relationship_manager.get_relationship(target.id, proposer.id)

        if rel_target_proposer['tension'] < 20:
            # Success
            family_id = str(uuid.uuid4())
            proposer.family_id = family_id
            target.family_id = family_id

            # Create family record
            if not hasattr(self.simulation, 'families'):
                self.simulation.families = []

            time_dict = self.simulation.time.get_time_dict()
            time_str = f"День {time_dict['day']}, {time_dict['hour']:02d}:{time_dict['minute']:02d}"

            family = {
                'id': family_id,
                'creation_time': time_str,
                'is_active': 1
            }
            self.simulation.families.append(family)

            # Memories
            self.simulation.memory_manager.add_memory(
                proposer.id, target.id, "Брак", f"Вступил(а) в брак с {target.get_full_name()}", time_dict, significance=1.0
            )
            self.simulation.memory_manager.add_memory(
                target.id, proposer.id, "Брак", f"Вступил(а) в брак с {proposer.get_full_name()}", time_dict, significance=1.0
            )

            bus.publish("log_event", f"{proposer.get_full_name()} и {target.get_full_name()} создали семью!")
            bus.publish("family_created", family)
        else:
            # Rejection
            time_dict = self.simulation.time.get_time_dict()
            self.simulation.memory_manager.add_memory(
                proposer.id, target.id, "Отказ", f"{target.first_name} отверг(ла) предложение", time_dict, significance=0.8
            )
            self.simulation.relationship_manager.modify_relationship(proposer.id, target.id, 'tension', 20.0)
            self.simulation.relationship_manager.modify_relationship(proposer.id, target.id, 'trust', -10.0)
