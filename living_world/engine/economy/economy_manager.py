from typing import Dict, List, Optional
import random
from living_world.engine.economy.enterprise import Enterprise
from living_world.engine.event_bus import bus

PROFESSION_HOURLY_WAGES: Dict[str, float] = {
    "Врач": 550.0,
    "Инженер": 500.0,
    "Строитель": 400.0,
    "Механик": 375.0,
    "Учитель": 310.0,
    "Пекарь": 275.0,
    "Фермер": 250.0,
    "Продавец": 225.0,
    "Разнорабочий": 190.0,
}

DEFAULT_HOURLY_WAGE = 200.0
DEFAULT_MEAL_PRICE = 150.0


class EconomyManager:
    """
    Управляет экономическими процессами города:
    - Предприятиями и их бюджетами
    - Начислением зарплат в соответствии с профессией и квалификацией
    - Торговлей и расходами жителей на питание и быт
    - Дивидендами владельцев бизнеса
    """
    def __init__(self, simulation):
        self.simulation = simulation
        self.enterprises: Dict[str, Enterprise] = {}
        self.building_to_enterprise: Dict[str, str] = {}  # building_id -> enterprise_id

    def register_enterprise(self, enterprise: Enterprise):
        self.enterprises[enterprise.id] = enterprise
        self.building_to_enterprise[enterprise.building_id] = enterprise.id

    def create_enterprise(
        self,
        name: str,
        enterprise_type: str,
        building_id: str,
        owner_id: Optional[str] = None,
        budget: float = 50000.0,
        wage_rate: Optional[float] = None
    ) -> Enterprise:
        if wage_rate is None:
            wage_rate = 250.0
        ent = Enterprise(
            name=name,
            enterprise_type=enterprise_type,
            building_id=building_id,
            owner_id=owner_id,
            budget=budget,
            wage_rate=wage_rate
        )
        self.register_enterprise(ent)
        return ent

    def get_enterprise_by_id(self, enterprise_id: str) -> Optional[Enterprise]:
        return self.enterprises.get(enterprise_id)

    def get_enterprise_for_building(self, building_id: str) -> Optional[Enterprise]:
        ent_id = self.building_to_enterprise.get(building_id)
        if ent_id:
            return self.enterprises.get(ent_id)
        return None

    def get_food_enterprises(self) -> List[Enterprise]:
        return [e for e in self.enterprises.values() if e.is_active and e.enterprise_type in ['shop', 'cafe']]

    def get_hourly_wage(self, profession: str) -> float:
        return PROFESSION_HOURLY_WAGES.get(profession, DEFAULT_HOURLY_WAGE)

    def pay_work_wage(self, npc, minutes: float = 1.0) -> float:
        """
        Начисляет оплату за отработанное время (в минутах).
        Деньги выплачиваются предприятием, на котором прикреплён житель.
        """
        hourly_wage = self.get_hourly_wage(npc.profession)
        minute_rate = hourly_wage / 60.0
        earned = minute_rate * minutes

        ent = self.get_enterprise_for_building(npc.work_id)
        if ent:
            ent.pay_expense(earned)
            ent.add_employee(npc.id)

        npc.money += earned
        return earned

    def purchase_food(self, npc, cost: float = DEFAULT_MEAL_PRICE) -> float:
        """
        Оплата еды жителем. Средства поступают в городские предприятия питания/торговли.
        Если средств недостаточно, житель питается социальным минимумом.
        """
        actual_paid = 0.0
        if npc.money >= cost:
            npc.money -= cost
            actual_paid = cost
        elif npc.money > 0:
            actual_paid = npc.money
            npc.money = 0.0
        else:
            # Денег нет: вынужденное бесплатное соцпитание
            actual_paid = 0.0

        if actual_paid > 0:
            food_venues = self.get_food_enterprises()
            if food_venues:
                chosen_venue = random.choice(food_venues)
                chosen_venue.receive_revenue(actual_paid)

        return actual_paid

    def daily_cycle(self):
        """
        Ежедневное подведение итогов экономической активности:
        - Расчет прибыли/убытков предприятий
        - Выплата дивидендов владельцам частных бизнесов
        """
        from living_world.engine.observer.world_event import EventType, EventImportance

        for ent in list(self.enterprises.values()):
            if not ent.is_active:
                continue

            # Если у предприятия есть владелец-NPC и баланс превышает 30 000 ₽ с положительной выручкой
            if ent.owner_id and ent.budget > 30000.0 and ent.daily_revenue > ent.daily_expenses:
                net_daily = ent.daily_revenue - ent.daily_expenses
                dividend = round(net_daily * 0.25, 2)
                if dividend > 0 and ent.budget >= dividend:
                    owner_npc = next((n for n in self.simulation.npcs if n.id == ent.owner_id and n.is_alive), None)
                    if owner_npc:
                        ent.budget -= dividend
                        owner_npc.money += dividend
                        if dividend >= 500:
                            self.simulation.event_aggregator.publish_event(
                                event_type=EventType.ECONOMIC,
                                importance=EventImportance.LOW,
                                message=f"💼 {owner_npc.get_full_name()} получил дивиденды {dividend:.0f} ₽ от предприятия '{ent.name}'.",
                                participants=[owner_npc.id]
                            )

            ent.reset_daily_stats()

    def get_city_economic_stats(self) -> dict:
        """
        Сводная статистика экономики города.
        """
        total_enterprise_capital = sum(e.budget for e in self.enterprises.values())
        active_enterprises = sum(1 for e in self.enterprises.values() if e.is_active)
        alive_npcs = [n for n in self.simulation.npcs if n.is_alive]
        total_citizens_money = sum(n.money for n in alive_npcs)
        avg_wealth = (total_citizens_money / len(alive_npcs)) if alive_npcs else 0.0

        return {
            "total_enterprises": len(self.enterprises),
            "active_enterprises": active_enterprises,
            "total_business_capital": total_enterprise_capital,
            "total_citizens_wealth": total_citizens_money,
            "average_wealth": avg_wealth,
        }
