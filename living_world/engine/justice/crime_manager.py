from datetime import datetime
import random
from typing import List, Dict, Optional, Tuple
from living_world.engine.observer.world_event import EventType, EventImportance

class CrimeType:
    THEFT = "THEFT"               # Мелкая кража (продукты/деньги)
    BRAWL = "BRAWL"               # Хулиганство / драка
    EMBEZZLEMENT = "EMBEZZLEMENT" # Финансовое хищение / растрата


class CrimeManager:
    """
    Система правопорядка, преступности, полиции, правосудия и пенитенциарного учета.
    """
    def __init__(self, simulation):
        self.simulation = simulation
        self.crime_history: List[Dict] = []
        self.jail_inmates: Dict[str, Dict] = {}  # npc_id -> {remaining_days, sentence_total, crime_type}
        self.district_crime_counts: Dict[str, int] = {}
        self.total_crimes_committed: int = 0
        self.total_crimes_solved: int = 0

    def get_police_building_id(self) -> Optional[str]:
        """Возвращает ID полицейского участка в городе (или создает его, если нет)."""
        city = getattr(self.simulation, 'city', None)
        if not city:
            return None
        for b in city.buildings:
            if getattr(b, 'b_type', None) in ["police", "police_station"] or "полиц" in b.name.lower():
                return b.id
        # Если здания нет, найдем административное или первое попавшееся
        if city.buildings:
            return city.buildings[0].id
        return None

    def get_police_officers(self) -> List:
        """Возвращает список действующих сотрудников полиции."""
        officers = []
        for npc in self.simulation.npcs:
            if not npc.is_alive or getattr(npc, 'jail_days', 0) > 0:
                continue
            if npc.profession in ["Полицейский", "Участковый", "Оперуполномоченный"]:
                officers.append(npc)
        return officers

    def is_patrolled(self, location_id: str) -> bool:
        """
        Проверяет, патрулируется ли данная локация сотрудником полиции (в том же здании или рядом).
        """
        officers = self.get_police_officers()
        if not officers:
            return False

        city = getattr(self.simulation, 'city', None)
        target_b = city.get_building(location_id) if city else None

        for off in officers:
            if off.state in ["Спит", "Болен", "В тюрьме"]:
                continue
            # Находится непосредственно в том же здании
            if off.current_location == location_id:
                return True
            # Проверка дистанции, если есть координаты
            if city and target_b:
                off_b = city.get_building(off.current_location)
                if off_b and getattr(city, 'get_distance', None):
                    dist = city.get_distance(off.current_location, location_id)
                    if dist <= 35.0:
                        return True
        return False

    def evaluate_and_trigger_crimes(self, current_datetime: datetime) -> int:
        """
        Проверяет жителей города на кризисные условия и мотивы совершения правонарушений.
        Возвращает количество попыток преступлений.
        """
        crimes_attempted = 0
        alive_npcs = [n for n in self.simulation.npcs if n.is_alive and getattr(n, 'jail_days', 0) == 0 and n.state not in ["Спит", "В тюрьме"]]
        random.shuffle(alive_npcs)

        for npc in alive_npcs:
            age = npc.get_age(current_datetime)
            if age < 16:
                continue

            # 1. Кража (Theft) из-за голода или нищеты
            if (npc.hunger < 20.0 or npc.money < 300.0) and npc.traits.get('diligence', 0) < 0.2:
                # Шанс совершения кражи
                theft_chance = 0.25 + (0.2 if npc.hunger < 15.0 else 0.0) + (npc.traits.get('boldness', 0) * 0.15)
                if random.random() < theft_chance:
                    self.execute_theft(npc, current_datetime)
                    crimes_attempted += 1
                    if crimes_attempted >= 2:
                        break
                    continue

            # 2. Хулиганство / драка (Brawl) из-за агрессии и высокого стресса
            if npc.traits.get('conflict', 0) > 0.4 and getattr(npc, 'stress', 0.0) > 50.0:
                brawl_chance = 0.20 + (npc.traits.get('conflict', 0) * 0.15)
                if random.random() < brawl_chance:
                    # Ищем жертву в той же локации
                    potential_victims = [
                        v for v in alive_npcs
                        if v.id != npc.id and v.current_location == npc.current_location and getattr(v, 'jail_days', 0) == 0
                    ]
                    if potential_victims:
                        victim = random.choice(potential_victims)
                        self.execute_brawl(npc, victim, current_datetime)
                        crimes_attempted += 1
                        if crimes_attempted >= 2:
                            break
                        continue

            # 3. Финансовая растрата (Embezzlement)
            if (npc.work_id and npc.traits.get('diligence', 0) < -0.3 and
                    npc.traits.get('frugality', 0) < 0.0 and npc.money < 2000.0):
                embezzle_chance = 0.15
                if random.random() < embezzle_chance:
                    self.execute_embezzlement(npc, current_datetime)
                    crimes_attempted += 1
                    if crimes_attempted >= 2:
                        break

        return crimes_attempted

    def execute_theft(self, offender, current_datetime: datetime):
        """Мелкая кража продуктов или денег из магазина/предприятия."""
        city = getattr(self.simulation, 'city', None)
        econ = getattr(self.simulation, 'economy_manager', None)
        target_enterprise = None
        target_location = offender.current_location

        if econ and hasattr(econ, 'enterprises') and econ.enterprises:
            # Ищем торговое предприятие
            shops = [e for e in econ.enterprises.values() if e.is_active and (e.finished_goods > 0 or e.budget > 500)]
            if shops:
                target_enterprise = random.choice(shops)
                target_location = target_enterprise.building_id

        self.total_crimes_committed += 1
        dist_id = "unknown"
        if city:
            b = city.get_building(target_location)
            if b and getattr(b, 'district_id', None):
                dist_id = b.district_id
                self.district_crime_counts[dist_id] = self.district_crime_counts.get(dist_id, 0) + 1

        # Проверка патруля: если локация патрулируется, 90% вероятность задержания на месте преступления
        patrolled = self.is_patrolled(target_location)
        if patrolled and random.random() < 0.90:
            # Задержание на месте!
            self.total_crimes_solved += 1
            self._publish_event(
                f"🚨 Полицейский патруль задержал с поличным {offender.get_full_name()} при попытке кражи в магазине!",
                EventType.SOCIAL_INTERACTION,
                EventImportance.HIGH,
                [offender.id]
            )
            self.process_court_verdict(offender, CrimeType.THEFT, caught_red_handed=True, current_datetime=current_datetime)
            return

        # Если патруля нет — кража удалась
        stolen_food = False
        stolen_money = 0.0
        if offender.hunger < 30.0:
            offender.hunger = min(100.0, offender.hunger + 45.0)
            stolen_food = True
            if target_enterprise and target_enterprise.finished_goods >= 1.0:
                target_enterprise.finished_goods -= 1.0
        else:
            stolen_money = 400.0
            offender.money += stolen_money
            if target_enterprise and target_enterprise.budget >= stolen_money:
                target_enterprise.budget -= stolen_money

        # Расследование по горячим следам (опрос свидетелей / камеры)
        investigation_solved = (random.random() < 0.45)
        if investigation_solved:
            self.total_crimes_solved += 1
            self._publish_event(
                f"🔍 Полиция раскрыла кражу: {offender.get_full_name()} опознан(а) по записям и показаниям свидетелей.",
                EventType.SOCIAL_INTERACTION,
                EventImportance.MEDIUM,
                [offender.id]
            )
            self.process_court_verdict(offender, CrimeType.THEFT, caught_red_handed=False, current_datetime=current_datetime)
        else:
            self._publish_event(
                f"⚠️ В районе {dist_id} совершена кража продуктов и денег. Преступнику удалось скрыться.",
                EventType.SOCIAL_INTERACTION,
                EventImportance.LOW,
                [offender.id]
            )

        self.crime_history.append({
            "type": CrimeType.THEFT,
            "offender_id": offender.id,
            "offender_name": offender.get_full_name(),
            "location_id": target_location,
            "solved": investigation_solved,
            "date": current_datetime.strftime("%Y-%m-%d %H:%M")
        })

    def execute_brawl(self, offender, victim, current_datetime: datetime):
        """Хулиганство и драка в общественном месте."""
        self.total_crimes_committed += 1
        loc_id = offender.current_location

        # Урон жертве
        victim.health = max(10.0, getattr(victim, 'health', 100.0) - 18.0)
        victim.stress = min(100.0, getattr(victim, 'stress', 0.0) + 30.0)
        victim.mood = max(0.0, victim.mood - 25.0)
        offender.stress = max(0.0, getattr(offender, 'stress', 0.0) - 15.0)  # Выместил злость

        if hasattr(self.simulation, 'memory_manager'):
            self.simulation.memory_manager.add_memory(
                victim.id, offender.id, "Нападение", f"Подвергся(лась) нападению со стороны {offender.first_name}", 0.9, -1.0
            )

        # Патруль
        patrolled = self.is_patrolled(loc_id)
        if patrolled and random.random() < 0.90:
            self.total_crimes_solved += 1
            self._publish_event(
                f"🚨 Полиция пресекла уличную драку: {offender.get_full_name()} задержан(а) за избиение {victim.get_full_name()}!",
                EventType.SOCIAL_INTERACTION,
                EventImportance.HIGH,
                [offender.id, victim.id]
            )
            self.process_court_verdict(offender, CrimeType.BRAWL, caught_red_handed=True, current_datetime=current_datetime)
            return

        # Подача заявления в полицию
        reported = random.random() < 0.65
        if reported:
            self.total_crimes_solved += 1
            self._publish_event(
                f"⚖ {victim.get_full_name()} подал(а) заявление в полицию на {offender.get_full_name()} по факту побоев.",
                EventType.SOCIAL_INTERACTION,
                EventImportance.MEDIUM,
                [offender.id, victim.id]
            )
            self.process_court_verdict(offender, CrimeType.BRAWL, caught_red_handed=False, current_datetime=current_datetime)
        else:
            self._publish_event(
                f"⚡ В городе произошла драка между гражданами, нарушитель скрылся с места потасовки.",
                EventType.SOCIAL_INTERACTION,
                EventImportance.LOW,
                [offender.id, victim.id]
            )

        self.crime_history.append({
            "type": CrimeType.BRAWL,
            "offender_id": offender.id,
            "victim_id": victim.id,
            "location_id": loc_id,
            "solved": reported,
            "date": current_datetime.strftime("%Y-%m-%d %H:%M")
        })

    def execute_embezzlement(self, offender, current_datetime: datetime):
        """Финансовое хищение средств с баланса предприятия."""
        econ = getattr(self.simulation, 'economy_manager', None)
        enterprise = None
        if econ and hasattr(econ, 'enterprises'):
            for e in econ.enterprises.values():
                if e.building_id == offender.work_id and e.budget >= 1500.0:
                    enterprise = e
                    break

        if not enterprise:
            return

        self.total_crimes_committed += 1
        stolen_amount = min(3500.0, enterprise.budget * 0.2)
        enterprise.budget -= stolen_amount
        offender.money += stolen_amount

        # Аудиторская проверка предприятия (70% вероятность вскрытия)
        audit_discovered = random.random() < 0.70
        if audit_discovered:
            self.total_crimes_solved += 1
            self._publish_event(
                f"🚨 Аудит на предприятии «{enterprise.name}» вскрыл факт хищения {stolen_amount:.0f} ₽ сотрудником {offender.get_full_name()}!",
                EventType.ECONOMIC,
                EventImportance.HIGH,
                [offender.id]
            )
            self.process_court_verdict(offender, CrimeType.EMBEZZLEMENT, caught_red_handed=False, current_datetime=current_datetime)
        else:
            self._publish_event(
                f"📉 На предприятии «{enterprise.name}» зафиксирована необъяснимая финансовая недостача.",
                EventType.ECONOMIC,
                EventImportance.LOW,
                [offender.id]
            )

        self.crime_history.append({
            "type": CrimeType.EMBEZZLEMENT,
            "offender_id": offender.id,
            "enterprise_id": enterprise.id,
            "amount": stolen_amount,
            "solved": audit_discovered,
            "date": current_datetime.strftime("%Y-%m-%d %H:%M")
        })

    def process_court_verdict(self, offender, crime_type: str, caught_red_handed: bool = False, current_datetime: datetime = None):
        """
        Судебное рассмотрение дела: назначение штрафа или реального тюремного заключения.
        """
        has_record = getattr(offender, 'has_criminal_record', False)
        econ = getattr(self.simulation, 'economy_manager', None)

        # Мелкая кража без судимости -> Административный штраф
        if crime_type == CrimeType.THEFT and not has_record:
            fine = 2000.0
            fine_paid = min(offender.money, fine)
            offender.money -= fine_paid
            if econ:
                econ.city_treasury += fine_paid
            offender.mood = max(0.0, offender.mood - 15.0)
            offender.stress = min(100.0, getattr(offender, 'stress', 0.0) + 20.0)
            self._publish_event(
                f"⚖ Городской суд приговорил {offender.get_full_name()} к штрафу {fine:.0f} ₽ за мелкое хищение.",
                EventType.SOCIAL_INTERACTION,
                EventImportance.MEDIUM,
                [offender.id]
            )
            return

        # Тяжкое нарушение (драка, растрата, повторная кража) -> Тюремное заключение
        sentence_days = 45
        if crime_type == CrimeType.BRAWL:
            sentence_days = 60
        elif crime_type == CrimeType.EMBEZZLEMENT:
            sentence_days = 90
        elif has_record:
            sentence_days = 75

        police_b_id = self.get_police_building_id()
        offender.has_criminal_record = True
        offender.jail_days = sentence_days
        offender.state = "В тюрьме"
        if police_b_id:
            offender.current_location = police_b_id

        # Увольнение с работы
        offender.work_id = None
        offender.mood = max(0.0, offender.mood - 40.0)
        offender.stress = min(100.0, getattr(offender, 'stress', 0.0) + 40.0)

        self.jail_inmates[offender.id] = {
            "name": offender.get_full_name(),
            "remaining_days": sentence_days,
            "sentence_total": sentence_days,
            "crime_type": crime_type,
            "admitted_date": current_datetime.strftime("%Y-%m-%d") if current_datetime else ""
        }

        if hasattr(self.simulation, 'memory_manager'):
            self.simulation.memory_manager.add_memory(
                offender.id, None, "Тюрьма", f"Осужден(а) судом на {sentence_days} дней лишения свободы", 1.0, -1.0
            )

        self._publish_event(
            f"🏛 Приговор городского суда: {offender.get_full_name()} признан(а) виновным(ой) и приговорен(а) к {sentence_days} суткам заключения в городском изоляторе!",
            EventType.SOCIAL_INTERACTION,
            EventImportance.HIGH,
            [offender.id]
        )

    def daily_update(self, current_datetime: datetime):
        """Ежедневное обновление пенитенциарной системы и условий заключенных."""
        released_ids = []

        for npc in self.simulation.npcs:
            if not npc.is_alive:
                continue

            # Обработка заключенных
            if getattr(npc, 'jail_days', 0) > 0:
                npc.jail_days -= 1
                npc.state = "В тюрьме"

                # Казенный паек и отдых в камере
                npc.hunger = max(npc.hunger, 65.0)
                npc.energy = max(npc.energy, 70.0)
                npc.hygiene = max(20.0, getattr(npc, 'hygiene', 100.0) - 2.0)
                npc.stress = min(100.0, getattr(npc, 'stress', 0.0) + 0.5)

                if npc.id in self.jail_inmates:
                    self.jail_inmates[npc.id]["remaining_days"] = npc.jail_days

                if npc.jail_days <= 0:
                    released_ids.append(npc)

        for npc in released_ids:
            npc.jail_days = 0
            npc.state = "Бодрствует"
            if npc.home_id:
                npc.current_location = npc.home_id
            if npc.id in self.jail_inmates:
                del self.jail_inmates[npc.id]

            self._publish_event(
                f"🕊 {npc.get_full_name()} полностью отбыл(а) срок тюремного заключения и вышел(ла) на свободу.",
                EventType.SOCIAL_INTERACTION,
                EventImportance.MEDIUM,
                [npc.id]
            )

    def _publish_event(self, msg: str, event_type: EventType, importance: EventImportance, participants: List[str]):
        if hasattr(self.simulation, 'event_aggregator'):
            self.simulation.event_aggregator.publish_event(
                event_type=event_type,
                importance=importance,
                message=msg,
                participants=participants
            )

    def to_dict(self) -> dict:
        return {
            "jail_inmates": self.jail_inmates,
            "district_crime_counts": self.district_crime_counts,
            "total_crimes_committed": self.total_crimes_committed,
            "total_crimes_solved": self.total_crimes_solved,
            "crime_history": self.crime_history[-100:]  # последние 100 преступлений
        }

    def load_from_dict(self, data: dict):
        if not data:
            return
        self.jail_inmates = data.get("jail_inmates", {})
        self.district_crime_counts = data.get("district_crime_counts", {})
        self.total_crimes_committed = int(data.get("total_crimes_committed", 0))
        self.total_crimes_solved = int(data.get("total_crimes_solved", 0))
        self.crime_history = data.get("crime_history", [])
