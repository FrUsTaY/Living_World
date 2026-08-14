from living_world.engine.event_bus import bus
import math

class RelationshipManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.relationships = {}

    def get_relationship(self, source_id, target_id):
        key = (source_id, target_id)
        if key not in self.relationships:
            self.relationships[key] = {
                'source_npc_id': source_id,
                'target_npc_id': target_id,
                'familiarity': 0.0,
                'affinity': 0.0,
                'trust': 0.0,
                'respect': 0.0,
                'romantic_interest': 0.0,
                'tension': 0.0,
                'last_interaction_time': self.simulation.time.get_total_minutes(),
                'last_meaningful_interaction_time': self.simulation.time.get_total_minutes(),
                'daily_interactions_count': 0,
                'initiations_sent': 0,
                'initiations_received': 0
            }

        rel = self.relationships[key]
        return self._apply_lazy_decay(rel, source_id)

    def _apply_lazy_decay(self, rel_dict, source_id):
        current_time = self.simulation.time.get_total_minutes()
        last_contact = rel_dict.get('last_interaction_time', current_time)
        last_meaningful = rel_dict.get('last_meaningful_interaction_time', current_time)

        # Calculate daily saturation reset
        days_since_contact = (current_time - last_contact) / (24 * 60.0)

        decayed_rel = rel_dict.copy()

        if days_since_contact > 0.5: # Reset daily interactions if half a day passed
            decayed_rel['daily_interactions_count'] = 0

        days_passed_meaningful = (current_time - last_meaningful) / (24 * 60.0)

        if days_passed_meaningful <= 0 and days_since_contact <= 0:
            return decayed_rel

        target_id = rel_dict['target_npc_id']

        # Cache npcs dict for O(1) lookups if not exists
        if not hasattr(self, '_npc_cache') or self._last_npc_count != len(self.simulation.npcs):
            self._npc_cache = {n.id: n for n in self.simulation.npcs}
            self._last_npc_count = len(self.simulation.npcs)

        source_npc = self._npc_cache.get(source_id)
        target_npc = self._npc_cache.get(target_id)

        comp = 0.0
        if source_npc and target_npc:
            from living_world.engine.social.compatibility import CompatibilityManager
            comp = CompatibilityManager.calculate_compatibility(source_npc, target_npc)

        # Calculate Social Mass gracefully (avoiding full scan if possible, but keeping it simple for now)
        # To avoid O(E) scan here, we can cache active mass per NPC per tick, or just count known relationships roughly
        # For Stage 2.5, counting dict keys for source_id is much faster than full value scan.
        # 3.0 Social Mass
        # Only count links that actually exist meaningfully
        active_links = sum(1 for (s, t), r in self.relationships.items() if s == source_id and (r['affinity'] > 30 or r['affinity'] < -30 or r['trust'] > 30 or r['romantic_interest'] > 30))
        load_penalty = (active_links ** 1.8) / 40000.0


        # Calculate Reciprocity (reset monthly to track current dynamic)
        sent = rel_dict.get('initiations_sent', 0)
        recvd = rel_dict.get('initiations_received', 0)

        # If total interactions exceed a threshold, decay the counters so they represent recent history
        if sent + recvd > 20:
            rel_dict['initiations_sent'] = int(sent * 0.5)
            rel_dict['initiations_received'] = int(recvd * 0.5)
            sent = rel_dict['initiations_sent']
            recvd = rel_dict['initiations_received']

        reciprocity = recvd / max(1.0, float(sent))
        recip_penalty = 0.0
        if sent > 5 and reciprocity < 0.3:
            recip_penalty = 0.005 # Mild penalty 0.5% per day

        # TENSION DECAY (uses contact days, not meaningful)
        decayed_rel['tension'] *= math.pow(0.85, max(0, days_since_contact))

        days_passed = max(0, days_passed_meaningful)

        # ROMANTIC DECAY
        romance_decay_rate = 0.95
        if source_npc:
            romance_decay_rate = 0.96 - (source_npc.traits.get('boldness', 0) * 0.01) + (source_npc.traits.get('patience', 0) * 0.01)
            if source_npc.family_id is not None and target_npc and source_npc.family_id == target_npc.family_id:
                romance_decay_rate += 0.02 # Marriage slows decay

        reverse_key = (target_id, source_id)
        if reverse_key in self.relationships:
            rev_rel = self.relationships[reverse_key]
            if rev_rel['romantic_interest'] > 40 and decayed_rel['romantic_interest'] > 40:
                romance_decay_rate += 0.015 # Mutual romance

        romance_decay_rate = max(0.85, min(0.995, romance_decay_rate - load_penalty - recip_penalty))
        decayed_rel['romantic_interest'] *= math.pow(romance_decay_rate, days_passed)

        # AFFINITY DECAY
        # Slower decay: base 0.995 (0.5% per day). Good friends take months to decay.
        intensity = abs(decayed_rel['affinity']) / 100.0
        aff_decay_rate = 0.992 + (comp * 0.003) + (intensity * 0.003) - load_penalty - recip_penalty
        # Max limit 0.998 means even perfect friends lose 0.2% per day without contact.
        # Min limit 0.97 means the absolute fastest loss is 3% per day.
        aff_decay_rate = max(0.97, min(0.998, aff_decay_rate))
        decayed_rel['affinity'] *= math.pow(aff_decay_rate, days_passed)

        # TRUST DECAY (also based on meaningful time)
        trust_decay_rate = 0.998 # Very stable
        if decayed_rel['affinity'] < 0:
            trust_decay_rate = 0.985 # Enemies lose trust

        decayed_rel['trust'] *= math.pow(trust_decay_rate, days_passed)

        # Cleanup tails
        if abs(decayed_rel['affinity']) < 2.0:
            decayed_rel['affinity'] = 0.0
        if abs(decayed_rel['tension']) < 2.0:
            decayed_rel['tension'] = 0.0

        return decayed_rel


    def get_diminishing_returns(self, base_val, current_val):
        # As value approaches 100 or -100, gain drops significantly
        # To avoid being stuck at exactly 0 gain at 100, we ensure a minimum of 5% of base
        # But wait, python math.pow with negative base is complex, abs is used.
        factor = max(0.05, 1.0 - (abs(current_val) / 100.0)**1.5)
        return base_val * factor

    def get_all_relationships_for(self, source_id):
        rels = []
        for (src, _), rel in self.relationships.items():
            if src == source_id:
                rels.append(self._apply_lazy_decay(rel, source_id))
        return rels

    def modify_relationship(self, source_id, target_id, axis, delta):
        rel_decayed = self.get_relationship(source_id, target_id)

        key = (source_id, target_id)

        # When we save the decayed state back, we must bake it in by advancing the timestamps
        # to the current time, so the next decay calculation starts from 0 days passed.
        # Otherwise, we double-decay the same period on subsequent fetches.
        current_time = self.simulation.time.get_total_minutes()
        rel_decayed['last_interaction_time'] = current_time
        rel_decayed['last_meaningful_interaction_time'] = current_time

        self.relationships[key] = rel_decayed
        rel = self.relationships[key]

        old_val = rel[axis]
        if axis == 'familiarity':
            rel[axis] = max(0.0, min(100.0, old_val + delta))
        elif axis in ['affinity', 'trust', 'respect', 'romantic_interest']:
            rel[axis] = max(-100.0, min(100.0, old_val + delta))
        elif axis == 'tension':
             rel[axis] = max(0.0, min(100.0, old_val + delta))

        rel['last_interaction_time'] = self.simulation.time.get_total_minutes()

        return rel[axis]

    def touch_relationship(self, source_id, target_id, initiator=False, is_meaningful=False):
        rel_decayed = self.get_relationship(source_id, target_id)
        key = (source_id, target_id)
        self.relationships[key] = rel_decayed

        current_time = self.simulation.time.get_total_minutes()
        self.relationships[key]['last_interaction_time'] = current_time

        if is_meaningful:
            self.relationships[key]['last_meaningful_interaction_time'] = current_time

        self.relationships[key]['daily_interactions_count'] = self.relationships[key].get('daily_interactions_count', 0) + 1

        # To avoid KeyError from old db loads, check and initialize
        if 'initiations_sent' not in self.relationships[key]:
            self.relationships[key]['initiations_sent'] = 0
            self.relationships[key]['initiations_received'] = 0

        if initiator:
            self.relationships[key]['initiations_sent'] += 1
        else:
            self.relationships[key]['initiations_received'] += 1

    def load_relationships(self, loaded_relationships):
        self.relationships.clear()
        for rel in loaded_relationships:
            key = (rel['source_npc_id'], rel['target_npc_id'])
            rel_data = {k: v for k, v in rel.items() if k != 'id'}
            # Initialize new fields if loading old save
            if 'initiations_sent' not in rel_data:
                rel_data['initiations_sent'] = 0
                rel_data['initiations_received'] = 0
            self.relationships[key] = rel_data

    def get_all_relationships(self):
        return list(self.relationships.values())
