import argparse
import random
import sys
import time
from collections import Counter
from datetime import datetime

from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.observer.world_event import EventType, EventImportance

def run_diagnostics_120_days(npc_count=25, days=120, seed=42):
    if seed is not None:
        random.seed(seed)

    print("=" * 70)
    print(f"      LIVING WORLD — ДИАГНОСТИЧЕСКИЙ ПРОГОН НА {days} ДНЕЙ")
    print(f"      Начальное население: {npc_count} NPC | Seed: {seed}")
    print("=" * 70)
    print("\n[*] Инициализация мира и генерация жителей...")

    sim = Simulation()
    sim.time.paused = False
    generate_initial_world(sim.city, sim, npc_count)

    # Счетчики прямых социальных действий
    action_counts = {
        'greetings': 0,
        'chats': 0,
        'deep_talks': 0,
        'flirts': 0,
        'household_conflicts': 0,
        'family_conflicts': 0,
        'proposes': 0,
        'divorces': 0
    }

    orig_resolve = sim.social_manager._resolve_action

    def tracked_resolve(action_name, npc_a, npc_b, time_dict):
        if action_name == 'greeting':
            action_counts['greetings'] += 1
        elif action_name == 'chat':
            action_counts['chats'] += 1
        elif action_name == 'deep_talk':
            action_counts['deep_talks'] += 1
        elif action_name == 'flirt':
            action_counts['flirts'] += 1
        elif action_name == 'propose':
            action_counts['proposes'] += 1
        elif action_name == 'divorce':
            action_counts['divorces'] += 1
        elif action_name == 'argue':
            hh_a = getattr(npc_a, 'household_id', None)
            hh_b = getattr(npc_b, 'household_id', None)
            is_family = False
            if hh_a and hh_a == hh_b:
                parents_a = sim.family_manager.get_parents(npc_a.id)
                parents_b = sim.family_manager.get_parents(npc_b.id)
                siblings_a = sim.family_manager.get_siblings(npc_a.id)
                if (npc_b in parents_a or npc_a in parents_b or 
                    npc_b in siblings_a or 
                    (npc_a.family_id is not None and npc_a.family_id == npc_b.family_id)):
                    is_family = True

            if is_family:
                action_counts['family_conflicts'] += 1
            else:
                action_counts['household_conflicts'] += 1

        return orig_resolve(action_name, npc_a, npc_b, time_dict)

    sim.social_manager._resolve_action = tracked_resolve

    print(f"[*] Запуск симуляции на {days} дней ({days * 24 * 60} минутных тиков)...")
    t_start = time.time()
    total_minutes = days * 24 * 60

    last_pct = -1
    for m in range(total_minutes):
        sim.update()
        pct = int(((m + 1) / total_minutes) * 100)
        if pct % 10 == 0 and pct != last_pct:
            elapsed = time.time() - t_start
            sys.stdout.write(f"\r    Прогресс: {pct}% | Симулировано дней: {(m+1)//(24*60)}/{days} | Время: {elapsed:.1f}с")
            sys.stdout.flush()
            last_pct = pct

    t_end = time.time()
    print(f"\n[+] Симуляция завершена за {t_end - t_start:.2f} сек.\n")

    # Сбор данных по жителям
    all_npcs = sim.npcs
    living_npcs = [n for n in all_npcs if n.is_alive]
    dead_npcs = [n for n in all_npcs if not n.is_alive]

    npc_name_map = {n.id: n.get_full_name() for n in all_npcs}

    # Домохозяйства
    households = list(sim.household_manager.households.values())

    # Браки
    active_families = [f for f in getattr(sim, 'families', []) if f.get('is_active', 1) == 1]

    # Dating пары
    dating_couples = set()
    for n in living_npcs:
        dp = getattr(n, 'dating_partner_id', None)
        if dp:
            pair = tuple(sorted([n.id, dp]))
            dating_couples.add(pair)

    # Отношения (дружба, романтика)
    all_rels = sim.relationship_manager.get_all_relationships()
    mutual_friends = set()
    mutual_romance = set()
    one_way_romance = set()

    for a in living_npcs:
        for b in living_npcs:
            if a.id >= b.id:
                continue
            r_ab = sim.relationship_manager.get_relationship(a.id, b.id)
            r_ba = sim.relationship_manager.get_relationship(b.id, a.id)

            if r_ab['familiarity'] == 0 and r_ba['familiarity'] == 0:
                continue

            pair = (a.id, b.id)
            if r_ab['affinity'] >= 40 and r_ba['affinity'] >= 40:
                mutual_friends.add(pair)

            if r_ab['romantic_interest'] >= 30 and r_ba['romantic_interest'] >= 30:
                mutual_romance.add(pair)
            elif r_ab['romantic_interest'] >= 20 or r_ba['romantic_interest'] >= 20:
                one_way_romance.add(pair)

    # Все события из EventJournal
    all_events = sim.event_journal.get_all_events()

    pregnancies_count = sum(1 for e in all_events if e.type == EventType.PREGNANCY)
    births_count = sum(1 for e in all_events if e.type == EventType.BIRTH)
    deaths_count = sum(1 for e in all_events if e.type == EventType.DEATH)
    divorces_count = sum(1 for e in all_events if e.type == EventType.DIVORCE)

    # =========================================================================
    # ВЫВОД РЕЗУЛЬТАТОВ
    # =========================================================================

    print("=" * 70)
    print("                      ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 70)
    print(f" 1. Общее количество жителей:          {len(all_npcs)}")
    print(f" 2. Количество живых / умерших:        {len(living_npcs)} живых / {len(dead_npcs)} умерших")
    print(f" 3. Количество домохозяйств:           {len(households)}")
    print(f" 4. Количество браков (активных):      {len(active_families)}")
    print(f" 5. Количество Dating-пар:             {len(dating_couples)}")
    print(f" 6. Количество беременностей:          {pregnancies_count}")
    print(f" 7. Количество рождений:               {births_count}")
    print(f" 8. Количество разводов:               {divorces_count}")
    print(f" 9. Количество дружеских связей:       {len(mutual_friends)} пар")
    print(f"10. Количество романтических связей:   {len(mutual_romance)} взаимных, {len(one_way_romance)} односторонних")
    print(f"11. Количество знакомств:              {action_counts['greetings']}")
    print(f"12. Количество deep_talk:              {action_counts['deep_talks']}")
    print(f"13. Количество флиртов:                {action_counts['flirts']}")
    print(f"14. Количество бытовых конфликтов:     {action_counts['household_conflicts']}")
    print(f"15. Количество семейных конфликтов:    {action_counts['family_conflicts']}")
    print(f"16. Количество смертей:                {deaths_count}")
    print("=" * 70)

    # =========================================================================
    # АНАЛИЗ EVENT JOURNAL
    # =========================================================================

    importance_counts = Counter(e.importance.name for e in all_events)
    type_counts = Counter(e.type.name for e in all_events)

    print("\n" + "=" * 70)
    print("                  АНАЛИЗ EVENT JOURNAL (ВСЯ ИСТОРИЯ)")
    print("=" * 70)
    print(f"Общее количество событий (WorldEvent): {len(all_events)}")
    print("\n--- Распределение по уровням важности (Importance) ---")
    for imp in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
        cnt = importance_counts.get(imp, 0)
        pct = (cnt / len(all_events) * 100) if all_events else 0
        print(f"  • {imp:<10}: {cnt:>6} ({pct:>5.1f}%)")

    print("\n--- Распределение по типам событий (EventType) ---")
    for ev_type, cnt in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (cnt / len(all_events) * 100) if all_events else 0
        print(f"  • {ev_type:<25}: {cnt:>6} ({pct:>5.1f}%)")
    print("=" * 70)

    # =========================================================================
    # ХРОНОЛОГИЯ HIGH И CRITICAL СОБЫТИЙ
    # =========================================================================

    high_critical_events = [e for e in all_events if e.importance in (EventImportance.HIGH, EventImportance.CRITICAL)]

    print("\n" + "=" * 70)
    print(f"     ХРОНОЛОГИЯ СОБЫТИЙ HIGH И CRITICAL ({len(high_critical_events)} событий)")
    print("=" * 70)

    if not high_critical_events:
        print("  (Событий уровней HIGH и CRITICAL не зафиксировано)")
    else:
        for idx, ev in enumerate(high_critical_events, 1):
            participant_names = []
            for p_id in ev.participants:
                if p_id in npc_name_map:
                    participant_names.append(npc_name_map[p_id])
                elif p_id in sim.household_manager.households:
                    participant_names.append(f"Домохозяйство {p_id[:6]}")
                else:
                    participant_names.append(p_id[:8])

            participants_str = ", ".join(participant_names) if participant_names else "Все жители"
            imp_badge = "[CRITICAL]" if ev.importance == EventImportance.CRITICAL else "[HIGH]"
            print(f"{idx:>3}. {ev.timestamp} {imp_badge:<10} [{ev.type.name}] | Участники: {participants_str}")
            print(f"     -> {ev.message}")

    # =========================================================================
    # КЛЮЧЕВЫЕ ЖИЗНЕННЫЕ ВЕХИ
    # =========================================================================

    key_types = {
        EventType.RELATIONSHIP_START: "НАЧАЛО ОТНОШЕНИЙ",
        EventType.FAMILY_CREATED: "БРАКИ И СОЗДАНИЕ СЕМЕЙ",
        EventType.MARRIAGE: "СВАДЬБЫ",
        EventType.PREGNANCY: "БЕРЕМЕННОСТИ",
        EventType.BIRTH: "РОЖДЕНИЯ ДЕТЕЙ",
        EventType.DIVORCE: "РАЗВОДЫ",
        EventType.DEATH: "СМЕРТИ"
    }

    print("\n" + "=" * 70)
    print("                  КЛЮЧЕВЫЕ ЖИЗНЕННЫЕ ВЕХИ")
    print("=" * 70)

    for target_type, title in key_types.items():
        matching = [e for e in all_events if e.type == target_type]
        print(f"\n--- {title} ({len(matching)}) ---")
        if not matching:
            print("  (Событий не происходило)")
        else:
            for ev in matching:
                p_names = [npc_name_map.get(pid, pid[:8]) for pid in ev.participants]
                p_str = ", ".join(p_names) if p_names else "-"
                print(f"  • [{ev.timestamp}] {ev.message} (Участники: {p_str})")

    print("\n" + "=" * 70)
    print("               ДИАГНОСТИЧЕСКИЙ ОТЧЕТ ЗАВЕРШЕН")
    print("=" * 70)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Living World - 120 Days Diagnostic Run")
    parser.add_argument('--npc', type=int, default=25, help="Initial NPC count (default: 25)")
    parser.add_argument('--days', type=int, default=120, help="Simulation duration in days (default: 120)")
    parser.add_argument('--seed', type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    run_diagnostics_120_days(npc_count=args.npc, days=args.days, seed=args.seed)
