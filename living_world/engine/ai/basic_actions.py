from living_world.engine.ai.action import Action
from living_world.engine.life_cycle_manager import LifeStage
import random

class SleepAction(Action):
    @property
    def name(self) -> str:
        return "Спит"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        if getattr(npc, 'is_sick', False):
            return 0.0  # Больничный
        hour = time_dict['hour']
        utility = 0.0

        # Гистерезис
        if getattr(npc, '_last_state', None) == self.name and npc.energy < 95:
            return 1000.0

        chronotype = getattr(npc, 'chronotype', 'lark')
        if chronotype == 'lark':
            is_sleep_hours = (hour >= 21 or hour < 6)
        else:
            is_sleep_hours = (hour >= 23 or hour < 8)

        if is_sleep_hours:
            utility += 100

            life_stage = npc.get_life_stage(simulation.time.current_datetime)
            if life_stage in [LifeStage.BABY, LifeStage.CHILD]:
                utility += 50

            if npc.energy < 30:
                utility += 50
        elif npc.energy < 20:
            utility += 50

        # При болезни или плохом самочувствии возрастает потребность в сне
        if getattr(npc, 'is_sick', False):
            utility += 75
        elif getattr(npc, 'health', 100.0) < 40:
            utility += 60

        return utility

    def execute(self, npc, simulation, time_dict):
        npc.energy += 0.3
        if npc.energy >= 60 and npc.hunger >= 30:
            npc.health = min(100.0, getattr(npc, 'health', 100.0) + 0.1)
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id

class EatAction(Action):
    @property
    def name(self) -> str:
        return "Ест"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0

        if getattr(npc, '_last_state', None) == self.name and npc.hunger < 95:
            return 1000.0

        if npc.hunger < 30:
            utility += 150
        elif npc.hunger < 60:
            utility += 50

        return utility

    def execute(self, npc, simulation, time_dict):
        npc.hunger += 2.0
        if npc.hunger >= 60:
            npc.health = min(100.0, getattr(npc, 'health', 100.0) + 0.05)
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id
        if getattr(npc, '_last_state', None) != self.name and hasattr(simulation, 'economy_manager'):
            paid = simulation.economy_manager.purchase_food(npc, cost=100.0)
            if paid == 0.0:
                npc.mood = max(0.0, npc.mood - 1.0)

class WorkAction(Action):
    @property
    def name(self) -> str:
        return "Работает"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return npc.work_id is not None

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        if getattr(npc, 'is_sick', False):
            return 0.0  # Больничный

        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', simulation.time.is_weekend if hasattr(simulation, 'time') else False)
        weekday = time_dict.get('weekday', simulation.time.weekday if hasattr(simulation, 'time') else 0)

        # Очная учеба блокирует дневную работу
        prog_id = getattr(npc, 'current_education_id', None)
        if prog_id:
            prog = simulation.education_manager.programs.get(prog_id)
            if prog and prog.type in ["school_9", "school_11", "bachelor", "college"]:
                if 8 <= hour < 15:
                    return 0.0

        # Сменные профессии (Врач, Продавец) дежурят и в выходные дни
        is_shift_worker = npc.profession in ["Врач", "Продавец"]

        if is_weekend:
            if is_shift_worker:
                # Врач или продавец выходят на дежурство в субботу или днем в воскресенье
                if 9 <= hour < 16:
                    return 85.0
                return 0.0
            else:
                # В субботу только сверхурочные у трудоголиков
                diligence = npc.traits.get('diligence', 0.0)
                if weekday == 5 and diligence > 0.6 and 9 <= hour < 13:
                    return 35.0
                # В воскресенье и для остальных в субботу — выходной
                return 0.0

        utility = 0.0
        if 8 <= hour < 17:
            life_stage = npc.get_life_stage(simulation.time.current_datetime)
            if life_stage in [LifeStage.YOUNG_ADULT, LifeStage.ADULT]:
                utility += 80
            elif life_stage == LifeStage.ELDER:
                utility += 30

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.work_id:
             npc.current_location = npc.work_id
        npc.energy -= 0.1
        if hasattr(simulation, 'economy_manager'):
            simulation.economy_manager.pay_work_wage(npc, minutes=1.0)
        else:
            npc.money += 1.0

        if hasattr(simulation, 'construction_manager'):
            work_b = simulation.city.get_building(npc.work_id) if hasattr(simulation, 'city') else None
            is_builder = npc.profession == "Строитель" or (work_b and "стройк" in work_b.name.lower())
            if is_builder:
                simulation.construction_manager.advance_construction(npc, minutes=1.0)

