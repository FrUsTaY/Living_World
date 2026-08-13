from living_world.engine.event_bus import bus
from living_world.engine.social.compatibility import CompatibilityManager
import random

class SocialManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.tick_counter = 0

    def process_social_ticks(self):
        self.tick_counter += 1
        if self.tick_counter < 10:
            return

        self.tick_counter = 0

        location_groups = {}
        for npc in self.simulation.npcs:
            loc = npc.current_location
            if not loc:
                continue
            if loc not in location_groups:
                location_groups[loc] = []
            location_groups[loc].append(npc)

        time_dict = self.simulation.time.get_time_dict()
        for loc_id, npcs_in_loc in location_groups.items():
            if len(npcs_in_loc) < 2:
                continue
            self._process_group(npcs_in_loc, time_dict)

        # Also check family logic occasionally (e.g., when tick_counter == 0)
        self.simulation.family_manager.process_family_ticks()

    def _process_group(self, npcs_in_loc, time_dict):
        for npc_a in npcs_in_loc:
            initiate_chance = 0.1 + (npc_a.traits['sociability'] * 0.1)
            if initiate_chance < 0: initiate_chance = 0.05

            if random.random() < initiate_chance:
                targets = [n for n in npcs_in_loc if n.id != npc_a.id]
                if not targets:
                    continue
                npc_b = random.choice(targets)
                self._resolve_interaction(npc_a, npc_b, time_dict)

    def _resolve_interaction(self, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager
        rel_a_b = rel_mgr.get_relationship(npc_a.id, npc_b.id)
        rel_b_a = rel_mgr.get_relationship(npc_b.id, npc_a.id)

        if rel_a_b['familiarity'] == 0:
            self._handle_greeting(npc_a, npc_b, time_dict)
            return

        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', 0.5)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', 0.5)

        compatibility = CompatibilityManager.calculate_compatibility(npc_a, npc_b)

        # Check for memories that might affect this interaction
        memories_a = self.simulation.memory_manager.get_memories_for(npc_a.id)
        recent_conflict_a = any(m['target_npc_id'] == npc_b.id and m['event_type'] == "Ссора" for m in memories_a[-5:])

        # Determine Interaction Type
        interaction_type = "chat"

        if rel_a_b['tension'] > 40 or recent_conflict_a:
            if random.random() < 0.3 + (npc_a.traits['conflict'] * 0.2):
                interaction_type = "argue"
        elif rel_a_b['romantic_interest'] > 30 and npc_a.age >= 18 and npc_b.age >= 18:
            if random.random() < 0.2 + (npc_a.traits['boldness'] * 0.2):
                interaction_type = "flirt"
        elif rel_a_b['affinity'] > 50 and rel_a_b['trust'] > 30:
            if random.random() < 0.2:
                interaction_type = "deep_talk"

        if interaction_type == "argue":
            self._handle_argue(npc_a, npc_b, time_dict)
        elif interaction_type == "flirt":
            self._handle_flirt(npc_a, npc_b, time_dict, compatibility)
        elif interaction_type == "deep_talk":
            self._handle_deep_talk(npc_a, npc_b, time_dict, compatibility)
        else:
            self._handle_chat(npc_a, npc_b, time_dict, compatibility)

        # Passive tension decay
        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -0.1)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -0.1)

    def _handle_greeting(self, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager
        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', 10.0)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', 10.0)
        comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
        affinity_change = (npc_a.traits['friendliness'] + npc_b.traits['friendliness']) * 5 + comp * 10
        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', affinity_change)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', affinity_change)

        self.simulation.memory_manager.add_memory(
            npc_a.id, npc_b.id, "Знакомство", f"Познакомился с {npc_b.get_full_name()}", time_dict, significance=0.3
        )
        self.simulation.memory_manager.add_memory(
            npc_b.id, npc_a.id, "Знакомство", f"Познакомился с {npc_a.get_full_name()}", time_dict, significance=0.3
        )

    def _handle_chat(self, npc_a, npc_b, time_dict, compatibility):
        success_chance = 0.5 + (npc_a.traits['friendliness'] * 0.2) + (npc_b.traits['friendliness'] * 0.2) + (compatibility * 0.1)
        rel_mgr = self.simulation.relationship_manager
        rel_a_b = rel_mgr.get_relationship(npc_a.id, npc_b.id)
        if rel_a_b['tension'] > 30: success_chance -= 0.3

        if random.random() < success_chance:
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 1.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 1.0)

            # Chance for romantic interest to spark slowly
            if npc_a.age >= 18 and npc_b.age >= 18 and compatibility > 0.2:
                if random.random() < 0.1:
                    rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', 1.0)
                    rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', 1.0)
        else:
            tension_inc = 1.0 + (npc_b.traits['conflict'] * 0.5)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', tension_inc)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -0.5)

    def _handle_argue(self, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager

        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 5.0)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 10.0)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -5.0)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', -2.0)

        # Memory creation logic for serious arguments
        if rel_mgr.get_relationship(npc_b.id, npc_a.id)['tension'] > 60:
            self.simulation.memory_manager.add_memory(
                npc_b.id, npc_a.id, "Ссора", f"Серьезно поссорился с {npc_a.get_full_name()}", time_dict, significance=0.6
            )

    def _handle_deep_talk(self, npc_a, npc_b, time_dict, compatibility):
        success_chance = 0.6 + compatibility * 0.2
        rel_mgr = self.simulation.relationship_manager

        if random.random() < success_chance:
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', 2.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', 2.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'respect', 1.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'respect', 1.0)
        else:
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.0)

    def _handle_flirt(self, npc_a, npc_b, time_dict, compatibility):
        rel_mgr = self.simulation.relationship_manager
        rel_b_a = rel_mgr.get_relationship(npc_b.id, npc_a.id)

        # B's reaction depends on their affinity for A and compatibility
        success_chance = 0.2 + (rel_b_a['affinity'] / 200.0) + (compatibility * 0.3)

        if random.random() < success_chance:
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', 5.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', 5.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 2.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 2.0)
        else:
            # Failed flirt
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 5.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 2.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -2.0)
