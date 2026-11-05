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
DEFAULT_MEAL_PRICE = 120.0


class EconomyManager:
    """
    Управляет экономическими процессами города:
    - Предприятиями и их бюджетами
    - Начислением зарплат в соответствии с профессией и квалификацией
    - Торговлей и расходами жителей на питание и быт
    - Дивидендами владельцев бизнеса
    """
    def __init__(self, simulation, city_treasury: float = 100000.0):
        self.simulation = simulation
        self.city_treasury: float = float(city_treasury)
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

        # 13% НДФЛ в городскую казну
        tax = earned * 0.13
        net = earned - tax
        self.city_treasury += tax
        npc.money += net
        return net

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
        - Выплата муниципальных пенсий из городской казны
        - Сбор ежемесячных коммунальных платежей (ЖКХ)
        - Расчет прибыли/убытков предприятий и дивидендов
        - Создание частных предприятий состоятельными гражданами
        """
        from living_world.engine.observer.world_event import EventType, EventImportance

        # 1. Пенсии пожилым жителям (из городской казны)
        daily_pension = 650.0  # ~20 000 ₽ / месяц
        for npc in self.simulation.npcs:
            if npc.is_alive and npc.profession == "Пенсионер":
                if self.city_treasury >= daily_pension:
                    self.city_treasury -= daily_pension
                    npc.money += daily_pension
                else:
                    npc.money += 200.0

        # 2. Ежемесячные коммунальные платежи (ЖКХ) каждые 30 дней
        sim_day = self.simulation.time.day if hasattr(self.simulation, 'time') else 1
        if sim_day > 1 and sim_day % 30 == 0:
            collected_tax = 0.0
            if hasattr(self.simulation, 'household_manager'):
                for hh in self.simulation.household_manager.households.values():
                    adults = self.simulation.household_manager.get_adults(hh.id)
                    if adults:
                        fee_per_adult = 4000.0 / len(adults)
                        for a in adults:
                            fee = min(a.money, fee_per_adult)
                            a.money -= fee
                            collected_tax += fee
            self.city_treasury += collected_tax
            if collected_tax > 0 and hasattr(self.simulation, 'event_aggregator'):
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.ECONOMIC,
                    importance=EventImportance.LOW,
                    message=f"Собраны коммунальные платежи (ЖКХ): {collected_tax:,.0f} ₽ поступили в городскую казну."
                )

        # 3. Дивиденды предпринимателям
        for ent in list(self.enterprises.values()):
            if not ent.is_active:
                continue

            if ent.owner_id and ent.budget > 30000.0 and ent.daily_revenue > ent.daily_expenses:
                net_daily = ent.daily_revenue - ent.daily_expenses
                dividend = round(net_daily * 0.25, 2)
                if dividend > 0 and ent.budget >= dividend:
                    owner_npc = next((n for n in self.simulation.npcs if n.id == ent.owner_id and n.is_alive), None)
                    if owner_npc:
                        ent.budget -= dividend
                        owner_npc.money += dividend
                        if dividend >= 400 and hasattr(self.simulation, 'event_aggregator'):
                            self.simulation.event_aggregator.publish_event(
                                event_type=EventType.ECONOMIC,
                                importance=EventImportance.LOW,
                                message=f"💼 {owner_npc.get_full_name()} получил(а) дивиденды {dividend:.0f} ₽ от предприятия '{ent.name}'.",
                                participants=[owner_npc.id]
                            )

            ent.reset_daily_stats()

        # 4. Открытие частных бизнесов амбициозными гражданами
        for npc in self.simulation.npcs:
            if not npc.is_alive:
                continue
            ambition = npc.traits.get('ambition', 0.0)
            if ambition > 0.2 and npc.money >= 75000.0:
                already_owner = any(e.owner_id == npc.id for e in self.enterprises.values())
                if not already_owner and random.random() < 0.2:
                    self.found_private_business(npc)

    def found_private_business(self, npc) -> Optional[Enterprise]:
        investment = 40000.0
        if npc.money < investment:
            return None
        npc.money -= investment

        b_types = [
            ("Мастерская", "workshop", "Мастерская"),
            ("Кафе", "cafe", "Кафе"),
            ("Пекарня", "shop", "Пекарня"),
            ("Магазин", "shop", "Магазин")
        ]
        prefix, e_type, b_name_prefix = random.choice(b_types)
        ent_name = f"{prefix} {npc.last_name}"

        city = getattr(self.simulation, 'city', None)
        if not city:
            return None

        from living_world.city.city import Building
        districts = city.districts if hasattr(city, 'districts') and city.districts else []
        target_dist_id = districts[0].id if districts else None

        building = Building(f"{b_name_prefix} {npc.last_name}", "work", 8, district_id=target_dist_id)
        city.add_building(building, district_id=target_dist_id)

        ent = self.create_enterprise(
            name=ent_name,
            enterprise_type=e_type,
            building_id=building.id,
            owner_id=npc.id,
            budget=investment,
            wage_rate=300.0
        )

        if hasattr(self.simulation, 'event_aggregator'):
            from living_world.engine.observer.world_event import EventType, EventImportance
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.ECONOMIC,
                importance=EventImportance.HIGH,
                message=f"💼 {npc.get_full_name()} вложил(а) {investment:,.0f} ₽ и открыл(а) собственное предприятие '{ent.name}'!",
                participants=[npc.id]
            )
        return ent

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