class RelaxAction(Action):
    @property
    def name(self) -> str:
        return "Отдыхает"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', simulation.time.is_weekend if hasattr(simulation, 'time') else False)

        if npc.mood < 30:
            utility += 40

        if getattr(npc, 'health', 100.0) < 50:
            utility += 45

        if 17 <= hour < 22 or 7 <= hour < 8:
             utility += 35
        elif is_weekend and 9 <= hour < 14:
             utility += 40

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id
        npc.mood = min(100.0, npc.mood + 1.0)
        if getattr(npc, 'health', 100.0) < 90:
            npc.health = min(100.0, getattr(npc, 'health', 100.0) + 0.05)

class PlayAction(Action):
    @property
    def name(self) -> str:
        return "Играет"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        life_stage = npc.get_life_stage(simulation.time.current_datetime)
        return life_stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL, LifeStage.TEEN]

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', simulation.time.is_weekend if hasattr(simulation, 'time') else False)
        life_stage = npc.get_life_stage(simulation.time.current_datetime)

        if 9 <= hour < 21:
             if life_stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL]:
                 utility += 70
                 if is_weekend:
                     utility += 25

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id
        npc.mood = min(100.0, npc.mood + 1.5)

class SocializeAction(Action):
    @property
    def name(self) -> str:
        return "Общается"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        if not npc.is_alive: return False
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return npc.energy >= 20 and npc.hunger >= 20

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', simulation.time.is_weekend if hasattr(simulation, 'time') else False)

        if 11 <= hour < 22:
            utility += 50 + (npc.traits.get("sociability", 0) * 15)
            if is_weekend:
                utility += 45 # На выходных горожане активно социализируются
            if getattr(npc, 'dating_partner_id', None):
                utility += 15
            if npc.mood < 60:
                utility += 10

        return utility

    def execute(self, npc, simulation, time_dict):
        cafes = simulation.city.get_places_by_type('cafe')
        parks = simulation.city.get_places_by_type('park')
        places = cafes + parks
        if places:
            target = random.choice(places).id
            if npc.current_location != target:
                npc.current_location = target
            # Если в кафе, покупает напиток или десерт
            loc_b = simulation.city.get_building(target) if hasattr(simulation, 'city') else None
            if loc_b and loc_b.b_type == 'cafe' and hasattr(simulation, 'economy_manager'):
                simulation.economy_manager.purchase_food(npc, cost=80.0)
        npc.mood = min(100.0, npc.mood + 1.2)

class StudyAction(Action):
    @property
    def name(self) -> str:
        return "Учится"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        return getattr(npc, 'education_status', None) == "Обучается" and getattr(npc, 'current_education_id', None) is not None

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        utility = 0.0
        weekday = time_dict.get('weekday', simulation.time.weekday if hasattr(simulation, 'time') else 0)

        # В воскресенье учебные заведения закрыты
        if weekday == 6:
            return 0.0

        # В субботу во второй половине дня учебные заведения закрыты
        if weekday == 5 and hour >= 13:
            return 0.0

        prog_id = getattr(npc, 'current_education_id', None)
        is_full_time = False
        if prog_id:
            prog = simulation.education_manager.programs.get(prog_id)
            if prog and prog.type in ["school_9", "school_11", "bachelor", "college"]:
                is_full_time = True

        if is_full_time:
            if 8 <= hour < 15:
                utility += 90
        else:
            # Заочное/вечернее обучение (part-time)
            if 18 <= hour < 21:
                utility += 70

        # Домашнее задание
        if 16 <= hour < 19 and is_full_time and weekday < 5:
            patience = npc.traits.get('patience', 0)
            if patience > 0:
                utility += 40

        return utility

    def execute(self, npc, simulation, time_dict):
        prog_id = getattr(npc, 'current_education_id', None)
        if not prog_id: return

        prog = simulation.education_manager.programs.get(prog_id)
        if not prog: return

        inst = simulation.education_manager.institutions.get(prog.institution_id)
        if inst and npc.current_location != inst.building_id:
             npc.current_location = inst.building_id

        npc.energy -= 0.15

