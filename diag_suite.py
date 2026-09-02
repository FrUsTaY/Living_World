import random
import argparse
from datetime import datetime
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.observer.world_event import EventType, EventImportance

def run_diagnostic(npc_count=25, days=180, seed=42, verbose=True):
    random.seed(seed)
    sim = Simulation()
    sim.time.paused = False
    generate_initial_world(sim.city, sim, npc_count)

    stats = {
        'days': days,
        'npc_initial': npc_count,
        'greetings': 0,
        'chats': 0,
        'deep_talks': 0,
        'flirts_total': 0,
        'flirts_success': 0,
        'flirts_fail': 0,
        'dates_total': 0,
        'argues_total': 0,
        'argues_minor': 0,
        'argues_major': 0,
        'proposes_total': 0,
        'proposes_success': 0,
        'proposes_fail': 0,
        'divorces': 0,
        'sparks_total': 0,
        'sparks_one_way': 0,
        'sparks_mutual': 0,
        'actions_by_location': {
            'home': 0,
            'park': 0,
            'cafe': 0,
            'shop': 0,
            'work': 0,
            'other': 0
        },
        'inter_household_interactions': 0,
        'intra_household_interactions': 0
    }

    orig_resolve = sim.social_manager._resolve_action
    def tracked_resolve(action_name, npc_a, npc_b, time_dict):
        # Track location type
        loc = sim.city.get_building(npc_a.current_location)
        if loc:
            b_type = getattr(loc, 'b_type', 'other')
            stats['actions_by_location'][b_type] = stats['actions_by_location'].get(b_type, 0) + 1
        else:
            stats['actions_by_location']['other'] = stats['actions_by_location'].get('other', 0) + 1

        # Track household cross
        hh_a = getattr(npc_a, 'household_id', None)
        hh_b = getattr(npc_b, 'household_id', None)
        if hh_a and hh_b and hh_a == hh_b:
            stats['intra_household_interactions'] += 1
        else:
            stats['inter_household_interactions'] += 1

        if action_name == 'greeting':
            stats['greetings'] += 1
        elif action_name == 'chat':
            stats['chats'] += 1
        elif action_name == 'deep_talk':
            stats['deep_talks'] += 1
        elif action_name == 'flirt':
            stats['flirts_total'] += 1
        elif action_name == 'date':
            stats['dates_total'] += 1
        elif action_name == 'argue':
            stats['argues_total'] += 1
        elif action_name == 'propose':
            stats['proposes_total'] += 1
        elif action_name == 'divorce':
            stats['divorces'] += 1

        return orig_resolve(action_name, npc_a, npc_b, time_dict)

    sim.social_manager._resolve_action = tracked_resolve

    # Run loop
    total_minutes = days * 24 * 60
    for m in range(total_minutes):
        sim.update()

    # Collect final metrics
    living_npcs = [n for n in sim.npcs if n.is_alive]
    stats['npc_alive'] = len(living_npcs)

    # Relationships metrics
    all_rels = sim.relationship_manager.get_all_relationships()
    fams = [r['familiarity'] for r in all_rels if r['familiarity'] > 0]
    affs = [r['affinity'] for r in all_rels if r['familiarity'] > 0]
    trusts = [r['trust'] for r in all_rels if r['familiarity'] > 0]
    roms = [r['romantic_interest'] for r in all_rels if r['familiarity'] > 0]

    stats['avg_familiarity'] = sum(fams) / len(fams) if fams else 0.0
    stats['max_familiarity'] = max(fams) if fams else 0.0
    stats['familiarity_gt_30'] = sum(1 for f in fams if f > 30)

    stats['avg_affinity'] = sum(affs) / len(affs) if affs else 0.0
    stats['avg_trust'] = sum(trusts) / len(trusts) if trusts else 0.0
    stats['trust_gt_30'] = sum(1 for t in trusts if t > 30)
    stats['trust_gt_50'] = sum(1 for t in trusts if t > 50)

    # Mutual vs one-way pairs
    mutual_friends = 0
    mutual_enemies = 0
    mutual_romance = 0
    one_way_romance = 0

    checked_pairs = set()
    for a in living_npcs:
        for b in living_npcs:
            if a.id >= b.id: continue
            r_ab = sim.relationship_manager.get_relationship(a.id, b.id)
            r_ba = sim.relationship_manager.get_relationship(b.id, a.id)
            if r_ab['familiarity'] == 0 and r_ba['familiarity'] == 0: continue

            if r_ab['affinity'] > 40 and r_ba['affinity'] > 40:
                mutual_friends += 1
            elif r_ab['affinity'] < -40 or r_ba['affinity'] < -40:
                mutual_enemies += 1

            if r_ab['romantic_interest'] > 40 and r_ba['romantic_interest'] > 40:
                mutual_romance += 1
            elif r_ab['romantic_interest'] > 30 or r_ba['romantic_interest'] > 30:
                one_way_romance += 1

    stats['mutual_friends'] = mutual_friends
    stats['mutual_enemies'] = mutual_enemies
    stats['mutual_romance'] = mutual_romance
    stats['one_way_romance'] = one_way_romance

    # Dating count
    dating_pairs = set()
    for n in living_npcs:
        dp = getattr(n, 'dating_partner_id', None)
        if dp:
            dating_pairs.add(tuple(sorted([n.id, dp])))
    stats['dating_couples'] = len(dating_pairs)

    # Families & cohabiting
    stats['active_families'] = sum(1 for f in getattr(sim, 'families', []) if f.get('is_active', 1) == 1)
    cohabiting = 0
    for f in getattr(sim, 'families', []):
        if f.get('is_active', 1) == 1:
            spouses = [n for n in living_npcs if n.family_id == f['id']]
            if len(spouses) == 2 and spouses[0].home_id == spouses[1].home_id and spouses[0].household_id == spouses[1].household_id:
                cohabiting += 1
    stats['cohabiting_families'] = cohabiting

    # Reproduction
    events = sim.event_journal.get_all_events()
    stats['pregnancies'] = sum(1 for e in events if e.type == EventType.PREGNANCY)
    stats['births'] = sum(1 for e in events if e.type == EventType.BIRTH)
    stats['deaths'] = sum(1 for e in events if e.type == EventType.DEATH)

    # Memory breakdown
    mems = sim.memory_manager.get_all_memories()
    stats['memories_total'] = len(mems)
    stats['memories_positive'] = sum(1 for m in mems if m.get('valence', 0) > 0.1)
    stats['memories_negative'] = sum(1 for m in mems if m.get('valence', 0) < -0.1)
    stats['memories_neutral'] = sum(1 for m in mems if abs(m.get('valence', 0)) <= 0.1)

    # Observer events by importance
    stats['events_total'] = len(events)
    stats['events_low'] = sum(1 for e in events if e.importance == EventImportance.LOW)
    stats['events_medium'] = sum(1 for e in events if e.importance == EventImportance.MEDIUM)
    stats['events_high'] = sum(1 for e in events if e.importance == EventImportance.HIGH)
    stats['events_critical'] = sum(1 for e in events if e.importance == EventImportance.CRITICAL)

    if verbose:
        print("="*60)
        print(f"DIAGNOSTIC REPORT: {days} Days, {npc_count} Initial NPCs, Seed={seed}")
        print("="*60)
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print("="*60)

    return stats

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--npc', type=int, default=25)
    parser.add_argument('--days', type=int, default=180)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    run_diagnostic(args.npc, args.days, args.seed)
