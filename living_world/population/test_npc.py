from datetime import datetime

from living_world.engine.life_cycle_manager import LifeStage
from living_world.population.npc import NPC


def test_life_stage_cache_is_invalidated_when_npc_dies():
    npc = NPC("Иван", "Иванов", datetime(1970, 1, 1), "М", "Врач", "home", "work")
    current_date = datetime(2040, 1, 1)

    assert npc.get_life_stage(current_date) is LifeStage.ELDER
    npc.is_alive = False

    assert npc.get_life_stage(current_date) is LifeStage.DEAD
