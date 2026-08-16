from living_world.engine.ai.action import Action
from living_world.engine.life_cycle_manager import LifeStage

class CareForChildAction(Action):
    @property
    def name(self) -> str:
        return "Заботится о ребенке"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        # Ухаживать могут только YOUNG_ADULT, ADULT, ELDER
        stage = npc.get_life_stage(simulation.time.current_datetime)
        if stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL, LifeStage.TEEN, LifeStage.DEAD]:
            return False

        # Ищем младенцев, нуждающихся в уходе.
        # Приоритет - биологические дети (где бы они ни были) или любые дети в собственном домохозяйстве
        biological_children = simulation.family_manager.get_children(npc.id)
        household_children = simulation.household_manager.get_children(npc.household_id) if getattr(npc, 'household_id', None) else []

        all_potential_children = set(biological_children + household_children)

        for child in all_potential_children:
            if not child.is_alive: continue
            child_stage = child.get_life_stage(simulation.time.current_datetime)
            if child_stage == LifeStage.BABY:
                return True

        return False

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0

        # Получаем всех младенцев, о которых этот NPC мог бы позаботиться
        biological_children = simulation.family_manager.get_children(npc.id)
        household_children = simulation.household_manager.get_children(npc.household_id) if getattr(npc, 'household_id', None) else []

        all_potential_children = set(biological_children + household_children)

        babies = [c for c in all_potential_children if c.is_alive and c.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY]

        if not babies:
            return 0.0

        # Находим младенца с наибольшей потребностью в уходе
        # Добавляем небольшой вес, если ребенок в том же домохозяйстве, и еще бОльший вес - если это биологический ребенок
        def baby_priority(b):
            base_need = max(100 - b.hunger, 100 - b.mood)
            is_bio = 1 if (b.mother_id == npc.id or b.father_id == npc.id) else 0
            is_same_hh = 1 if getattr(b, 'household_id', None) == getattr(npc, 'household_id', None) else 0
            return base_need + (is_bio * 50) + (is_same_hh * 20)

        target_baby = max(babies, key=baby_priority)

        # Базовая мотивация: если ребёнок голоден или плачет (плохое настроение)
        hunger_deficit = 100 - target_baby.hunger
        mood_deficit = 100 - target_baby.mood

        if hunger_deficit > 70:
            utility += 250  # Критический голод младенца - высший приоритет
        elif hunger_deficit > 40:
            utility += 100
        elif hunger_deficit > 20:
            utility += 50

        if mood_deficit > 60:
            utility += 80
        elif mood_deficit > 30:
            utility += 40

        # Учёт расстояния (штраф за дальнюю локацию)
        if npc.current_location != target_baby.current_location:
            utility -= 20

        # Учёт состояния самого родителя (если родитель истощён, utility падает)
        if npc.energy < 20:
            utility -= 80
        if npc.hunger < 20:
            utility -= 80

        # Учёт черт характера (опционально)
        empathy = npc.traits.get('empathy', 0)
        utility += empathy * 20

        # Штрафуем не-биологических родителей (приоритет отдается биологическим)
        is_biological_parent = (target_baby.mother_id == npc.id or target_baby.father_id == npc.id)
        if not is_biological_parent:
            utility *= 0.5 # Снижаем мотивацию, чтобы био родители отреагировали первыми

        # Учет наличия других способных взрослых опекунов (био родителей или других взрослых из домохозяйства)
        parents = simulation.family_manager.get_parents(target_baby.id)
        living_bio_parents = [p for p in parents if p.is_alive]

        household_adults = simulation.household_manager.get_adults(getattr(target_baby, 'household_id', None)) if getattr(target_baby, 'household_id', None) else []

        # Кто потенциально может заботиться? Био родители + взрослые в домохозяйстве
        potential_caregivers = set(living_bio_parents + household_adults)
        other_caregivers = [c for c in potential_caregivers if c.id != npc.id and c.is_alive]

        if other_caregivers:
            # Если рядом есть другие потенциальные опекуны (особенно био родители)
            nearby_caregivers = [c for c in other_caregivers if c.current_location == target_baby.current_location]

            # Если npc не является био родителем, но рядом есть живой био родитель, сильно снижаем utility
            if not is_biological_parent and any((p.id == target_baby.mother_id or p.id == target_baby.father_id) for p in nearby_caregivers):
                utility *= 0.2
            elif nearby_caregivers:
                # Кто-то другой рядом (даже если оба био родители или оба не био)
                utility *= 0.6
            else:
                # Опекуны есть, но они далеко
                utility *= 0.8

        # Сохраняем target_baby, чтобы использовать его в execute()
        npc._target_baby_id = target_baby.id

        # Гистерезис
        if getattr(npc, '_last_state', None) == self.name and (target_baby.hunger < 95 or target_baby.mood < 95):
            utility += 500.0

        return max(0.0, utility)

    def execute(self, npc, simulation, time_dict):
        target_baby_id = getattr(npc, '_target_baby_id', None)
        if not target_baby_id: return

        target_baby = next((n for n in simulation.npcs if n.id == target_baby_id), None)
        if not target_baby or not target_baby.is_alive: return

        # Перемещаемся к ребенку
        if npc.current_location != target_baby.current_location:
            npc.current_location = target_baby.current_location

        # Тратим ресурсы родителя
        npc.energy -= 0.5

        # Восстанавливаем потребности младенца
        target_baby.hunger += 10.0
        target_baby.mood += 5.0

        target_baby.hunger = min(100.0, target_baby.hunger)
        target_baby.mood = min(100.0, target_baby.mood)

        # Улучшаем отношения
        simulation.relationship_manager.modify_relationship(target_baby.id, npc.id, 'affinity', 0.5)
        simulation.relationship_manager.modify_relationship(target_baby.id, npc.id, 'trust', 0.5)
