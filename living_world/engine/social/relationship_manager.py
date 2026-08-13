from living_world.engine.event_bus import bus
import math

class RelationshipManager:
    def __init__(self, simulation):
        self.simulation = simulation
        # A dictionary mapping (source_npc_id, target_npc_id) -> relationship dict
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
                'last_interaction_time': self.simulation.time.get_total_minutes()
            }

        rel = self.relationships[key]
        return self._apply_lazy_decay(rel, source_id)

    def _apply_lazy_decay(self, rel_dict, source_id):
        current_time = self.simulation.time.get_total_minutes()
        last_time = rel_dict.get('last_interaction_time', current_time)

        days_passed = (current_time - last_time) / (24 * 60.0)
        if days_passed <= 0:
            return rel_dict.copy()

        decayed_rel = rel_dict.copy()

                # Tension decays quickly
        decayed_rel['tension'] *= math.pow(0.85, days_passed)

        # Get source and target NPCs for trait-based decay
        source_npc = next((n for n in self.simulation.npcs if n.id == source_id), None)
        target_npc = next((n for n in self.simulation.npcs if n.id == rel_dict['target_npc_id']), None)

        # Romantic Interest decay
        # Depends on traits of the source NPC and whether it's mutual active connection
        romance_decay_rate = 0.95 # Base rate
        if source_npc:
            # Bold people might move on faster if no action, patient people hold on longer
            romance_decay_rate = 0.95 - (source_npc.traits.get('boldness', 0) * 0.02) + (source_npc.traits.get('patience', 0) * 0.02)

        # Check mutual romance to slow down decay
        # To avoid infinite recursion, we just check the raw dict if it exists
        reverse_key = (rel_dict['target_npc_id'], source_id)
        if reverse_key in self.relationships:
            rev_rel = self.relationships[reverse_key]
            if rev_rel['romantic_interest'] > 40 and decayed_rel['romantic_interest'] > 40:
                romance_decay_rate += 0.03 # Mutual strong romance decays much slower

        romance_decay_rate = max(0.80, min(0.995, romance_decay_rate))
        decayed_rel['romantic_interest'] *= math.pow(romance_decay_rate, days_passed)

        # Affinity non-linear decay
        # No artificial 40 limit. Everything tends to 0.
        # But deep relationships decay much slower.
        current_aff = decayed_rel['affinity']
        # If affinity is 100, rate is 0.995. If affinity is 0, rate is 0.95.
        aff_decay_rate = 0.95 + (abs(current_aff) / 100.0) * 0.045
        decayed_rel['affinity'] *= math.pow(aff_decay_rate, days_passed)

        # Trust decays extremely slowly
        current_trust = decayed_rel['trust']
        trust_decay_rate = 0.97 + (abs(current_trust) / 100.0) * 0.025
        decayed_rel['trust'] *= math.pow(trust_decay_rate, days_passed)

        # Familiarity doesn't decay

        return decayed_rel

    def get_all_relationships_for(self, source_id):
        # We need to return decayed versions for the UI
        rels = []
        for (src, _), rel in self.relationships.items():
            if src == source_id:
                rels.append(self._apply_lazy_decay(rel, source_id))
        return rels

    def modify_relationship(self, source_id, target_id, axis, delta):
        # First, apply decay up to now, so we modify the *current* real value
        rel_decayed = self.get_relationship(source_id, target_id)

        # Now update the real storage with the decayed values
        key = (source_id, target_id)
        self.relationships[key] = rel_decayed
        rel = self.relationships[key]

        # Apply delta
        old_val = rel[axis]
        if axis == 'familiarity':
            rel[axis] = max(0.0, min(100.0, old_val + delta))
        elif axis in ['affinity', 'trust', 'respect', 'romantic_interest']:
            rel[axis] = max(-100.0, min(100.0, old_val + delta))
        elif axis == 'tension':
             rel[axis] = max(0.0, min(100.0, old_val + delta))

        # Update timestamp to now, preventing immediate re-decay
        rel['last_interaction_time'] = self.simulation.time.get_total_minutes()

        return rel[axis]

    def touch_relationship(self, source_id, target_id):
        # Just update the timestamp after applying decay
        rel_decayed = self.get_relationship(source_id, target_id)
        key = (source_id, target_id)
        self.relationships[key] = rel_decayed
        self.relationships[key]['last_interaction_time'] = self.simulation.time.get_total_minutes()

    def load_relationships(self, loaded_relationships):
        self.relationships.clear()
        for rel in loaded_relationships:
            key = (rel['source_npc_id'], rel['target_npc_id'])
            # Copy all fields except 'id' if it exists
            rel_data = {k: v for k, v in rel.items() if k != 'id'}
            self.relationships[key] = rel_data

    def get_all_relationships(self):
        # Return raw relationships for saving
        return list(self.relationships.values())
