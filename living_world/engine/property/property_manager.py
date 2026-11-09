from datetime import datetime
import random
from typing import Optional, Dict, List
from living_world.engine.observer.world_event import EventType, EventImportance

class PropertyManager:
    """
    Управление личным имуществом, бытовой техникой, автомобилями, зимним гардеробом,
    подарками и домашними питомцами.
    """
    APPLIANCE_CATALOG = [
        ("Холодильник", 15000.0),
        ("Стиральная машина", 18000.0),
        ("Телевизор", 14000.0),
        ("Кухонная плита", 12000.0)
    ]
    DOG_NAMES = ["Бобик", "Шарик", "Рекс", "Дружок", "Бим", "Арчи"]
    CAT_NAMES = ["Барсик", "Мурка", "Васька", "Кузя", "Снежок", "Том"]

    def __init__(self, simulation):
        self.simulation = simulation
        self.total_cars_bought: int = 0
        self.total_pets_adopted: int = 0
        self.total_appliances_bought: int = 0

    def daily_update(self, dt: datetime):
        """Ежедневная оценка приобретения имущества, питомцев и комфорта."""
        self._evaluate_appliances(dt)
        self._evaluate_cars(dt)
        self._evaluate_warm_clothes(dt)
        self._evaluate_pets(dt)
        self._maintain_cars()

    def _evaluate_appliances(self, dt: datetime):
        """Домохозяйства улучшают жилищные условия покупкой бытовой техники."""
        hm = getattr(self.simulation, 'household_manager', None)
        if not hm:
            return

        for hh in hm.households.values():
            if not hasattr(hh, 'appliances') or not isinstance(hh.appliances, list):
                if isinstance(getattr(hh, 'appliances', None), str):
                    try:
                        import json
                        hh.appliances = json.loads(hh.appliances)
                    except Exception:
                        hh.appliances = []
                else:
                    hh.appliances = []

            # Если все 4 базовых прибора куплены — пропускаем
            if len(hh.appliances) >= len(self.APPLIANCE_CATALOG):
                continue

            members = [n for n in self.simulation.npcs if n.is_alive and n.household_id == hh.id]
            if not members:
                continue

            family_budget = sum(m.money for m in members)
            # Находим следующий прибор для покупки
            for app_name, cost in self.APPLIANCE_CATALOG:
                if app_name not in hh.appliances:
                    # Покупка если бюджет семьи превышает 2x стоимость
                    if family_budget >= cost * 2.0:
                        # Списываем средства
                        remaining_cost = cost
                        for m in members:
                            deduct = min(m.money, remaining_cost)
                            m.money -= deduct
                            remaining_cost -= deduct
                            if remaining_cost <= 0:
                                break

                        hh.appliances.append(app_name)
                        hh.home_comfort = min(100.0, 40.0 + len(hh.appliances) * 15.0)
                        self.total_appliances_bought += 1

                        for m in members:
                            m.mood = min(100.0, m.mood + 10.0)

                        if hasattr(self.simulation, 'event_aggregator'):
                            home_b = self.simulation.city.get_building(hh.home_id) if hasattr(self.simulation, 'city') else None
                            home_name = home_b.name if home_b else "Дом"
                            self.simulation.event_aggregator.publish_event(
                                event_type=EventType.ECONOMIC,
                                importance=EventImportance.LOW,
                                message=f"🛋 Домохозяйство ({home_name}) приобрело бытовую технику: «{app_name}»! Комфорт жилья вырос до {int(hh.home_comfort)}%.",
                                participants=[m.id for m in members[:3]]
                            )
                    break

    def _evaluate_cars(self, dt: datetime):
        """Зажиточные горожане покупают личные автомобили."""
        for npc in self.simulation.npcs:
            if not npc.is_alive or getattr(npc, 'jail_days', 0) > 0:
                continue
            if getattr(npc, 'transport_mode', 'foot') != 'car' and npc.money >= 120000.0:
                car_cost = 95000.0
                npc.money -= car_cost
                npc.transport_mode = 'car'
                self.total_cars_bought += 1
                npc.mood = min(100.0, npc.mood + 25.0)

                if hasattr(self.simulation, 'memory_manager'):
                    self.simulation.memory_manager.add_memory(
                        npc.id, None, "Покупка авто", "Приобрел(а) личный автомобиль в автосалоне", 0.9, 1.0
                    )

                if hasattr(self.simulation, 'event_aggregator'):
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.ECONOMIC,
                        importance=EventImportance.MEDIUM,
                        message=f"🚗 {npc.get_full_name()} приобрел(а) личный автомобиль за {car_cost:,.0f} ₽!",
                        participants=[npc.id]
                    )

    def _maintain_cars(self):
        """Расходы на бензин и обслуживание личных авто."""
        econ = getattr(self.simulation, 'economy_manager', None)
        for npc in self.simulation.npcs:
            if npc.is_alive and getattr(npc, 'transport_mode', 'foot') == 'car':
                fuel_cost = 60.0
                if npc.money >= fuel_cost:
                    npc.money -= fuel_cost
                    if econ:
                        econ.city_treasury += 15.0  # Топливный сбор в казну

    def _evaluate_warm_clothes(self, dt: datetime):
        """Покупка теплой одежды в холодный сезон."""
        wm = getattr(self.simulation, 'weather_manager', None)
        temp = wm.temperature if wm else 10.0

        if dt.month in [10, 11, 12, 1, 2, 3] or temp < 5.0:
            for npc in self.simulation.npcs:
                if not npc.is_alive or getattr(npc, 'has_warm_clothes', False):
                    continue
                cost = 2500.0
                if npc.money >= cost:
                    npc.money -= cost
                    npc.has_warm_clothes = True
                    npc.mood = min(100.0, npc.mood + 5.0)

    def _evaluate_pets(self, dt: datetime):
        """Одинокие пенсионеры и семьи заводят домашних питомцев."""
        hm = getattr(self.simulation, 'household_manager', None)
        if not hm:
            return

        for hh in hm.households.values():
            if getattr(hh, 'pet', None):
                continue

            members = [n for n in self.simulation.npcs if n.is_alive and n.household_id == hh.id]
            if not members:
                continue

            # Одинокий пожилой человек или семья с детьми
            is_lonely_elder = len(members) == 1 and members[0].get_age(dt) >= 60
            has_children = any(m.get_age(dt) < 16 for m in members)
            avg_money = sum(m.money for m in members) / len(members)

            if (is_lonely_elder or has_children) and avg_money >= 3000.0:
                pet_type = "dog" if (has_children or random.random() < 0.5) else "cat"
                pet_name = random.choice(self.DOG_NAMES if pet_type == "dog" else self.CAT_NAMES)
                hh.pet = {"type": pet_type, "name": pet_name}
                self.total_pets_adopted += 1

                for m in members:
                    m.mood = min(100.0, m.mood + 15.0)
                    m.stress = max(0.0, getattr(m, 'stress', 0.0) - 15.0)
                    if hasattr(self.simulation, 'memory_manager'):
                        pet_ru = "собаку" if pet_type == "dog" else "кошку"
                        self.simulation.memory_manager.add_memory(
                            m.id, None, "Питомец", f"Завели {pet_ru} по кличке {pet_name}", 0.7, 0.9
                        )

                if hasattr(self.simulation, 'event_aggregator'):
                    head = members[0]
                    pet_ru = "щенка" if pet_type == "dog" else "котенка"
                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.SOCIAL_INTERACTION,
                        importance=EventImportance.LOW,
                        message=f"🐾 В семье {head.get_full_name()} появился питомец — взяли {pet_ru} по кличке {pet_name}!",
                        participants=[m.id for m in members]
                    )

    def give_gift(self, sender, receiver, gift_name: str = "Цветы и подарок", cost: float = 600.0):
        """Дарение подарка между жителями."""
        if sender.money >= cost:
            sender.money -= cost
        receiver.mood = min(100.0, receiver.mood + 20.0)
        receiver.stress = max(0.0, getattr(receiver, 'stress', 0.0) - 15.0)
        sender.mood = min(100.0, sender.mood + 10.0)

        if hasattr(self.simulation, 'relationship_manager'):
            rm = self.simulation.relationship_manager
            rm.modify_relationship(receiver.id, sender.id, 'affinity', 20.0)
            rm.modify_relationship(receiver.id, sender.id, 'trust', 15.0)
            rm.modify_relationship(sender.id, receiver.id, 'affinity', 10.0)

        if hasattr(self.simulation, 'memory_manager'):
            self.simulation.memory_manager.add_memory(
                receiver.id, sender.id, "Подарок", f"Получил(а) «{gift_name}» от {sender.first_name}", 0.8, 1.0
            )

        if hasattr(self.simulation, 'event_aggregator'):
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.SOCIAL_INTERACTION,
                importance=EventImportance.LOW,
                message=f"🎁 {sender.get_full_name()} преподнес(ла) подарок («{gift_name}») для {receiver.get_full_name()}.",

                participants=[sender.id, receiver.id]
            )

    def to_dict(self) -> dict:
        return {
            "total_cars_bought": self.total_cars_bought,
            "total_pets_adopted": self.total_pets_adopted,
            "total_appliances_bought": self.total_appliances_bought
        }

    def load_from_dict(self, data: dict):
        if not data:
            return
        self.total_cars_bought = int(data.get("total_cars_bought", 0))
        self.total_pets_adopted = int(data.get("total_pets_adopted", 0))
        self.total_appliances_bought = int(data.get("total_appliances_bought", 0))
