import os
import sys
import io
import time
import json
from datetime import datetime, timedelta

# Set UTF-8 encoding for console output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.life_cycle_manager import LifeCycleManager, LifeStage
from living_world.engine.observer.world_event import EventType, EventImportance

CHECKPOINTS = [73, 146, 219, 292, 365]
SAVES_DIR = "saves"

def collect_metrics(sim, run_id, day):
    cur_date = sim.time.current_datetime
    alive_npcs = [n for n in sim.npcs if n.is_alive]
    dead_npcs = [n for n in sim.npcs if not n.is_alive]

    men = sum(1 for n in alive_npcs if n.gender == "М")
    women = sum(1 for n in alive_npcs if n.gender == "Ж")

    babies = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.BABY)
    children = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.CHILD)
    adults = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) in [LifeStage.YOUNG_ADULT, LifeStage.ADULT])
    elders = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.ELDER)

    dating_couples = sum(1 for n in alive_npcs if getattr(n, "dating_partner_id", None)) // 2
    families_count = len(getattr(sim, "families", []))

    total_wealth = sum(n.money for n in alive_npcs)
    avg_wealth = (total_wealth / len(alive_npcs)) if alive_npcs else 0.0

    econ_mgr = getattr(sim, "economy_manager", None)
    total_biz_capital = sum(e.budget for e in econ_mgr.enterprises.values()) if econ_mgr else 0.0
    enterprises_count = len(econ_mgr.enterprises) if econ_mgr else 0

    homes_count = len(sim.city.get_homes())
    districts_count = len(sim.city.districts)

    cm = getattr(sim, "construction_manager", None)
    active_projects = len(cm.active_projects) if cm else 0
    completed_projects = len(cm.completed_projects) if cm else 0

    # Recent significant events
    journal = getattr(sim, "event_journal", None)
    all_events = journal.get_all_events() if journal else []
    critical_events = [e.message for e in all_events if e.importance == EventImportance.CRITICAL][-5:]

    # Sample citizen names
    sample_names = [n.get_full_name() for n in alive_npcs[:5]]

    return {
        "run_id": run_id,
        "day": day,
        "date": cur_date.strftime("%d.%m.%Y"),
        "total_npcs": len(sim.npcs),
        "alive_npcs": len(alive_npcs),
        "dead_npcs": len(dead_npcs),
        "gender_ratio": f"{men}М / {women}Ж",
        "babies": babies,
        "children": children,
        "adults": adults,
        "elders": elders,
        "dating_couples": dating_couples,
        "families": families_count,
        "total_wealth": round(total_wealth, 2),
        "avg_wealth": round(avg_wealth, 2),
        "biz_capital": round(total_biz_capital, 2),
        "enterprises": enterprises_count,
        "homes": homes_count,
        "districts": districts_count,
        "completed_construction": completed_projects,
        "critical_events_count": len([e for e in all_events if e.importance == EventImportance.CRITICAL]),
        "recent_critical": critical_events,
        "sample_names": sample_names
    }

