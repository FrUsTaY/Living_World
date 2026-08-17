import math
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
            if not getattr(npc, 'is_available_for_social', lambda: False)(): continue
            from living_world.engine.life_cycle_manager import LifeStage
            if npc.get_life_stage(self.simulation.time.current_datetime) == LifeStage.BABY: continue
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
            # We add social load pressure. Highly overloaded NPCs might just rest and not initiate
            rel_mgr = self.simulation.relationship_manager

            # Count active links roughly
            active_links = sum(1 for r in rel_mgr.get_all_relationships_for(npc_a.id) if abs(r['affinity']) > 20 or r['romantic_interest'] > 20)
            load_penalty = (active_links / 10.0) * 0.05

            initiate_chance = 0.1 + (npc_a.traits.get('sociability', 0) * 0.1) - load_penalty
            initiate_chance = max(0.02, min(0.3, initiate_chance)) # Minimum 2% chance to do something

            if random.random() > initiate_chance:
                continue

            targets = [n for n in npcs_in_loc if n.id != npc_a.id]
            if not targets: continue

            target_weights = []
            for npc_b in targets:
                appeal = self._calculate_appeal(npc_a, npc_b)
                target_weights.append(appeal)

            target_b = random.choices(targets, weights=target_weights, k=1)[0]

            action_name = self._select_action(npc_a, target_b)
            if not action_name: continue

            self._resolve_action(action_name, npc_a, target_b, time_dict)

    def _calculate_appeal(self, npc_a, npc_b):
        rel = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)
        context_score = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

        appeal = 10.0
        appeal += rel['familiarity'] * 0.1
        appeal += rel['affinity'] * 0.15
        appeal += rel['romantic_interest'] * 0.2
        appeal += rel['tension'] * 0.15 * npc_a.traits.get('conflict', 0.0)

        # Recovery: memories boost appeal significantly for old friends
        if context_score > 0 and rel['affinity'] < 20:
            appeal += context_score * 20.0
        else:
            appeal += context_score * 10.0

        # 3.0 Reciprocity Penalty
        sent = rel.get('initiations_sent', 0)
        recvd = rel.get('initiations_received', 0)
        if sent > 3:
            ratio = recvd / float(sent)
            if ratio < 0.3:
                appeal *= 0.5 # A wants to talk 50% less if B ignores them

        return max(1.0, appeal)

    def _select_action(self, npc_a, npc_b):
        rel = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)
        context_score = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

        scores = {}
        if rel['familiarity'] == 0: return 'greeting'

        chat_score = 30 + (npc_a.traits.get('sociability', 0) * 10) + (rel['familiarity'] * 0.1)
        chat_score += context_score * 5.0
        scores['chat'] = max(1, chat_score)

        if rel['familiarity'] > 30:
            comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
            dt_score = (rel['affinity'] * 0.4) + (rel['trust'] * 0.4) + (comp * 10) - (rel['tension'] * 0.2)
            dt_score += context_score * 10.0
            if dt_score > 0: scores['deep_talk'] = dt_score

        tension_factor = rel['tension']
        if tension_factor > 70 and npc_a.traits.get('conflict', 0) < 0.3:
            tension_factor = 70 - (tension_factor - 70)

        argue_score = (tension_factor * 0.5) + (npc_a.traits.get('conflict', 0) * 20) - (npc_a.traits.get('patience', 0) * 10) - (rel['trust'] * 0.2)
        argue_score -= max(-2.0, context_score) * 10.0

        # Household Stress Context
        if getattr(npc_a, 'household_id', None) and npc_a.household_id == getattr(npc_b, 'household_id', None):
            household = self.simulation.household_manager.get_household(npc_a.household_id)
            if household:
                # High household stress makes argument more likely
                argue_score += household.stress * 0.3

        if argue_score > 0: scores['argue'] = min(60, argue_score)

        flirt_score = (rel['romantic_interest'] * 0.8) + (npc_a.traits.get('boldness', 0) * 20) + (rel['affinity'] * 0.2)
        flirt_score += context_score * 5.0
        current_date = self.simulation.time.current_datetime
        if flirt_score > 0 and npc_a.get_age(current_date) >= 18 and npc_b.get_age(current_date) >= 18 and rel['romantic_interest'] > 15:
            scores['flirt'] = flirt_score

        # Divorce Check (replaces Propose as the only family-related check, Propose remains)
        if npc_a.family_id is not None and npc_a.family_id == npc_b.family_id:
            if rel['romantic_interest'] < 20 and rel['affinity'] < 30:
                divorce_score = 5 + (npc_a.traits.get('boldness', 0) * 20) + (20 - rel['romantic_interest']) + (30 - rel['affinity']) - (context_score * 10)
                if divorce_score > 0: scores['divorce'] = divorce_score

        elif rel['romantic_interest'] > 70 and rel['trust'] > 60 and npc_a.family_id is None and npc_b.family_id is None and npc_a.get_age(current_date) >= 18 and npc_b.get_age(current_date) >= 18:
            inclination_a = (npc_a.traits.get('friendliness', 0) + npc_a.traits.get('empathy', 0) + npc_a.traits.get('sociability', 0) - npc_a.traits.get('boldness', 0) * 0.5) / 3.0
            propose_score = 5 + (npc_a.traits.get('boldness', 0) * 20) + (rel['romantic_interest'] - 70) + (rel['trust'] - 60) + (context_score * 10) + (inclination_a * 20)
            if propose_score > 0: scores['propose'] = propose_score

        actions = list(scores.keys())
        weights = list(scores.values())
        if not actions: return 'chat'
        return random.choices(actions, weights=weights, k=1)[0]

    def _resolve_action(self, action_name, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager

        is_meaningful = action_name in ['deep_talk', 'flirt', 'argue', 'propose', 'divorce']

        if action_name == 'greeting':
            self._handle_greeting(npc_a, npc_b, time_dict)
            return

        # 3.0 Meaningful vs Superficial
        rel_mgr.touch_relationship(npc_a.id, npc_b.id, initiator=True, is_meaningful=is_meaningful)
        rel_mgr.touch_relationship(npc_b.id, npc_a.id, initiator=False, is_meaningful=is_meaningful)

        comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
        rel_a_b = rel_mgr.get_relationship(npc_a.id, npc_b.id)
        rel_b_a = rel_mgr.get_relationship(npc_b.id, npc_a.id)
        context_b_a = self.simulation.memory_manager.get_context_score(npc_b.id, npc_a.id)
        context_a_b = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

        # Helper for Diminishing Returns and 3.0 Interaction Saturation
        def get_gain(base_gain, current_val, source_rel):
            diminished = rel_mgr.get_diminishing_returns(base_gain, current_val)
            interactions_today = source_rel.get('daily_interactions_count', 1) - 1
            saturation = math.pow(0.7, max(0, interactions_today))
            return diminished * saturation

        if action_name == 'chat':
            aff_factor_b = max(-15, rel_b_a['affinity']) * 0.1
            ctx_b = max(-2.0, context_b_a)
            olive_branch = (npc_a.traits.get('friendliness', 0) + npc_a.traits.get('empathy', 0)) * 5.0

            success_b = aff_factor_b + (comp * 5) + olive_branch - (rel_b_a['tension'] * 0.05) + (ctx_b * 2.0)

            if success_b >= -5:
                relief_b = 2.0 + (npc_b.traits.get('empathy', 0) * 2.0) + (success_b * 0.2) + (max(0, rel_b_a['trust']) * 0.05)
                if rel_b_a['tension'] > 0: rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -max(1.0, relief_b))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', get_gain(2.8, rel_b_a['affinity'], rel_b_a))
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 1.0)

            aff_factor_a = max(-15, rel_a_b['affinity']) * 0.1
            ctx_a = max(-2.0, context_a_b)
            olive_branch_b = (npc_b.traits.get('friendliness', 0) + npc_b.traits.get('empathy', 0)) * 5.0

            success_a = aff_factor_a + (comp * 5) + olive_branch_b + (success_b * 0.2) + (ctx_a * 2.0)
            if success_a >= -5:
                relief_a = 2.0 + (npc_a.traits.get('empathy', 0) * 2.0) + (success_a * 0.2) + (max(0, rel_a_b['trust']) * 0.05)
                if rel_a_b['tension'] > 0: rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -max(1.0, relief_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', get_gain(2.8, rel_a_b['affinity'], rel_a_b))
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.0)

            self._check_spark(npc_a, npc_b, comp, success_b, success_a, is_deep_talk=False)

        elif action_name == 'deep_talk':
            success_b = (rel_b_a['affinity'] * 0.2) + (comp * 10) + (npc_a.traits.get('friendliness',0) * 5) - (rel_b_a['tension'] * 0.3) + (context_b_a * 5.0)
            if success_b > 0:
                relief_b = 3.0 + (npc_b.traits.get('empathy', 0) * 2.0) + (success_b * 0.2) + (rel_b_a['trust'] * 0.1)
                if rel_b_a['tension'] > 0: rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -max(1.0, relief_b))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', get_gain(5.5, rel_b_a['affinity'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', get_gain(3.5, rel_b_a['trust'], rel_b_a))
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 2.0)

            success_a = (rel_a_b['affinity'] * 0.2) + (comp * 10) + (npc_b.traits.get('friendliness',0) * 5) + (success_b * 0.5) + (context_a_b * 5.0)
            if success_a > 0:
                relief_a = 3.0 + (npc_a.traits.get('empathy', 0) * 2.0) + (success_a * 0.2) + (rel_a_b['trust'] * 0.1)
                if rel_a_b['tension'] > 0: rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -max(1.0, relief_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', get_gain(5.5, rel_a_b['affinity'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', get_gain(3.5, rel_a_b['trust'], rel_a_b))
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 2.0)

            self._check_spark(npc_a, npc_b, comp, success_b, success_a, is_deep_talk=True)

        elif action_name == 'argue':
            is_household_conflict = False
            is_family_conflict = False
            household_id = getattr(npc_a, 'household_id', None)

            if household_id and household_id == getattr(npc_b, 'household_id', None):
                is_household_conflict = True
                parents_a = self.simulation.family_manager.get_parents(npc_a.id)
                parents_b = self.simulation.family_manager.get_parents(npc_b.id)
                siblings_a = self.simulation.family_manager.get_siblings(npc_a.id)
                if npc_b in parents_a or npc_a in parents_b or npc_b in siblings_a or (npc_a.family_id is not None and npc_a.family_id == npc_b.family_id):
                    is_family_conflict = True

            event_title = "Семейный конфликт" if is_family_conflict else ("Бытовой конфликт" if is_household_conflict else "Ссора")

            mem_b = self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, event_title, f"Ссора с {npc_a.first_name}", 0.6, -0.6)
            mem_a = self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, event_title, f"Ссора с {npc_b.first_name}", 0.6, -0.6)

            # If memory generation is skipped due to cooldown, do NOT apply penalties
            if mem_a is None and mem_b is None:
                return

            if rel_b_a['tension'] < 80:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 5.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', -get_gain(2.0, rel_b_a['trust'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -get_gain(4.0, rel_b_a['affinity'], rel_b_a))
            else:
                # Discharge tension (runaway loop breaker)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -10.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -get_gain(1.0, rel_b_a['affinity'], rel_b_a))

            if rel_a_b['tension'] < 80:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 5.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -get_gain(2.0, rel_a_b['trust'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', -get_gain(4.0, rel_a_b['affinity'], rel_a_b))
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -10.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', -get_gain(1.0, rel_a_b['affinity'], rel_a_b))

            if is_household_conflict:
                from living_world.engine.observer.world_event import EventType, EventImportance
                if hasattr(self.simulation, 'event_aggregator'):
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.CONFLICT_MAJOR,
                        importance=EventImportance.HIGH,
                        message=f"{event_title} между {npc_a.first_name} и {npc_b.first_name}.",
                        participants=[npc_a.id, npc_b.id, household_id],
                        data={"conflict_type": event_title}
                    )
                bus.publish("family_conflict", {"household_id": household_id, "npc_a": npc_a, "npc_b": npc_b})

        elif action_name == 'flirt':
            success_b = (rel_b_a['romantic_interest'] * 0.5) + (rel_b_a['affinity'] * 0.2) + (comp * 10) - (rel_b_a['tension'] * 0.5) + (context_b_a * 5.0)
            if success_b > 5:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', get_gain(5.0, rel_b_a['romantic_interest'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', get_gain(2.0, rel_b_a['affinity'], rel_b_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', get_gain(5.0, rel_a_b['romantic_interest'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', get_gain(2.0, rel_a_b['affinity'], rel_a_b))

                if success_b > 20 and random.random() < 0.3:
                    self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Флирт", f"Удачный флирт с {npc_a.first_name}", 0.5, 0.7)
                    self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Флирт", f"Удачный флирт с {npc_b.first_name}", 0.5, 0.7)
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 3.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -1.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 5.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -get_gain(5.0, rel_a_b['romantic_interest'], rel_a_b))
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Отказ", f"{npc_b.first_name} отверг(ла) флирт", 0.7, -0.8)

        elif action_name == 'propose':
            inclination_b = (npc_b.traits.get('friendliness', 0) + npc_b.traits.get('empathy', 0) + npc_b.traits.get('sociability', 0) - npc_b.traits.get('boldness', 0) * 0.5) / 3.0
            success_b = False
            if rel_b_a['romantic_interest'] > 70 and rel_b_a['trust'] > 60 and rel_b_a['tension'] < 30:
                accept_chance = 0.5 + (inclination_b * 0.5) + (rel_b_a['romantic_interest'] - 70) * 0.01 + (context_b_a * 0.2)
                if random.random() < accept_chance: success_b = True

            if success_b:
                self.simulation.family_manager.create_family(npc_a, npc_b, time_dict)
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 20.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -15.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -10.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 10.0)
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Отказ", f"{npc_b.first_name} отверг(ла) предложение", 0.9, -1.0)

        elif action_name == 'divorce':
            self.simulation.family_manager.divorce_family(npc_a, npc_b, time_dict)

            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 40.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -30.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 40.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', -30.0)

            self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Развод", f"Развелся с {npc_b.first_name}", 1.0, -1.0)
            self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Развод", f"Развелся с {npc_a.first_name}", 1.0, -1.0)

    def _check_spark(self, npc_a, npc_b, comp, success_b, success_a, is_deep_talk=False):
        current_date = self.simulation.time.current_datetime
        if npc_a.get_age(current_date) < 18 or npc_b.get_age(current_date) < 18: return
        base_chance = 0.25 if is_deep_talk else 0.05

        spark_happened = False

        if success_b > 5:
            chance_b = base_chance * max(0.1, comp)
            if random.random() < chance_b:
                self.simulation.relationship_manager.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', random.uniform(15.0, 25.0))
                spark_happened = True

        if success_a > 5:
            chance_a = base_chance * max(0.1, comp)
            if random.random() < chance_a:
                self.simulation.relationship_manager.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', random.uniform(15.0, 25.0))
                spark_happened = True

        if spark_happened:
            from living_world.engine.observer.world_event import EventType, EventImportance
            if hasattr(self.simulation, 'event_aggregator'):
                # Avoid spamming this event if they already have high interest, but for simplicity let's just log it if it happens
                # Usually check_spark pushes it from 0 to 20
                if self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)['romantic_interest'] < 30:
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.ROMANCE_START,
                        importance=EventImportance.HIGH,
                        message=f"Между {npc_a.first_name} и {npc_b.first_name} проскочила искра.",
                        participants=[npc_a.id, npc_b.id]
                    )

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

        mem_a = self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Знакомство", f"Познакомился с {npc_b.first_name}", 0.3, 0.1)
        self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Знакомство", f"Познакомился с {npc_a.first_name}", 0.3, 0.1)

        if mem_a:
            from living_world.engine.observer.world_event import EventType, EventImportance
            if hasattr(self.simulation, 'event_aggregator'):
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.SOCIAL_INTERACTION,
                    importance=EventImportance.MEDIUM,
                    message=f"{npc_a.get_full_name()} и {npc_b.get_full_name()} познакомились.",
                    participants=[npc_a.id, npc_b.id]
                )
