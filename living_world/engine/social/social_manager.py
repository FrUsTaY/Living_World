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
            if not loc: continue
            if loc not in location_groups: location_groups[loc] = []
            location_groups[loc].append(npc)

        time_dict = self.simulation.time.get_time_dict()
        for loc_id, npcs_in_loc in location_groups.items():
            if len(npcs_in_loc) < 2: continue
            self._process_group(npcs_in_loc, time_dict)



    def _process_group(self, npcs_in_loc, time_dict):
        for npc_a in npcs_in_loc:
            # Initiative Check
            initiate_chance = 0.1 + (npc_a.traits['sociability'] * 0.1)
            initiate_chance = max(0.05, min(0.3, initiate_chance))

            if random.random() > initiate_chance:
                continue

            # 1. Target Selection (Appeal)
            targets = [n for n in npcs_in_loc if n.id != npc_a.id]
            if not targets: continue

            target_weights = []
            for npc_b in targets:
                appeal = self._calculate_appeal(npc_a, npc_b)
                target_weights.append(appeal)

            # Weighted Random Choice for Target
            target_b = random.choices(targets, weights=target_weights, k=1)[0]

            # 2. Action Selection
            action_name = self._select_action(npc_a, target_b)
            if not action_name: continue

            # 3. Asymmetric Resolution
            self._resolve_action(action_name, npc_a, target_b, time_dict)

    def _calculate_appeal(self, npc_a, npc_b):
        rel = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)
        context_score = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

        appeal = 10.0 # Base
        appeal += rel['familiarity'] * 0.1
        appeal += rel['affinity'] * 0.15
        appeal += rel['romantic_interest'] * 0.2

        # Conflict trait influence
        conflict_a = npc_a.traits.get('conflict', 0.0)
        appeal += rel['tension'] * 0.15 * conflict_a

        appeal += context_score * 10.0

        return max(1.0, appeal)

    def _select_action(self, npc_a, npc_b):
        rel = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)
        context_score = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

        scores = {}

        # Chat
        chat_score = 30 + (npc_a.traits.get('sociability', 0) * 10) + (rel['familiarity'] * 0.1)
        scores['chat'] = max(1, chat_score)

        if rel['familiarity'] == 0:
            return 'greeting'

        # Deep Talk
        if rel['familiarity'] > 30:
            comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
            dt_score = (rel['affinity'] * 0.4) + (rel['trust'] * 0.4) + (comp * 10) - (rel['tension'] * 0.2)
            if dt_score > 0: scores['deep_talk'] = dt_score

        # Argue
        argue_score = (rel['tension'] * 0.5) + (npc_a.traits.get('conflict', 0) * 20) - (npc_a.traits.get('patience', 0) * 10) - (rel['trust'] * 0.2)
        if argue_score > 0: scores['argue'] = argue_score

        # Flirt
        flirt_score = (rel['romantic_interest'] * 0.6) + (npc_a.traits.get('boldness', 0) * 20) + (rel['affinity'] * 0.2)
        if flirt_score > 0 and npc_a.age >= 18 and npc_b.age >= 18:
            scores['flirt'] = flirt_score

        # Propose
        if rel['romantic_interest'] > 70 and rel['trust'] > 60 and npc_a.family_id is None and npc_b.family_id is None and npc_a.age >= 18 and npc_b.age >= 18:
            inclination_a = (npc_a.traits.get('friendliness', 0) + npc_a.traits.get('empathy', 0) + npc_a.traits.get('sociability', 0) - npc_a.traits.get('boldness', 0) * 0.5) / 3.0
            propose_score = 5 + (npc_a.traits.get('boldness', 0) * 20) + (rel['romantic_interest'] - 70) + (rel['trust'] - 60) + (context_score * 10) + (inclination_a * 20)
            if propose_score > 0:
                scores['propose'] = propose_score

        actions = list(scores.keys())
        weights = list(scores.values())

        if not actions: return 'chat' # Fallback

        return random.choices(actions, weights=weights, k=1)[0]

    def _resolve_action(self, action_name, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager

        if action_name == 'greeting':
            self._handle_greeting(npc_a, npc_b, time_dict)
            return

        # Touch relationships to update timestamps
        rel_mgr.touch_relationship(npc_a.id, npc_b.id)
        rel_mgr.touch_relationship(npc_b.id, npc_a.id)

        comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)

        # Current relationships
        rel_a_b = rel_mgr.get_relationship(npc_a.id, npc_b.id)
        rel_b_a = rel_mgr.get_relationship(npc_b.id, npc_a.id)

        if action_name == 'chat':
            # B's reaction
            success_b = (rel_b_a['affinity'] * 0.1) + (comp * 5) + (npc_a.traits.get('friendliness',0) * 5) - (rel_b_a['tension'] * 0.2)
            if success_b >= 0:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 0.5)
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 1.0)

            # A's reaction
            success_a = (rel_a_b['affinity'] * 0.1) + (comp * 5) + (npc_b.traits.get('friendliness',0) * 5) + (success_b * 0.2)
            if success_a >= 0:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 0.5)
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.0)

            self._check_spark(npc_a, npc_b, comp, success_b, success_a)

        elif action_name == 'deep_talk':
            success_b = (rel_b_a['affinity'] * 0.2) + (comp * 10) + (npc_a.traits.get('friendliness',0) * 5) - (rel_b_a['tension'] * 0.3)
            if success_b > 5:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 2.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', 1.0)
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 2.0)

            success_a = (rel_a_b['affinity'] * 0.2) + (comp * 10) + (npc_b.traits.get('friendliness',0) * 5) + (success_b * 0.5)
            if success_a > 5:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 2.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', 1.0)
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 2.0)

            self._check_spark(npc_a, npc_b, comp, success_b, success_a)

        elif action_name == 'argue':
            # Arguing hurts trust and increases tension
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 5.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', -2.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -3.0)

            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 3.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -1.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', -1.0)

            # Significant argue creates memory
            if rel_b_a['tension'] > 50 or rel_a_b['tension'] > 50:
                self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Ссора", f"Ссора с {npc_a.first_name}", 0.6, -0.6)
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Ссора", f"Ссора с {npc_b.first_name}", 0.4, -0.4)

        elif action_name == 'flirt':
            success_b = (rel_b_a['romantic_interest'] * 0.5) + (rel_b_a['affinity'] * 0.2) + (comp * 10) - (rel_b_a['tension'] * 0.5)

            if success_b > 10: # Accept flirt
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', 5.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 2.0)

                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', 5.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 2.0)

                # Big success memory
                if success_b > 30 and random.random() < 0.3:
                    self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Флирт", f"Удачный флирт с {npc_a.first_name}", 0.5, 0.7)
                    self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Флирт", f"Удачный флирт с {npc_b.first_name}", 0.5, 0.7)

            else: # Reject flirt
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 5.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -2.0)

                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 10.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -5.0)

                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Отказ", f"{npc_b.first_name} отверг(ла) флирт", 0.7, -0.8)

        elif action_name == 'propose':
            # Target's reaction
            inclination_b = (npc_b.traits.get('friendliness', 0) + npc_b.traits.get('empathy', 0) + npc_b.traits.get('sociability', 0) - npc_b.traits.get('boldness', 0) * 0.5) / 3.0

            success_b = False
            if rel_b_a['romantic_interest'] > 70 and rel_b_a['trust'] > 60 and rel_b_a['tension'] < 30:
                accept_chance = 0.5 + (inclination_b * 0.5) + (rel_b_a['romantic_interest'] - 70) * 0.01
                if random.random() < accept_chance:
                    success_b = True

            if success_b:
                # Call family manager to technically create the family
                self.simulation.family_manager.create_family(npc_a, npc_b, time_dict)
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 30.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -20.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -15.0)

                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 10.0)
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Отказ", f"{npc_b.first_name} отверг(ла) предложение", 0.9, -1.0)

    def _check_spark(self, npc_a, npc_b, comp, success_b, success_a):
        # Spark can happen if they are compatible and it was a successful interaction
        if npc_a.age < 18 or npc_b.age < 18: return

        # A spark for B
        if success_b > 5 and random.random() < 0.05 * max(0, comp):
            self.simulation.relationship_manager.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', random.uniform(5.0, 15.0))

        # A spark for A
        if success_a > 5 and random.random() < 0.05 * max(0, comp):
            self.simulation.relationship_manager.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', random.uniform(5.0, 15.0))

    def _handle_greeting(self, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager
        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', 10.0)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', 10.0)

        comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
        affinity_base = comp * 10

        aff_a = affinity_base + (npc_b.traits.get('friendliness', 0) * 5)
        aff_b = affinity_base + (npc_a.traits.get('friendliness', 0) * 5)

        rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', aff_a)
        rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', aff_b)

        self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Знакомство", f"Познакомился с {npc_b.first_name}", 0.3, 0.1)
        self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Знакомство", f"Познакомился с {npc_a.first_name}", 0.3, 0.1)
