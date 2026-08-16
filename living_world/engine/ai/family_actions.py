from living_world.engine.ai.action import Action
from living_world.engine.life_cycle_manager import LifeStage

class CareForChildAction(Action):
    @property
    def name(self) -> str:
        return "Заботится о ребенке"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        # Ухаживать могут только YOUNG_ADULT, ADULT, ELDER (TEEN - опционально в будущем)
        stage = npc.get_life_stage(simulation.time.current_datetime)
        if stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL, LifeStage.TEEN, LifeStage.DEAD]:
            return False

        # Есть ли дети, нуждающиеся в уходе (в данном случае - младенцы)
        children = simulation.family_manager.get_children(npc.id)
        for child in children:
            if not child.is_alive: continue
            child_stage = child.get_life_stage(simulation.time.current_datetime)
            if child_stage == LifeStage.BABY:
                return True

        return False

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0

        # Получаем всех детей-младенцев
        children = simulation.family_manager.get_children(npc.id)
        babies = [c for c in children if c.is_alive and c.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY]

        if not babies:
            return 0.0

        # Находим младенца с наибольшей потребностью в уходе
        target_baby = max(babies, key=lambda b: max(100 - b.hunger, 100 - b.mood))

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

        # Учет наличия второго родителя
        parents = simulation.family_manager.get_parents(target_baby.id)
        other_parent = next((p for p in parents if p.id != npc.id and p.is_alive), None)

        if other_parent:
            # Если другой родитель жив, делим ответственность
            # Если другой родитель рядом, снижаем utility, чтобы они не бросались одновременно
            if other_parent.current_location == target_baby.current_location:
                 utility *= 0.6
            else:
                 # Если другой родитель далеко, берем больше ответственности на себя, но все же меньше чем мать/отец-одиночка
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
