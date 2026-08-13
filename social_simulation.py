import argparse
import random
import sys
import logging
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.event_bus import bus

class SocialMonitor:
    def __init__(self, simulation, days, log_events=True):
        self.sim = simulation
        self.total_days = days
        self.log_events = log_events
        self.events_log = []

        if self.log_events:
            bus.subscribe("memory_created", self._on_memory)
            bus.subscribe("family_created", self._on_family)
            bus.subscribe("log_event", self._on_log)

    def _format_time(self):
        time_dict = self.sim.time.get_time_dict()
        return f"DAY {time_dict['day']}/{time_dict['hour']:02d}:{time_dict['minute']:02d}"

    def _on_memory(self, memory):
        msg = f"{self._format_time()}: [MEMORY] {memory['event_type']} - {memory['description']} (Valence: {memory['valence']:.1f})"
        self.events_log.append(msg)
        print(msg)

    def _on_family(self, family):
        msg = f"{self._format_time()}: [FAMILY] Family {family['id'][:8]} created."
        self.events_log.append(msg)
        print(msg)

    def _on_log(self, msg):
        # Filter out spammy state changes like "is now sleeping" if we only want social events
        # In current codebase, log_event is used for state changes mostly. We can ignore it or print it.
        # Let's ignore basic state changes for the social diagnostic report to keep it clean.
        pass

    def run(self):
        print(f"Starting simulation for {self.total_days} days...")
        total_minutes = self.total_days * 24 * 60

        # Determine reporting interval based on total days to avoid spam
        report_interval_days = max(1, self.total_days // 10)
        report_interval_mins = report_interval_days * 24 * 60

        next_report = report_interval_mins

        for i in range(total_minutes):
            self.sim.update()

            if (i + 1) >= next_report:
                self.print_stats()
                next_report += report_interval_mins

        self.print_final_report()

    def print_stats(self):
        print(f"\n--- INTERIM REPORT: {self._format_time()} ---")
        self._calculate_and_print_metrics()
        print("------------------------------------\n")

    def print_final_report(self):
        print("\n====================================")
        print("====== FINAL DIAGNOSTIC REPORT =====")
        print("====================================")
        print(f"Time Elapsed: {self._format_time()}")
        self._calculate_and_print_metrics()

    def _calculate_and_print_metrics(self):
        npcs = self.sim.npcs
        total_npcs = len(npcs)

        # Get all relationships directly (raw) and apply lazy decay to measure current state
        # We'll use get_all_relationships_for for each NPC to ensure we get decayed values

        friends = 0
        enemies = 0
        conflicts = 0
        one_way_romance = 0
        mutual_romance = 0

        familiar_counts = {npc.id: 0 for npc in npcs}
        isolated_npcs = total_npcs

        # To avoid double counting mutual relationships, keep track of pairs
        processed_pairs = set()

        for npc in npcs:
            rels = self.sim.relationship_manager.get_all_relationships_for(npc.id)
            if len(rels) > 0:
                has_familiar = any(r['familiarity'] > 0 for r in rels)
                if has_familiar:
                    isolated_npcs -= 1

            for rel in rels:
                if rel['familiarity'] == 0: continue

                familiar_counts[npc.id] += 1

                target_id = rel['target_npc_id']
                pair_key = tuple(sorted([npc.id, target_id]))

                # Romance logic
                if rel['romantic_interest'] > 40:
                    # Check mutual
                    rev_rel = next((r for r in self.sim.relationship_manager.get_all_relationships_for(target_id) if r['target_npc_id'] == npc.id), None)
                    if rev_rel and rev_rel['romantic_interest'] > 40:
                        if pair_key not in processed_pairs:
                            mutual_romance += 1
                    else:
                        one_way_romance += 1

                # Friendship / Enmity (only count unique pairs)
                if pair_key not in processed_pairs:
                    rev_rel = next((r for r in self.sim.relationship_manager.get_all_relationships_for(target_id) if r['target_npc_id'] == npc.id), None)

                    aff_a = rel['affinity']
                    aff_b = rev_rel['affinity'] if rev_rel else 0
                    ten_a = rel['tension']
                    ten_b = rev_rel['tension'] if rev_rel else 0

                    if aff_a > 40 and aff_b > 40:
                        friends += 1
                    elif aff_a < -40 or aff_b < -40:
                        enemies += 1

                    if ten_a > 50 or ten_b > 50:
                        conflicts += 1

                    processed_pairs.add(pair_key)

        total_memories = len(self.sim.memory_manager.get_all_memories())
        families = len(getattr(self.sim, 'families', []))

        counts = list(familiar_counts.values())
        avg_fam = sum(counts) / total_npcs if total_npcs > 0 else 0
        max_fam = max(counts) if counts else 0

        # Single NPCs
        singles = sum(1 for n in npcs if n.family_id is None)

        print(f"Total NPCs:                     {total_npcs}")
        print(f"Isolated NPCs (0 familiars):    {isolated_npcs}")
        print(f"Average familiars per NPC:      {avg_fam:.1f}")
        print(f"Max familiars for one NPC:      {max_fam}")
        print(f"Total Unique Known Pairs:       {len(processed_pairs)}")
        print(f"Friendships (Affinity > 40):    {friends}")
        print(f"Enmities (Affinity < -40):      {enemies}")
        print(f"Active Conflicts (Tension >50): {conflicts}")
        print(f"One-way Romance (Romance > 40): {one_way_romance}")
        print(f"Mutual Romance (Romance > 40):  {mutual_romance}")
        print(f"Families / Marriages:           {families}")
        print(f"Unmarried (Single) NPCs:        {singles}")
        print(f"Total Memories Created:         {total_memories}")

def main():
    parser = argparse.ArgumentParser(description="Living World - Social Simulation Diagnostic Tool")
    parser.add_argument('--npc', type=int, default=30, help="Number of NPCs to generate (default 30)")
    parser.add_argument('--days', type=int, default=30, help="Number of simulation days to run (default 30)")
    parser.add_argument('--seed', type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument('--speed', type=int, default=1000, help="Ignored in headless mode, runs at max speed")
    parser.add_argument('--no-log', action='store_true', help="Disable event logging to console")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    sim = Simulation()
    sim.time.paused = False

    # Generate World
    generate_initial_world(sim.city, sim, args.npc)

    monitor = SocialMonitor(sim, args.days, not args.no_log)
    monitor.run()

if __name__ == '__main__':
    main()