class StrollAction(Action):
    @property
    def name(self) -> str:
        return "Гуляет"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        if not npc.is_alive: return False
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) in [LifeStage.BABY, LifeStage.CHILD]:
            return False
        return npc.energy >= 20 and npc.hunger >= 20

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', simulation.time.is_weekend if hasattr(simulation, 'time') else False)
        utility = 0.0
        if 17 <= hour < 22 or 7 <= hour < 9 or (is_weekend and 10 <= hour < 21):
            utility += 48 + (npc.traits.get('sociability', 0) * 10) + (npc.traits.get('boldness', 0) * 5)
            if is_weekend:
                utility += 15
            if npc.mood < 50:
                utility += 15
        if hasattr(simulation, 'weather_manager'):
            cond = simulation.weather_manager.weather_condition
            if any(w in cond for w in ["дождь", "Дождь", "Гроза", "Метель", "Снегопад"]):
                utility -= 40.0
            elif any(w in cond for w in ["Солнечно", "ясно", "Теплый"]):
                utility += 25.0
        return max(0.0, utility)

    def execute(self, npc, simulation, time_dict):
        parks = simulation.city.get_places_by_type('park')
        if parks:
            target = parks[0].id
            if npc.current_location != target:
                npc.current_location = target
        npc.energy -= 0.05
        npc.mood = min(100.0, npc.mood + 1.0)

class DateAction(Action):
    @property
    def name(self) -> str:
        return "На свидании"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        if not npc.is_alive: return False
        partner_id = getattr(npc, 'dating_partner_id', None)
        if not partner_id: return False
        partner = next((n for n in simulation.npcs if n.id == partner_id), None)
        if not partner or not partner.is_alive: return False
        return npc.energy >= 20 and npc.hunger >= 20

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', simulation.time.is_weekend if hasattr(simulation, 'time') else False)
        utility = 0.0
        partner_id = getattr(npc, 'dating_partner_id', None)
        if partner_id and ((17 <= hour < 22) or (is_weekend and 12 <= hour < 22)):
            rel = simulation.relationship_manager.get_relationship(npc.id, partner_id)
            utility += 60 + (rel.get('romantic_interest', 0) * 0.2)
            if is_weekend:
                utility += 30
        return utility

    def execute(self, npc, simulation, time_dict):
        cafes = simulation.city.get_places_by_type('cafe')
        parks = simulation.city.get_places_by_type('park')
        places = cafes + parks
        partner_id = getattr(npc, 'dating_partner_id', None)
        partner = next((n for n in simulation.npcs if n.id == partner_id), None) if partner_id else None

        # Synchronize location with partner if partner is already at a public place
        if partner and partner.current_location in [p.id for p in places]:
            target = partner.current_location
        elif places:
            target = places[0].id
        else:
            target = npc.home_id

        if npc.current_location != target:
            npc.current_location = target
        loc_b = simulation.city.get_building(target) if hasattr(simulation, 'city') else None
        if loc_b and loc_b.b_type == 'cafe' and hasattr(simulation, 'economy_manager'):
            simulation.economy_manager.purchase_food(npc, cost=150.0)
        npc.mood = min(100.0, npc.mood + 2.0)
        npc.energy -= 0.05


class HygieneAction(Action):
    @property
    def name(self) -> str:
        return "Принимает душ"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if not npc.is_alive or npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hygiene = getattr(npc, 'hygiene', 100.0)
        hour = time_dict['hour']
        utility = 0.0

        if getattr(npc, '_last_state', None) == self.name and hygiene < 95:
            return 1000.0

        if hygiene < 30:
            utility += 130
        elif hygiene < 60 and (7 <= hour < 9 or 21 <= hour < 23):
            utility += 65

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.home_id:
            npc.current_location = npc.home_id
        npc.hygiene = min(100.0, getattr(npc, 'hygiene', 0.0) + 25.0)
        npc.mood = min(100.0, npc.mood + 1.0)


