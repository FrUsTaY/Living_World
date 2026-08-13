from living_world.engine.event_bus import bus

class RelationshipManager:
    def __init__(self):
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
                'tension': 0.0
            }
        return self.relationships[key]

    def get_all_relationships_for(self, source_id):
        return [rel for (src, _), rel in self.relationships.items() if src == source_id]

    def modify_relationship(self, source_id, target_id, axis, delta):
        rel = self.get_relationship(source_id, target_id)

        old_val = rel[axis]
        # Allow most axes to go from -100 to 100. Familiarity is 0 to 100.
        if axis == 'familiarity':
            rel[axis] = max(0.0, min(100.0, old_val + delta))
        elif axis in ['affinity', 'trust', 'respect', 'romantic_interest']:
            rel[axis] = max(-100.0, min(100.0, old_val + delta))
        elif axis == 'tension':
             rel[axis] = max(0.0, min(100.0, old_val + delta))

        # Threshold logic could be added here to trigger events,
        # e.g., if tension crosses 80, fire a "high tension" event.
        # But for now, we leave event triggering to the SocialManager.

        return rel[axis]

    def load_relationships(self, loaded_relationships):
        self.relationships.clear()
        for rel in loaded_relationships:
            key = (rel['source_npc_id'], rel['target_npc_id'])
            # Copy all fields except 'id' if it exists
            rel_data = {k: v for k, v in rel.items() if k != 'id'}
            self.relationships[key] = rel_data

    def get_all_relationships(self):
        return list(self.relationships.values())
