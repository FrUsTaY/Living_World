class CompatibilityManager:
    @staticmethod
    def calculate_compatibility(npc_a, npc_b):
        """
        Calculates a baseline compatibility modifier between -1.0 and 1.0
        based on the traits of both NPCs.
        """
        if not hasattr(npc_a, 'traits') or not hasattr(npc_b, 'traits'):
            return 0.0

        traits_a = npc_a.traits
        traits_b = npc_b.traits

        score = 0.0

        # Sociability synergy (two sociable people like each other more, introverts might clash or just be neutral)
        score += (traits_a['sociability'] * traits_b['sociability']) * 0.2

        # Friendliness synergy
        score += (traits_a['friendliness'] * traits_b['friendliness']) * 0.3

        # Empathy vs Conflict (Empathy can absorb some conflict, but double conflict is bad)
        conflict_synergy = (traits_a['conflict'] * traits_b['conflict'])
        if conflict_synergy > 0: # both are high conflict
            score -= conflict_synergy * 0.4

        # Empathy helps smooth things over
        score += ((traits_a['empathy'] + traits_b['empathy']) / 2) * 0.2

        # Patience vs Conflict
        score += (traits_a['patience'] * traits_b['conflict'] * -0.1) # B is conflicting, A is patient
        score += (traits_b['patience'] * traits_a['conflict'] * -0.1)

        # Clamp between -1.0 and 1.0
        return max(-1.0, min(1.0, score))
