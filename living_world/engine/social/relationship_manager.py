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

        days_since_contact = (current_time - last_contact) / (24 * 60.0)

        decayed_rel = rel_dict.copy()

        if days_since_contact > 0.5:
            decayed_rel['daily_interactions_count'] = 0

        days_passed_meaningful = (current_time - last_meaningful) / (24 * 60.0)

        if days_passed_meaningful <= 0 and days_since_contact <= 0:
            return decayed_rel

        target_id = rel_dict['target_npc_id']

        if not hasattr(self, '_npc_cache') or self._last_npc_count != len(self.simulation.npcs):
            self._npc_cache = {n.id: n for n in self.simulation.npcs}
            self._last_npc_count = len(self.simulation.npcs)

        source_npc = self._npc_cache.get(source_id)
        target_npc = self._npc_cache.get(target_id)

        comp = 0.0
        if source_npc and target_npc:
            from living_world.engine.social.compatibility import CompatibilityManager
            comp = CompatibilityManager.calculate_compatibility(source_npc, target_npc)

        active_links = sum(1 for (s, t), r in self.relationships.items() if s == source_id and (abs(r.get('affinity', 0)) > 30 or r.get('romantic_interest', 0) > 30 or r.get('trust', 0) > 30))
        load_penalty = (active_links ** 1.8) / 40000.0

        sent = rel_dict.get('initiations_sent', 0)
        recvd = rel_dict.get('initiations_received', 0)

        if sent + recvd > 20:
            rel_dict['initiations_sent'] = int(sent * 0.5)
            rel_dict['initiations_received'] = int(recvd * 0.5)
            sent = rel_dict['initiations_sent']
            recvd = rel_dict['initiations_received']

        reciprocity = recvd / max(1.0, float(sent))
        recip_penalty = 0.0
        if sent > 5 and reciprocity < 0.3:
            recip_penalty = 0.005

        # TENSION DECAY (uses contact days, decays fast if no conflict)
        decayed_rel['tension'] *= math.pow(0.85, max(0, days_since_contact))

        days_passed = max(0, days_passed_meaningful)

        # ROMANTIC DECAY
        romance_decay_rate = 0.985 # Base 1.5% per day
        if source_npc:
            romance_decay_rate = 0.985 - (source_npc.traits.get('boldness', 0) * 0.005) + (source_npc.traits.get('patience', 0) * 0.005)
            if source_npc.family_id is not None and target_npc and source_npc.family_id == target_npc.family_id:
                romance_decay_rate += 0.012
            elif getattr(source_npc, 'dating_partner_id', None) == target_id:
                romance_decay_rate += 0.012

        reverse_key = (target_id, source_id)
        if reverse_key in self.relationships:
            rev_rel = self.relationships[reverse_key]
            if rev_rel['romantic_interest'] > 30 and decayed_rel['romantic_interest'] > 30:
                romance_decay_rate += 0.008

        romance_decay_rate = max(0.92, min(0.999, romance_decay_rate - load_penalty - recip_penalty))
        decayed_rel['romantic_interest'] *= math.pow(romance_decay_rate, days_passed)

        # AFFINITY DECAY
        intensity = abs(decayed_rel['affinity']) / 100.0
        aff_decay_rate = 0.994 + (comp * 0.002) + (intensity * 0.002) - load_penalty - recip_penalty
        aff_decay_rate = max(0.97, min(0.998, aff_decay_rate))
        decayed_rel['affinity'] *= math.pow(aff_decay_rate, days_passed)

        # TRUST DECAY
        trust_decay_rate = 0.998
        if decayed_rel['affinity'] < 0:
            trust_decay_rate = 0.985

        decayed_rel['trust'] *= math.pow(trust_decay_rate, days_passed)

        # Cleanup tails
        if abs(decayed_rel['affinity']) < 2.0:
            decayed_rel['affinity'] = 0.0
        if abs(decayed_rel['tension']) < 2.0:
            decayed_rel['tension'] = 0.0

        return decayed_rel

    def get_diminishing_returns(self, base_val, current_val):
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
            if 'initiations_sent' not in rel_data:
                rel_data['initiations_sent'] = 0
                rel_data['initiations_received'] = 0
            self.relationships[key] = rel_data

    def get_all_relationships(self):
        return list(self.relationships.values())