class HobbyAction(Action):
    @property
    def name(self) -> str:
        return "Занимается хобби"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if not npc.is_alive or npc.get_life_stage(simulation.time.current_datetime) in [LifeStage.BABY, LifeStage.CHILD]:
            return False
        return not getattr(npc, 'is_sick', False) and npc.energy >= 15 and npc.hunger >= 20

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        is_weekend = time_dict.get('is_weekend', False)
        stress = getattr(npc, 'stress', 0.0)
        utility = 0.0

        if (17 <= hour < 22) or (is_weekend and 10 <= hour < 20):
            utility += 42.0 + (stress * 0.5)
            if npc.mood < 45:
                utility += 15.0

        return utility

    def execute(self, npc, simulation, time_dict):
        hobby = getattr(npc, 'hobby', 'Чтение')
        if hobby in ['Рыбалка', 'Спорт']:
            parks = simulation.city.get_places_by_type('park') if hasattr(simulation, 'city') else []
            if parks:
                npc.current_location = parks[0].id
            else:
                npc.current_location = npc.home_id
        else:
            npc.current_location = npc.home_id

        npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 2.5)
        npc.mood = min(100.0, npc.mood + 1.5)
        npc.energy -= 0.05


class VisitDoctorAction(Action):
    @property
    def name(self) -> str:
        return "На приеме у врача"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        if not npc.is_alive or not getattr(npc, 'is_sick', False):
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        if 8 <= hour < 18:
            return 250.0
        return 0.0

    def execute(self, npc, simulation, time_dict):
        city = getattr(simulation, 'city', None)
        doc_building = None
        if city:
            doc_building = next((b for b in city.buildings if any(w in b.name.lower() for w in ['больниц', 'поликлиник', 'клиник'])), None)
            if not doc_building:
                doc_npc = next((n for n in simulation.npcs if n.is_alive and n.profession == 'Врач' and n.work_id), None)
                if doc_npc:
                    doc_building = city.get_building(doc_npc.work_id)

        target_loc = doc_building.id if doc_building else npc.home_id
        if npc.current_location != target_loc:
            npc.current_location = target_loc

        fee = 250.0
        if npc.money >= fee:
            npc.money -= fee
            if hasattr(simulation, 'economy_manager'):
                clinic_ent = simulation.economy_manager.get_enterprise_for_building(target_loc)
                if clinic_ent:
                    clinic_ent.receive_revenue(fee)
                else:
                    simulation.economy_manager.city_treasury += fee

        npc.is_sick = False
        npc.sick_days = 0
        npc.health = min(100.0, getattr(npc, 'health', 50.0) + 35.0)
        npc.mood = min(100.0, npc.mood + 10.0)

        if hasattr(simulation, 'memory_manager'):
            simulation.memory_manager.add_memory(
                npc.id, None, "Лечение", "Посетил(а) врача, прошел(ла) курс лечения и поправился(лась)", 0.6, 0.7
            )
        if hasattr(simulation, 'event_aggregator'):
            from living_world.engine.observer.world_event import EventType, EventImportance
            simulation.event_aggregator.publish_event(
                event_type=EventType.SOCIAL_INTERACTION,
                importance=EventImportance.LOW,
                message=f"💊 {npc.get_full_name()} посетил(а) врача и успешно вылечился(лась) от болезни.",
                participants=[npc.id]
            )



