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

        self.flow_friendships_created = 0
        self.flow_friendships_lost = 0
        self.flow_enmities_created = 0
        self.flow_enmities_resolved = 0
        self.flow_romances_started = 0
        self.flow_romances_ended = 0

        self.prev_friendships = set()
        self.prev_enmities = set()
        self.prev_romances = set()

        self.prev_affinities = {}

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

        report_interval_days = max(1, self.total_days // 10)
        report_interval_mins = report_interval_days * 24 * 60

        next_report = report_interval_mins

        self.report_log = []

        for i in range(total_minutes):
            self.sim.update()

            if (i + 1) >= next_report:
                self.print_stats()
                next_report += report_interval_mins

        self.print_final_report()
        self.ask_save()

    def print_stats(self):
        header = f"--- INTERIM REPORT: {self._format_time()} ---"
        print(f"\n{header}")
        self.report_log.append(header)
        self._calculate_and_print_metrics()
        footer = "------------------------------------"
        print(f"{footer}\n")
        self.report_log.append(footer)
        self.report_log.append("")

    def print_final_report(self):
        header1 = "===================================="
        header2 = "====== FINAL DIAGNOSTIC REPORT ====="
        header3 = "===================================="
        time_elapsed = f"Time Elapsed: {self._format_time()}"

        print(f"\n{header1}\n{header2}\n{header3}\n{time_elapsed}")

        self.report_log.append(header1)
        self.report_log.append(header2)
        self.report_log.append(header3)
        self.report_log.append(time_elapsed)

        self._calculate_and_print_metrics()

    def ask_save(self):
        while True:
            choice = input("Сохранить диагностический отчет в .md файл? (y/n): ").strip().lower()
            if choice == 'y':
                filename = f"social_report_{self.total_days}days.md"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for line in self.report_log:
                            f.write(line + "\n")
                    print(f"Отчет сохранен в файл {filename}")
                except Exception as e:
                    print(f"Ошибка при сохранении: {e}")
                break
            elif choice == 'n':
                break


    def _calculate_and_print_metrics(self):
        npcs = self.sim.npcs
        total_npcs = len(npcs)

        friends = 0
        enemies = 0
        conflicts = 0
        one_way_romance = 0
        mutual_romance = 0

        familiar_counts = {npc.id: 0 for npc in npcs}
        isolated_npcs = total_npcs
        processed_pairs = set()

        curr_friendships = set()
        curr_enmities = set()
        curr_romances = set()

        for npc in npcs:
            rels = self.sim.relationship_manager.get_all_relationships_for(npc.id)
            if len(rels) > 0:
                has_familiar = any(r['familiarity'] > 0 for r in rels)
                if has_familiar: isolated_npcs -= 1

            for rel in rels:
                if rel['familiarity'] == 0: continue
                familiar_counts[npc.id] += 1

                target_id = rel['target_npc_id']
                pair_key = tuple(sorted([npc.id, target_id]))

                rev_rel = next((r for r in self.sim.relationship_manager.get_all_relationships_for(target_id) if r['target_npc_id'] == npc.id), None)
                aff_a = rel['affinity']
                aff_b = rev_rel['affinity'] if rev_rel else 0
                ten_a = rel['tension']
                ten_b = rev_rel['tension'] if rev_rel else 0
                rom_a = rel['romantic_interest']
                rom_b = rev_rel['romantic_interest'] if rev_rel else 0

                # Check transitions for logging
                if self.log_events:
                    key_a_b = (npc.id, target_id)
                    prev_aff = self.prev_affinities.get(key_a_b, 0.0)
                    if prev_aff < 40 and aff_a >= 40:
                        target_name = next((n.first_name for n in npcs if n.id == target_id), "Unknown")
                        print(f"\n{self._format_time()}: [TRANSITION] {npc.first_name} + {target_name}: Friendship Created (Affinity {prev_aff:.1f} -> {aff_a:.1f})")
                    elif prev_aff >= 40 and aff_a < 40:
                        target_name = next((n.first_name for n in npcs if n.id == target_id), "Unknown")
                        print(f"\n{self._format_time()}: [TRANSITION] {npc.first_name} + {target_name}: Friendship Lost (Affinity {prev_aff:.1f} -> {aff_a:.1f})")
                    self.prev_affinities[key_a_b] = aff_a


                if rom_a > 40:
                    if rev_rel and rom_b > 40:
                        if pair_key not in processed_pairs:
                            mutual_romance += 1
                            curr_romances.add(pair_key)
                    else:
                        one_way_romance += 1

                if pair_key not in processed_pairs:
                    if aff_a > 40 and aff_b > 40:
                        friends += 1
                        curr_friendships.add(pair_key)
                    elif aff_a < -40 or aff_b < -40:
                        enemies += 1
                        curr_enmities.add(pair_key)

                    if ten_a > 50 or ten_b > 50:
                        conflicts += 1

                    processed_pairs.add(pair_key)

        # Calculate Flow Deltas
        new_friends = curr_friendships - self.prev_friendships
        lost_friends = self.prev_friendships - curr_friendships
        self.flow_friendships_created += len(new_friends)
        self.flow_friendships_lost += len(lost_friends)

        new_enmities = curr_enmities - self.prev_enmities
        resolved_enmities = self.prev_enmities - curr_enmities
        self.flow_enmities_created += len(new_enmities)
        self.flow_enmities_resolved += len(resolved_enmities)

        new_romances = curr_romances - self.prev_romances
        ended_romances = self.prev_romances - curr_romances
        self.flow_romances_started += len(new_romances)
        self.flow_romances_ended += len(ended_romances)

        # Warnings
        warning_msg = ""
        # Check monotonic growth (just a simple check if it only grows and never loses and is > 10)
        if len(new_friends) > 0 and len(lost_friends) == 0 and len(curr_friendships) > 10:
            self.consecutive_friend_growth = getattr(self, 'consecutive_friend_growth', 0) + 1
        elif len(lost_friends) > 0:
            self.consecutive_friend_growth = 0

        if getattr(self, 'consecutive_friend_growth', 0) >= 3:
            warning_msg = "! WARNING: MONOTONIC GROWTH DETECTED (Friendships only grew for 3+ snapshots, no turnover)."


        self.prev_friendships = curr_friendships
        self.prev_enmities = curr_enmities
        self.prev_romances = curr_romances

        total_memories = len(self.sim.memory_manager.get_all_memories())
        families = len(getattr(self.sim, 'families', []))

        counts = list(familiar_counts.values())
        avg_fam = sum(counts) / total_npcs if total_npcs > 0 else 0

        metrics = [
            "[CURRENT STATE]",
            f"- Friendships Active (>40): {friends}  (Δ: +{len(new_friends)} | -{len(lost_friends)})",
            f"- Enmities Active (<-40):    {enemies}  (Δ: +{len(new_enmities)} | -{len(resolved_enmities)})",
            f"- Mutual Romances Active:   {mutual_romance}  (Δ: +{len(new_romances)} | -{len(ended_romances)})",
            f"- Active Conflicts (>50):   {conflicts}",
            "",
            "[FLOW METRICS (Total Accumulated)]",
            f"- Friendships Created:      {self.flow_friendships_created}",
            f"- Friendships Lost:         {self.flow_friendships_lost}",
            f"- Net Friendship Change:    {self.flow_friendships_created - self.flow_friendships_lost}",
            f"- Enmities Created:         {self.flow_enmities_created}",
            f"- Enmities Resolved:        {self.flow_enmities_resolved}",
            f"- Romances Started:         {self.flow_romances_started}",
            f"- Romances Ended:           {self.flow_romances_ended}",
            "",
            "[SYSTEM STATS]",
            f"- Total Memories Created:   {total_memories}",
            f"- Average familiars per NPC:{avg_fam:.1f}",
            f"- Families Active:          {sum(1 for f in getattr(self.sim, 'families', []) if f.get('is_active', 1) == 1)}",
            f"- Divorces/Breakups:        {sum(1 for f in getattr(self.sim, 'families', []) if f.get('is_active', 1) == 0)}"
        ]

        if warning_msg:
            metrics.append("")
            metrics.append(warning_msg)

        for m in metrics:
            print(m)
            self.report_log.append(m)



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