def run_simulation_365(run_id: int):
    print("\n" + "=" * 70)
    print(f"      ЗАПУСК СИМУЛЯЦИИ #{run_id} НА 365 ДНЕЙ (УСКОРЕНИЕ 1000x)")
    print("=" * 70)

    sim = Simulation()
    sim.time.paused = False
    sim.time.speed = 1000

    generate_initial_world(sim.city, sim, 25)

    os.makedirs(SAVES_DIR, exist_ok=True)
    snapshots = {}

    start_real_time = time.time()
    step_minutes = 5
    minutes_per_day = 1440
    steps_per_day = minutes_per_day // step_minutes

    current_day = 1
    next_checkpoint_idx = 0

    while current_day <= 365:
        # Advance 1 day
        for s in range(steps_per_day):
            sim.time.tick(step_minutes)
            time_dict = sim.time.get_time_dict()

            # Midnight daily events
            is_new_day = (time_dict["hour"] == 0 and time_dict["minute"] < step_minutes)
            if is_new_day:
                cur_date = sim.time.current_datetime
                # Natural death check
                for npc in sim.npcs:
                    if npc.is_alive:
                        age = npc.get_age(cur_date)
                        if LifeCycleManager.check_natural_death(age):
                            npc.is_alive = False
                            npc.date_of_death = cur_date
                            npc.state = "Умер"
                            sim.event_aggregator.publish_event(
                                event_type=EventType.DEATH,
                                importance=EventImportance.CRITICAL,
                                message=f"✝ {npc.get_full_name()} скончался в возрасте {age} лет.",
                                participants=[npc.id]
                            )
                            bus.publish("npc_died", {"npc": npc})

                sim.reproduction_manager.update()
                sim.economy_manager.daily_cycle()
                sim._process_daily_lifecycle(cur_date)
                sim.construction_manager.evaluate_city_growth()

            for npc in sim.npcs:
                if not npc.is_alive:
                    continue

                if is_new_day:
                    sim.education_manager.update_npc_education(npc, time_dict)

                # Needs decay proportional to step
                npc.hunger = max(0.0, min(100.0, npc.hunger - 0.1 * step_minutes))
                npc.energy = max(0.0, min(100.0, npc.energy - 0.05 * step_minutes))
                if npc.hunger <= 0.0 or npc.energy <= 0.0:
                    npc.health = max(0.0, getattr(npc, 'health', 100.0) - 0.1 * step_minutes)
                bio_baseline = (npc.hunger + npc.energy) / 2.0
                npc.mood = max(0.0, min(100.0, npc.mood * 0.96 + bio_baseline * 0.04))

                # Fast path for continuous states
                cur_state = npc.state
                if cur_state == "Спит" and npc.energy < 95:
                    npc.energy = min(100.0, npc.energy + 0.3 * step_minutes)
                elif cur_state == "Ест" and npc.hunger < 95:
                    npc.hunger = min(100.0, npc.hunger + 2.0 * step_minutes)
                elif cur_state == "Работает" and 8 <= time_dict["hour"] < 17 and npc.energy > 20 and npc.hunger > 25:
                    npc.energy -= 0.1 * step_minutes
                    sim.economy_manager.pay_work_wage(npc, minutes=step_minutes)
                    work_b = sim.city.get_building(npc.work_id)
                    if npc.profession == "Строитель" or (work_b and "стройк" in work_b.name.lower()):
                        sim.construction_manager.advance_construction(npc, minutes=step_minutes)
                else:
                    sim.ai_controller.choose_and_execute_action(npc, time_dict)

            sim.social_manager.process_social_ticks()

        # End of day check
        if next_checkpoint_idx < len(CHECKPOINTS) and current_day == CHECKPOINTS[next_checkpoint_idx]:
            chk_day = CHECKPOINTS[next_checkpoint_idx]
            save_name = f"run{run_id}_day_{chk_day}.db"
            save_path = os.path.join(SAVES_DIR, save_name)

            sim.save_to_file(save_path)
            metrics = collect_metrics(sim, run_id, chk_day)
            snapshots[chk_day] = metrics

            elapsed = time.time() - start_real_time
            print(f"[Сохранение {next_checkpoint_idx + 1}/5] День {chk_day:3d} сохранен в {save_name} | Население: {metrics['alive_npcs']} | Семьи: {metrics['families']} | Капитал: {metrics['total_wealth']:,.0f} руб. | Время: {elapsed:.1f}с")

            next_checkpoint_idx += 1

        current_day += 1

    total_time = time.time() - start_real_time
    print(f"[+] Симуляция #{run_id} успешно завершена за {total_time:.2f} сек. Сформировано 5 чекпоинтов.")

    sim.close()
    return snapshots

