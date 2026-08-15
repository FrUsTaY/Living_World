import pytest
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from datetime import datetime, timedelta

def test_life_cycle_integration():
    sim = Simulation()
    # Speed up sim to test aging
    sim.time.speed = 1000

    generate_initial_world(sim.city, sim, 20)

    # Store initial ages
    initial_ages = {npc.id: npc.get_age(sim.time.current_datetime) for npc in sim.npcs}

    from living_world.engine.life_cycle_manager import LifeCycleManager

    # Run for 1 year (365 days), advancing day by day, making sure we hit 00:00
    for day in range(365):
        # Set time to just before midnight to hit 00:00 exactly
        sim.time.current_datetime = sim.time.current_datetime.replace(hour=23, minute=59)
        sim.update() # this ticks 1 min, becomes 00:00, triggers death check

        # Then tick the rest of the day (23h 59m) to prepare for next loop
        sim.time.tick(minutes=23*60 + 59)

    final_ages = {npc.id: npc.get_age(sim.time.current_datetime) for npc in sim.npcs}

    # Because we advanced exactly 365 days, and age randomizer in generation doesn't use leaps perfectly,
    # age should increment by exactly 1 for almost everyone (or 0 if they had a leap year birthday we missed)
    for npc in sim.npcs:
        if npc.is_alive:
            assert final_ages[npc.id] == initial_ages[npc.id] + 1 or final_ages[npc.id] == initial_ages[npc.id]

    # Test that a baby behaves differently from an adult
    # Create a baby
    from living_world.population.npc import NPC
    baby_dob = sim.time.current_datetime - timedelta(days=100) # < 1 year old
    baby = NPC("Baby", "Test", baby_dob, "М", "None", sim.npcs[0].home_id, sim.npcs[0].home_id)
    sim.add_npc(baby)

    adult_dob = sim.time.current_datetime - timedelta(days=30*365)
    adult = NPC("Adult", "Test", adult_dob, "Ж", "Врач", sim.npcs[0].home_id, sim.npcs[0].work_id)
    sim.add_npc(adult)

    # Set time to 14:00 (working hours)
    sim.time.current_datetime = datetime(2001, 1, 1, 14, 0)
    time_dict = sim.time.get_time_dict()

    baby.update(time_dict)
    adult.update(time_dict)

    assert baby.state in ["Отдыхает", "Играет", "Ест", "Спит"]
    # Adult has high probability of working, but might be resting if tired, let's force high energy
    adult.energy = 100
    adult.hunger = 100
    adult.update(time_dict)
    assert adult.state == "Работает"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
