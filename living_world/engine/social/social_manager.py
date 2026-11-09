import math
from living_world.engine.event_bus import bus
from living_world.engine.life_cycle_manager import LifeStage
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
            rel_mgr = self.simulation.relationship_manager

            active_links = sum(1 for r in rel_mgr.get_all_relationships_for(npc_a.id) if abs(r['affinity']) > 20 or r['romantic_interest'] > 20)
            load_penalty = (active_links / 10.0) * 0.04

            initiate_chance = 0.12 + (npc_a.traits.get('sociability', 0) * 0.1) - load_penalty
            initiate_chance = max(0.03, min(0.35, initiate_chance))

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

        # Dating partner preference
        if getattr(npc_a, 'dating_partner_id', None) == npc_b.id:
            appeal += 25.0

        # Phase 2: Colleagues & Neighbors boost
        if npc_a.work_id and npc_a.work_id == npc_b.work_id:
            appeal += 12.0
        if npc_a.home_id and npc_a.home_id == npc_b.home_id:
            appeal += 10.0

        # Recovery: memories boost appeal significantly for old friends
        if context_score > 0 and rel['affinity'] < 20:
            appeal += context_score * 15.0
        else:
            appeal += context_score * 8.0

        # Reciprocity Penalty
        sent = rel.get('initiations_sent', 0)
        recvd = rel.get('initiations_received', 0)
        if sent > 3:
            ratio = recvd / float(sent)
            if ratio < 0.3:
                appeal *= 0.5

        return max(1.0, appeal)

    def _select_action(self, npc_a, npc_b):
        rel = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)
        context_score = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

        scores = {}
        if rel['familiarity'] == 0: return 'greeting'

        chat_score = 30 + (npc_a.traits.get('sociability', 0) * 10) + (rel['familiarity'] * 0.1)
        chat_score += context_score * 4.0
        scores['chat'] = max(1, chat_score)

        # Deep talk threshold: familiarity >= 18 and affinity >= 10
        if rel['familiarity'] >= 18 and rel['affinity'] >= 10:
            comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
            dt_score = (rel['affinity'] * 0.35) + (rel['trust'] * 0.4) + (comp * 10) + (rel['familiarity'] * 0.15) - (rel['tension'] * 0.2)
            dt_score += max(-2.0, context_score) * 4.0
            if dt_score > 0: scores['deep_talk'] = dt_score

        tension_factor = rel['tension']
        if tension_factor > 70 and npc_a.traits.get('conflict', 0) < 0.3:
            tension_factor = 70 - (tension_factor - 70)

        argue_score = (tension_factor * 0.4) + (npc_a.traits.get('conflict', 0) * 15) - (npc_a.traits.get('patience', 0) * 10) - (rel['trust'] * 0.2)
        argue_score -= max(-1.0, min(2.0, context_score)) * 4.0

        # Household Stress Context
        if getattr(npc_a, 'household_id', None) and npc_a.household_id == getattr(npc_b, 'household_id', None):
            household = self.simulation.household_manager.get_household(npc_a.household_id)
            if household:
                argue_score += household.stress * 0.15

        if argue_score > 0: scores['argue'] = min(40, argue_score)

        current_date = self.simulation.time.current_datetime
        is_adult_pair = (npc_a.get_age(current_date) >= 18 and npc_b.get_age(current_date) >= 18 and npc_a.gender != npc_b.gender)

        # Flirt check (for singles or active couple)
        if is_adult_pair and npc_a.family_id is None and npc_b.family_id is None:
            if npc_a.dating_partner_id in [None, npc_b.id] and npc_b.dating_partner_id in [None, npc_a.id]:
                flirt_score = (rel['romantic_interest'] * 0.7) + (npc_a.traits.get('boldness', 0) * 15) + (rel['affinity'] * 0.25)
                flirt_score += max(-2.0, context_score) * 3.0
                if getattr(npc_a, 'dating_partner_id', None) == npc_b.id:
                    flirt_score += 30.0 # Dating partners flirt frequently
                if flirt_score > 0 and (rel['romantic_interest'] > 10 or (rel['affinity'] > 15 and npc_a.traits.get('boldness', 0) > -0.2)):
                    scores['flirt'] = flirt_score

        # Divorce Check
        if npc_a.family_id is not None and npc_a.family_id == npc_b.family_id:
            if rel['romantic_interest'] < 15 and rel['affinity'] < 20 and rel['tension'] > 40:
                divorce_score = 5 + (npc_a.traits.get('boldness', 0) * 15) + (15 - rel['romantic_interest']) + (20 - rel['affinity']) - (context_score * 5)
                if divorce_score > 0: scores['divorce'] = divorce_score

        # Propose Check (requires mature dating relationship)
        elif is_adult_pair and getattr(npc_a, 'dating_partner_id', None) == npc_b.id and npc_a.family_id is None and npc_b.family_id is None:
            if rel['romantic_interest'] >= 50 and rel['trust'] >= 30 and rel['affinity'] >= 35:
                inclination_a = (npc_a.traits.get('friendliness', 0) + npc_a.traits.get('empathy', 0) + npc_a.traits.get('sociability', 0)) / 3.0
                propose_score = 10 + (npc_a.traits.get('boldness', 0) * 15) + (rel['romantic_interest'] - 50) + (rel['trust'] - 30) + (context_score * 4) + (inclination_a * 15)
                if propose_score > 0: scores['propose'] = propose_score

        # Apology check
        if rel['tension'] > 20 and rel['affinity'] > -20:
            empathy_a = npc_a.traits.get('empathy', 0.0)
            friendliness_a = npc_a.traits.get('friendliness', 0.0)
            if empathy_a > -0.2 or friendliness_a > 0.0:
                apology_score = (rel['tension'] * 0.35) + (empathy_a * 15) + (friendliness_a * 10) - (npc_a.traits.get('conflict', 0) * 15)
                if apology_score > 0:
                    scores['apology'] = apology_score

        # Help / Gift check
        if rel['familiarity'] >= 15 and rel['affinity'] >= 20 and getattr(npc_a, 'money', 0) >= 1200:
            if npc_a.traits.get('frugality', 0) < 0.3 and (getattr(npc_b, 'money', 0) < 800 or getattr(npc_b, 'mood', 100) < 45):
                help_score = 15 + (npc_a.traits.get('empathy', 0) * 15) + (rel['affinity'] * 0.15) - (npc_a.traits.get('frugality', 0) * 15)
                if help_score > 0:
                    scores['help_or_gift'] = help_score

        # Breakup Check (dating partners before marriage with severe tension/loss of romance)
        if getattr(npc_a, 'dating_partner_id', None) == npc_b.id and npc_a.family_id is None:
            if rel['tension'] >= 40 and rel['affinity'] <= 15 and rel['romantic_interest'] <= 25:
                breakup_score = 15 + (rel['tension'] * 0.4) - (rel['affinity'] * 0.5) - (rel['romantic_interest'] * 0.5)
                if breakup_score > 0:
                    scores['breakup'] = breakup_score

        # Colleague work talk
        if npc_a.work_id and npc_a.work_id == npc_b.work_id and npc_a.current_location == npc_a.work_id:
            scores['colleague_talk'] = 24.0 + (npc_a.traits.get('diligence', 0.0) * 10.0)

        # Neighbor community talk
        if npc_a.home_id and npc_a.home_id == npc_b.home_id and npc_a.family_id != npc_b.family_id:
            scores['neighbor_talk'] = 20.0 + (npc_a.traits.get('friendliness', 0.0) * 10.0)

        actions = list(scores.keys())
        weights = list(scores.values())
        if not actions: return 'chat'
        return random.choices(actions, weights=weights, k=1)[0]

    def _resolve_action(self, action_name, npc_a, npc_b, time_dict):
        rel_mgr = self.simulation.relationship_manager

        is_meaningful = action_name in ['deep_talk', 'flirt', 'argue', 'propose', 'divorce', 'apology', 'help_or_gift', 'breakup', 'colleague_talk', 'neighbor_talk']

        if action_name == 'greeting':
            self._handle_greeting(npc_a, npc_b, time_dict)
            return

        rel_mgr.touch_relationship(npc_a.id, npc_b.id, initiator=True, is_meaningful=is_meaningful)
        rel_mgr.touch_relationship(npc_b.id, npc_a.id, initiator=False, is_meaningful=is_meaningful)

        comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
        rel_a_b = rel_mgr.get_relationship(npc_a.id, npc_b.id)
        rel_b_a = rel_mgr.get_relationship(npc_b.id, npc_a.id)
        context_b_a = self.simulation.memory_manager.get_context_score(npc_b.id, npc_a.id)
        context_a_b = self.simulation.memory_manager.get_context_score(npc_a.id, npc_b.id)

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
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', get_gain(3.0, rel_b_a['affinity'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', get_gain(1.5, rel_b_a['familiarity'], rel_b_a))
                if success_b >= 0 and (comp >= -0.3 or rel_b_a['affinity'] > 10):
                    rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', get_gain(0.35, rel_b_a['trust'], rel_b_a))
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 1.0)

            aff_factor_a = max(-15, rel_a_b['affinity']) * 0.1
            ctx_a = max(-2.0, context_a_b)
            olive_branch_b = (npc_b.traits.get('friendliness', 0) + npc_b.traits.get('empathy', 0)) * 5.0

            success_a = aff_factor_a + (comp * 5) + olive_branch_b + (success_b * 0.2) + (ctx_a * 2.0)
            if success_a >= -5:
                relief_a = 2.0 + (npc_a.traits.get('empathy', 0) * 2.0) + (success_a * 0.2) + (max(0, rel_a_b['trust']) * 0.05)
                if rel_a_b['tension'] > 0: rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -max(1.0, relief_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', get_gain(3.0, rel_a_b['affinity'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', get_gain(1.5, rel_a_b['familiarity'], rel_a_b))
                if success_a >= 0 and (comp >= -0.3 or rel_a_b['affinity'] > 10):
                    rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', get_gain(0.35, rel_a_b['trust'], rel_a_b))
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.0)

            # Check Friendship Milestone
            rel_curr_a = rel_mgr.get_relationship(npc_a.id, npc_b.id)
            rel_curr_b = rel_mgr.get_relationship(npc_b.id, npc_a.id)
            if rel_curr_a['affinity'] >= 40 and rel_curr_b['affinity'] >= 40:
                mem_a = self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Дружба", f"Стали хорошими друзьями с {npc_b.first_name}", 0.6, 0.6)
                mem_b = self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Дружба", f"Стали хорошими друзьями с {npc_a.first_name}", 0.6, 0.6)
                if mem_a:
                    from living_world.engine.observer.world_event import EventType, EventImportance
                    if hasattr(self.simulation, 'event_aggregator'):
                        self.simulation.event_aggregator.publish_event(
                            event_type=EventType.FRIENDSHIP_START,
                            importance=EventImportance.MEDIUM,
                            message=f"{npc_a.get_full_name()} и {npc_b.get_full_name()} стали хорошими друзьями.",
                            participants=[npc_a.id, npc_b.id]
                        )

            self._check_spark(npc_a, npc_b, comp, success_b, success_a, is_deep_talk=False)

        elif action_name == 'deep_talk':
            success_b = (rel_b_a['affinity'] * 0.25) + (comp * 10) + (npc_a.traits.get('friendliness',0) * 5) - (rel_b_a['tension'] * 0.3) + (context_b_a * 4.0)
            if success_b > 0:
                relief_b = 4.0 + (npc_b.traits.get('empathy', 0) * 2.0) + (success_b * 0.2) + (rel_b_a['trust'] * 0.1)
                if rel_b_a['tension'] > 0: rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -max(1.0, relief_b))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', get_gain(5.0, rel_b_a['affinity'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', get_gain(3.5, rel_b_a['trust'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', get_gain(2.5, rel_b_a['familiarity'], rel_b_a))
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 1.5)

            success_a = (rel_a_b['affinity'] * 0.25) + (comp * 10) + (npc_b.traits.get('friendliness',0) * 5) + (success_b * 0.5) + (context_a_b * 4.0)
            if success_a > 0:
                relief_a = 4.0 + (npc_a.traits.get('empathy', 0) * 2.0) + (success_a * 0.2) + (rel_a_b['trust'] * 0.1)
                if rel_a_b['tension'] > 0: rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -max(1.0, relief_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', get_gain(5.0, rel_a_b['affinity'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', get_gain(3.5, rel_a_b['trust'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', get_gain(2.5, rel_a_b['familiarity'], rel_a_b))
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.5)

            if success_b > 0 and success_a > 0:
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Душевный разговор", f"Искренний разговор с {npc_b.first_name}", 0.4, 0.5)
                self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Душевный разговор", f"Искренний разговор с {npc_a.first_name}", 0.4, 0.5)

            # Check Friendship Milestone
            rel_curr_a = rel_mgr.get_relationship(npc_a.id, npc_b.id)
            rel_curr_b = rel_mgr.get_relationship(npc_b.id, npc_a.id)
            if rel_curr_a['affinity'] >= 40 and rel_curr_b['affinity'] >= 40:
                mem_a = self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Дружба", f"Стали хорошими друзьями с {npc_b.first_name}", 0.6, 0.6)
                mem_b = self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Дружба", f"Стали хорошими друзьями с {npc_a.first_name}", 0.6, 0.6)
                if mem_a:
                    from living_world.engine.observer.world_event import EventType, EventImportance
                    if hasattr(self.simulation, 'event_aggregator'):
                        self.simulation.event_aggregator.publish_event(
                            event_type=EventType.FRIENDSHIP_START,
                            importance=EventImportance.MEDIUM,
                            message=f"{npc_a.get_full_name()} и {npc_b.get_full_name()} стали хорошими друзьями.",
                            participants=[npc_a.id, npc_b.id]
                        )

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

            is_major = (rel_b_a['tension'] > 60 or rel_a_b['tension'] > 60)
            sig = 0.5 if is_major else 0.2
            val = -0.5 if is_major else -0.25
            event_title = "Семейный конфликт" if is_family_conflict else "Бытовой конфликт"

            mem_b = self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, event_title, f"{event_title} с {npc_a.first_name}", sig, val)
            mem_a = self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, event_title, f"{event_title} с {npc_b.first_name}", sig, val)

            # If memory generation was skipped due to cooldown, do NOT apply runaway penalties
            if mem_a is None and mem_b is None:
                return

            if rel_b_a['tension'] < 80:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 3.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', -get_gain(0.8, rel_b_a['trust'], rel_b_a))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -get_gain(2.0, rel_b_a['affinity'], rel_b_a))
            else:
                # Discharge tension (runaway loop breaker)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -15.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -get_gain(0.8, rel_b_a['affinity'], rel_b_a))

            if rel_a_b['tension'] < 80:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 3.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -get_gain(0.8, rel_a_b['trust'], rel_a_b))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', -get_gain(2.0, rel_a_b['affinity'], rel_a_b))
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -15.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', -get_gain(0.8, rel_a_b['affinity'], rel_a_b))

            if is_household_conflict:
                from living_world.engine.observer.world_event import EventType, EventImportance
                if hasattr(self.simulation, 'event_aggregator'):
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.CONFLICT_MAJOR if is_major else EventType.CONFLICT_MINOR,
                        importance=EventImportance.HIGH if is_major else EventImportance.LOW,
                        message=f"{event_title} между {npc_a.first_name} и {npc_b.first_name}.",
                        participants=[npc_a.id, npc_b.id, household_id],
                        data={"conflict_type": event_title}
                    )
                bus.publish("family_conflict", {"household_id": household_id, "npc_a": npc_a, "npc_b": npc_b})

        elif action_name == 'flirt':
            # Monogamy check
            if npc_b.family_id is not None or (getattr(npc_b, 'dating_partner_id', None) is not None and npc_b.dating_partner_id != npc_a.id):
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -1.0)
                return

            success_b = (rel_b_a['affinity'] * 0.3) + (rel_b_a['romantic_interest'] * 0.4) + (comp * 10) - (rel_b_a['tension'] * 0.3) + (context_b_a * 3.0)
            if success_b >= 0:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', get_gain(4.5, rel_a_b['romantic_interest'], rel_a_b))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', get_gain(4.0, rel_b_a['romantic_interest'], rel_b_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', get_gain(2.5, rel_a_b['affinity'], rel_a_b))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', get_gain(2.5, rel_b_a['affinity'], rel_b_a))
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', get_gain(1.5, rel_a_b['familiarity'], rel_a_b))
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', get_gain(1.5, rel_b_a['familiarity'], rel_b_a))
                if rel_a_b['tension'] > 0: rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -1.0)
                if rel_b_a['tension'] > 0: rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -1.0)

                # Form Dating relationship if mutual romance reaches 30
                rel_a_b_curr = rel_mgr.get_relationship(npc_a.id, npc_b.id)
                rel_b_a_curr = rel_mgr.get_relationship(npc_b.id, npc_a.id)
                if (rel_a_b_curr['romantic_interest'] >= 30 and rel_b_a_curr['romantic_interest'] >= 30 and
                    getattr(npc_a, 'dating_partner_id', None) is None and getattr(npc_b, 'dating_partner_id', None) is None and
                    npc_a.family_id is None and npc_b.family_id is None):
                    npc_a.dating_partner_id = npc_b.id
                    npc_b.dating_partner_id = npc_a.id

                    self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Начало отношений", f"Начал(а) встречаться с {npc_b.first_name}", 0.8, 0.9)
                    self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Начало отношений", f"Начал(а) встречаться с {npc_a.first_name}", 0.8, 0.9)

                    from living_world.engine.observer.world_event import EventType, EventImportance
                    if hasattr(self.simulation, 'event_aggregator'):
                        self.simulation.event_aggregator.publish_event(
                            event_type=EventType.RELATIONSHIP_START,
                            importance=EventImportance.HIGH,
                            message=f"{npc_a.get_full_name()} и {npc_b.get_full_name()} начали встречаться!",
                            participants=[npc_a.id, npc_b.id]
                        )
                elif success_b > 15 and random.random() < 0.25:
                    self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Флирт", f"Приятный флирт с {npc_a.first_name}", 0.4, 0.6)
                    self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Флирт", f"Приятный флирт с {npc_b.first_name}", 0.4, 0.6)
            else:
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 1.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', -0.2)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 1.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -1.0)

        elif action_name == 'propose':
            inclination_b = (npc_b.traits.get('friendliness', 0) + npc_b.traits.get('empathy', 0) + npc_b.traits.get('sociability', 0) - npc_b.traits.get('boldness', 0) * 0.3) / 3.0
            success_b = False
            if rel_b_a['romantic_interest'] >= 45 and rel_b_a['trust'] >= 30 and rel_b_a['tension'] < 40:
                accept_chance = 0.7 + (inclination_b * 0.25) + (rel_b_a['romantic_interest'] - 45) * 0.01 + (context_b_a * 0.1)
                if random.random() < accept_chance: success_b = True

            if success_b:
                npc_a.dating_partner_id = None
                npc_b.dating_partner_id = None
                self.simulation.family_manager.create_family(npc_a, npc_b, time_dict)
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 6.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -3.0)
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Отказ", f"{npc_b.first_name} пока не готов(а) к браку", 0.5, -0.3)

        elif action_name == 'divorce':
            self.simulation.family_manager.divorce_family(npc_a, npc_b, time_dict)

            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 40.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', -30.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 40.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', -30.0)

            self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Развод", f"Развелся с {npc_b.first_name}", 1.0, -1.0)
            self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Развод", f"Развелся с {npc_a.first_name}", 1.0, -1.0)

        elif action_name == 'apology':
            comp = CompatibilityManager.calculate_compatibility(npc_a, npc_b)
            accept_chance = 0.75 + (npc_b.traits.get('empathy', 0) * 0.2) + (npc_a.traits.get('empathy', 0) * 0.1) + (comp * 0.1)
            accept_chance = max(0.2, min(1.0, accept_chance))
            if accept_chance >= 0.95:
                accept_chance = 1.0
            if random.random() < accept_chance:
                relief = 20.0 + (npc_a.traits.get('empathy', 0) * 5.0)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -relief)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -relief)
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 4.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 4.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', 3.0)
                npc_a.mood = min(100.0, npc_a.mood + 5.0)
                npc_b.mood = min(100.0, npc_b.mood + 5.0)

                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Примирение", f"Помирился с {npc_b.first_name}", 0.4, 0.5)
                self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Примирение", f"Принял(а) извинения {npc_a.first_name}", 0.4, 0.5)

                from living_world.engine.observer.world_event import EventType, EventImportance
                if hasattr(self.simulation, 'event_aggregator'):
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.SOCIAL_INTERACTION,
                        importance=EventImportance.LOW,
                        message=f"{npc_a.get_full_name()} принес(ла) извинения {npc_b.get_full_name()}, разногласия улажены.",
                        participants=[npc_a.id, npc_b.id]
                    )
            else:
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 2.0)

        elif action_name == 'help_or_gift':
            gift_sum = 500.0
            if npc_a.money >= gift_sum:
                npc_a.money -= gift_sum
                npc_b.money += gift_sum
                rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 4.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 8.0)
                rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', 5.0)
                if rel_b_a['tension'] > 0:
                    rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -5.0)
                npc_b.mood = min(100.0, npc_b.mood + 8.0)

                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Помощь", f"Оказал(а) поддержку {npc_b.first_name}", 0.4, 0.5)
                self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Помощь", f"{npc_a.first_name} выручил(а) в нужный момент", 0.5, 0.7)

                from living_world.engine.observer.world_event import EventType, EventImportance
                if hasattr(self.simulation, 'event_aggregator'):
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.ECONOMIC,
                        importance=EventImportance.LOW,
                        message=f"{npc_a.get_full_name()} оказал(а) материальную поддержку {npc_b.get_full_name()}.",
                        participants=[npc_a.id, npc_b.id]
                    )

        elif action_name == 'breakup':
            npc_a.dating_partner_id = None
            npc_b.dating_partner_id = None
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 15.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', 15.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', -20.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', -20.0)

            self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Расставание", f"Расстался(лась) с {npc_b.first_name}", 0.7, -0.6)
            self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Расставание", f"Расстался(лась) с {npc_a.first_name}", 0.7, -0.6)

            from living_world.engine.observer.world_event import EventType, EventImportance
            if hasattr(self.simulation, 'event_aggregator'):
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.RELATIONSHIP_END,
                    importance=EventImportance.MEDIUM,
                    message=f"Пара {npc_a.get_full_name()} и {npc_b.get_full_name()} распалась.",
                    participants=[npc_a.id, npc_b.id]
                )

    def _check_spark(self, npc_a, npc_b, comp, success_b, success_a, is_deep_talk=False):
        current_date = self.simulation.time.current_datetime
        if npc_a.get_age(current_date) < 18 or npc_b.get_age(current_date) < 18: return
        if npc_a.gender == npc_b.gender: return
        if npc_a.family_id is not None or npc_b.family_id is not None: return
        if npc_a.dating_partner_id not in [None, npc_b.id] or npc_b.dating_partner_id not in [None, npc_a.id]: return

        base_chance = 0.25 if is_deep_talk else 0.12

        spark_happened = False

        if success_b > 0:
            chance_b = base_chance * max(0.25, (comp + 1.0) / 2.0)
            if random.random() < chance_b:
                cur_rom_b = self.simulation.relationship_manager.get_relationship(npc_b.id, npc_a.id)['romantic_interest']
                if cur_rom_b < 20:
                    self.simulation.relationship_manager.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', random.uniform(15.0, 25.0))
                    spark_happened = True

        if success_a > 0:
            chance_a = base_chance * max(0.25, (comp + 1.0) / 2.0)
            if random.random() < chance_a:
                cur_rom_a = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)['romantic_interest']
                if cur_rom_a < 20:
                    self.simulation.relationship_manager.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', random.uniform(15.0, 25.0))
                    spark_happened = True

        if spark_happened:
            from living_world.engine.observer.world_event import EventType, EventImportance
            if hasattr(self.simulation, 'event_aggregator'):
                rel_ab = self.simulation.relationship_manager.get_relationship(npc_a.id, npc_b.id)
                if rel_ab['romantic_interest'] < 30:
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

        mem_a = self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Знакомство", f"Познакомился с {npc_b.first_name}", 0.3, 0.2)
        self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Знакомство", f"Познакомился с {npc_a.first_name}", 0.3, 0.2)

        if mem_a:
            from living_world.engine.observer.world_event import EventType, EventImportance
            if hasattr(self.simulation, 'event_aggregator'):
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.SOCIAL_INTERACTION,
                    importance=EventImportance.MEDIUM,
                    message=f"{npc_a.get_full_name()} и {npc_b.get_full_name()} познакомились.",
                    participants=[npc_a.id, npc_b.id]
                )

        elif action_name == 'colleague_talk':
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', 2.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', 2.0)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'trust', 1.5)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'trust', 1.5)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 1.5)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 1.5)
            npc_a.mood = min(100.0, npc_a.mood + 1.0)
            npc_b.mood = min(100.0, npc_b.mood + 1.0)
            if random.random() < 0.25:
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Работа", f"Обсудили рабочие вопросы с коллегой {npc_b.first_name}", 0.3, 0.4)
                self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Работа", f"Обсудили рабочие вопросы с коллегой {npc_a.first_name}", 0.3, 0.4)

        elif action_name == 'neighbor_talk':
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'familiarity', 1.8)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'familiarity', 1.8)
            rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', 2.0)
            rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'affinity', 2.0)
            if rel_a_b['tension'] > 0: rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', -1.5)
            if rel_b_a['tension'] > 0: rel_mgr.modify_relationship(npc_b.id, npc_a.id, 'tension', -1.5)
            if random.random() < 0.25:
                self.simulation.memory_manager.add_memory(npc_a.id, npc_b.id, "Соседи", f"Приветливый разговор с соседом {npc_b.first_name}", 0.3, 0.4)
                self.simulation.memory_manager.add_memory(npc_b.id, npc_a.id, "Соседи", f"Приветливый разговор с соседом {npc_a.first_name}", 0.3, 0.4)