def main():
    print("=" * 70)
    print("      ТЕСТ ДИВЕРГЕНЦИИ: 2 НЕЗАВИСИМЫХ ПРОГОНА ПО 365 ДНЕЙ")
    print("      5 промежуточных чекпоинтов: 73, 146, 219, 292, 365 дней")
    print("=" * 70)

    # 1. Запуск первой симуляции
    run1_data = run_simulation_365(run_id=1)

    # 2. Небольшая пауза для полной изоляции ресурсов
    time.sleep(0.5)

    # 3. Запуск второй независимой симуляции
    run2_data = run_simulation_365(run_id=2)

    # 4. Сравнительный анализ дивергенции
    print("\n" + "=" * 70)
    print("         СРАВНИТЕЛЬНЫЙ АНАЛИЗ ДИВЕРГЕНЦИИ СИМУЛЯЦИЙ")
    print("=" * 70)

    header = f"{'Чекпоинт':<10} | {'Население (R1 / R2)':<22} | {'Семьи (R1 / R2)':<18} | {'Дома (R1 / R2)':<16} | {'Богатство жителей (R1 / R2)':<30}"
    print(header)
    print("-" * len(header))

    for day in CHECKPOINTS:
        s1 = run1_data[day]
        s2 = run2_data[day]
        pop_str = f"{s1['alive_npcs']} / {s2['alive_npcs']}"
        fam_str = f"{s1['families']} / {s2['families']}"
        homes_str = f"{s1['homes']} / {s2['homes']}"
        wealth_str = f"{s1['total_wealth']:,.0f} руб. / {s2['total_wealth']:,.0f} руб."
        print(f"День {day:<5} | {pop_str:<22} | {fam_str:<18} | {homes_str:<16} | {wealth_str:<30}")

    print("\n" + "=" * 70)
    print("ИТОГОВОЕ СОСТОЯНИЕ МИРОВ НА ДЕНЬ 365:")
    print("=" * 70)
    f1 = run1_data[365]
    f2 = run2_data[365]

    print(f"\n[МИР #1 (День 365)]:")
    print(f"  * Население: {f1['alive_npcs']} живых, {f1['dead_npcs']} умерших (Родилось детей/младенцев: {f1['babies'] + f1['children']})")
    print(f"  * Семьи и пары: {f1['families']} семей, {f1['dating_couples']} влюбленных пар")
    print(f"  * Экономика: {f1['total_wealth']:,.0f} руб. общий капитал (средний: {f1['avg_wealth']:,.0f} руб.), капитал бизнеса: {f1['biz_capital']:,.0f} руб.")
    print(f"  * Градостроительство: {f1['homes']} домов, {f1['districts']} районов, завершено строек: {f1['completed_construction']}")
    print(f"  * Ключевые события: {f1['critical_events_count']} критических событий")
    for ev in f1['recent_critical'][-3:]:
        print(f"      - {ev}")

    print(f"\n[МИР #2 (День 365)]:")
    print(f"  * Население: {f2['alive_npcs']} живых, {f2['dead_npcs']} умерших (Родилось детей/младенцев: {f2['babies'] + f2['children']})")
    print(f"  * Семьи и пары: {f2['families']} семей, {f2['dating_couples']} влюбленных пар")
    print(f"  * Экономика: {f2['total_wealth']:,.0f} руб. общий капитал (средний: {f2['avg_wealth']:,.0f} руб.), капитал бизнеса: {f2['biz_capital']:,.0f} руб.")
    print(f"  * Градостроительство: {f2['homes']} домов, {f2['districts']} районов, завершено строек: {f2['completed_construction']}")
    print(f"  * Ключевые события: {f2['critical_events_count']} критических событий")
    for ev in f2['recent_critical'][-3:]:
        print(f"      - {ev}")

    # Проверка дивергенции: миры не должны быть идентичными
    assert f1['sample_names'] != f2['sample_names'], "Генерация жителей должна быть уникальной!"
    print("\n[+] УСПЕШНО: Симуляции прошли по совершенно разным эволюционным развилкам!")
    print(f"[+] Все 10 файлов сохранений созданы в папке '{SAVES_DIR}/':")
    for chk in CHECKPOINTS:
        print(f"    - saves/run1_day_{chk}.db | saves/run2_day_{chk}.db")

if __name__ == "__main__":
    main()