class VisitCultureAction(Action):
    @property
    def name(self) -> str:
        return "Культурный досуг"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if not npc.is_alive or getattr(npc, 'jail_days', 0) > 0 or npc.state == "В тюрьме":
            return False
        if hasattr(npc, 'get_life_stage') and npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        city = getattr(simulation, 'city', None)
        if not city:
            return False
        cult_buildings = [
            b for b in city.buildings
            if getattr(b, 'b_type', '') in ['library', 'cinema', 'theater', 'stadium', 'club', 'park']
            or any(w in b.name.lower() for w in ['библиотек', 'кино', 'театр', 'стадион', 'парк', 'музей'])
        ]
        return len(cult_buildings) > 0

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        is_weekend = time_dict.get('day_of_week') in [5, 6] or time_dict.get('is_weekend', False)

        # В рабочие часы будних дней работающие жители заняты на работе
        if 8 <= hour < 17 and not is_weekend and npc.work_id:
            return 0.0

        utility = 0.0

        holiday_mgr = getattr(simulation, 'holiday_manager', None)
        if holiday_mgr and holiday_mgr.get_current_holiday(simulation.time.current_datetime):
            utility += 40.0

        if getattr(npc, 'stress', 0.0) > 40.0:
            utility += 30.0
        if npc.mood < 50.0:
            utility += 25.0

        if (17 <= hour < 22) or (is_weekend and 10 <= hour < 22):
            utility += 35.0

        return utility

    def execute(self, npc, simulation, time_dict):
        city = getattr(simulation, 'city', None)
        cult_buildings = [
            b for b in city.buildings
            if getattr(b, 'b_type', '') in ['library', 'cinema', 'theater', 'stadium', 'club', 'park']
            or any(w in b.name.lower() for w in ['библиотек', 'кино', 'театр', 'стадион', 'парк', 'музей'])
        ]
        if not cult_buildings:
            return

        import random
        target_b = random.choice(cult_buildings)
        npc.current_location = target_b.id
        b_name_lower = target_b.name.lower()

        if 'библиотек' in b_name_lower or getattr(target_b, 'b_type', '') == 'library':
            npc.traits['patience'] = min(1.0, npc.traits.get('patience', 0.0) + 0.05)
            npc.mood = min(100.0, npc.mood + 8.0)
            npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 10.0)
            desc = "Посетил(а) библиотеку, читал(а) литературу"
        elif any(w in b_name_lower for w in ['кино', 'театр', 'музей']) or getattr(target_b, 'b_type', '') in ['cinema', 'theater']:
            npc.inspiration_buffer_days = 7
            npc.mood = min(100.0, npc.mood + 15.0)
            npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 20.0)
            desc = "Посетил(а) кино/театр, получил(а) заряд вдохновения"
        elif 'стадион' in b_name_lower or getattr(target_b, 'b_type', '') in ['stadium', 'sports']:
            npc.health = min(100.0, getattr(npc, 'health', 100.0) + 4.0)
            npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 15.0)
            npc.mood = min(100.0, npc.mood + 10.0)
            desc = "Посетил(а) стадион, участвовал(а) в спортивных состязаниях"
        else:
            npc.mood = min(100.0, npc.mood + 12.0)
            npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 15.0)
            desc = "Участвовал(а) в городском фестивале в парке"

        if hasattr(simulation, 'memory_manager'):
            simulation.memory_manager.add_memory(
                npc.id, None, "Культура", desc, 0.5, 0.7
            )



class WalkPetAction(Action):
    @property
    def name(self) -> str:
        return "Прогулка с питомцем"

    def check_preconditions(self, npc, simulation, time_dict=None) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if not npc.is_alive or getattr(npc, 'jail_days', 0) > 0 or npc.state == "В тюрьме":
            return False
        if hasattr(npc, 'get_life_stage') and npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        hm = getattr(simulation, 'household_manager', None)
        if not hm:
            return False
        hh = hm.get_household(npc.household_id) if npc.household_id else None
        if not hh or not getattr(hh, 'pet', None):
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        is_weekend = time_dict.get('day_of_week') in [5, 6] or time_dict.get('is_weekend', False)
        if 8 <= hour < 17 and not is_weekend and npc.work_id:
            return 0.0

        hm = getattr(simulation, 'household_manager', None)
        hh = hm.get_household(npc.household_id) if hm and npc.household_id else None
        pet = getattr(hh, 'pet', None) if hh else None
        if not pet:
            return 0.0

        utility = 0.0
        # Собаки требуют утренней (7-9) и вечерней (18-21) прогулки
        if pet.get('type') == 'dog' and (7 <= hour <= 9 or 18 <= hour <= 21):
            utility += 55.0
        elif pet.get('type') == 'cat' and 19 <= hour <= 22:
            utility += 35.0

        if getattr(npc, 'stress', 0.0) > 35.0:
            utility += 30.0

        return utility

    def execute(self, npc, simulation, time_dict):
        hm = getattr(simulation, 'household_manager', None)
        hh = hm.get_household(npc.household_id) if hm and npc.household_id else None
        pet = getattr(hh, 'pet', None) if hh else None
        if not pet:
            return

        city = getattr(simulation, 'city', None)
        if pet.get('type') == 'dog' and city:
            parks = city.get_places_by_type('park')
            if parks:
                npc.current_location = parks[0].id
                # Социализация между собаководами в парке
                if hasattr(simulation, 'relationship_manager'):
                    rm = simulation.relationship_manager
                    other_dog_walkers = [
                        o for o in simulation.npcs
                        if o.is_alive and o.id != npc.id and o.current_location == npc.current_location
                    ]
                    if other_dog_walkers:
                        partner = other_dog_walkers[0]
                        rm.modify_relationship(npc.id, partner.id, 'familiarity', 8.0)
                        rm.modify_relationship(npc.id, partner.id, 'affinity', 5.0)

        npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 25.0)
        npc.mood = min(100.0, npc.mood + 18.0)
