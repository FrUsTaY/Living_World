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
        career_lvl = getattr(npc, 'career_level', 1)
        wage_mult = 1.0 + (career_lvl - 1) * 0.25
        hourly_wage *= wage_mult
        minute_rate = hourly_wage / 60.0
        earned = minute_rate * minutes

        ent = self.get_enterprise_for_building(npc.work_id)
        if ent:
            ent.pay_expense(earned)
            ent.add_employee(npc.id)

        pol = getattr(self.simulation, 'politics_manager', None)
        tax_rate = pol.get_tax_rate() if pol else 0.13
        tax = earned * tax_rate
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

        # 0. Реализация произведенных предприятиями товаров и услуг
        for ent in list(self.enterprises.values()):
            if not ent.is_active:
                continue
            if ent.daily_revenue == 0 and ent.daily_expenses > 0:
                commercial_revenue = round(ent.daily_expenses * 1.30, 2)
                ent.receive_revenue(commercial_revenue)

        # 1. Пенсии пожилым жителям (из городской казны с учетом политики Мэра)
        pol = getattr(self.simulation, 'politics_manager', None)
        daily_pension = pol.get_pension_amount() if pol else 650.0
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

        self.process_labor_market()
        self.process_supply_chains()
        self.process_banking_and_welfare()

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

    def process_labor_market(self):
        from living_world.engine.observer.world_event import EventType, EventImportance
        import random

        # 1. Накопление стажа и повышение квалификации (разряды 1-5)
        for npc in self.simulation.npcs:
            if not npc.is_alive or not npc.work_id or npc.profession in ["Безработный", "Пенсионер"]:
                continue

            if not getattr(npc, 'is_sick', False):
                npc.work_experience_days = getattr(npc, 'work_experience_days', 0) + 1

                cur_lvl = getattr(npc, 'career_level', 1)
                if cur_lvl < 5:
                    exp = npc.work_experience_days
                    diligence = npc.traits.get('diligence', 0.0) if hasattr(npc, 'traits') else 0.0
                    thresholds = {1: 25, 2: 75, 3: 180, 4: 360}
                    req_days = thresholds.get(cur_lvl, 999)
                    if diligence > 0.3:
                        req_days = int(req_days * 0.8)

                    if exp >= req_days:
                        npc.career_level = cur_lvl + 1
                        npc.mood = min(100.0, npc.mood + 15.0)
                        if hasattr(self.simulation, 'event_aggregator'):
                            self.simulation.event_aggregator.publish_event(
                                event_type=EventType.JOB_CHANGE,
                                importance=EventImportance.MEDIUM,
                                message=f"🎖 Повышение квалификации: {npc.get_full_name()} получил(а) {npc.career_level}-й разряд в профессии '{npc.profession}'!",
                                participants=[npc.id]
                            )
                        if hasattr(self.simulation, 'memory_manager'):
                            self.simulation.memory_manager.add_memory(
                                npc.id, None, "Повышение", f"Присвоен {npc.career_level}-й квалификационный разряд", 0.7, 0.8
                            )

        # 2. Сокращение штата убыточными предприятиями
        for ent in list(self.enterprises.values()):
            if ent.is_active and ent.budget < -15000.0 and len(ent.employees) > 1:
                emp_npcs = [n for n in self.simulation.npcs if n.id in ent.employees and n.is_alive]
                if emp_npcs:
                    victim = min(emp_npcs, key=lambda n: getattr(n, 'work_experience_days', 0))
                    ent.remove_employee(victim.id)
                    victim.work_id = None
                    victim.profession = "Безработный"
                    victim.mood = max(0.0, victim.mood - 25.0)
                    if hasattr(self.simulation, 'event_aggregator'):
                        self.simulation.event_aggregator.publish_event(
                            event_type=EventType.JOB_CHANGE,
                            importance=EventImportance.HIGH,
                            message=f"📉 Сокращение штата: {victim.get_full_name()} уволен(а) из {ent.name} из-за убытков предприятия.",
                            participants=[victim.id]
                        )

        # 3. Биржа труда: наем безработных на предприятия с открытыми вакансиями
        current_date = self.simulation.time.current_datetime
        unemployed = [
            n for n in self.simulation.npcs
            if n.is_alive and (n.profession == "Безработный" or not n.work_id) and 18 <= n.get_age(current_date) < 65 and getattr(n, 'jail_days', 0) == 0
        ]

        if unemployed:
            active_enterprises = [e for e in self.enterprises.values() if e.is_active and e.budget >= 0.0]
            for ent in active_enterprises:
                max_cap = 5
                if len(ent.employees) < max_cap and unemployed:
                    candidate = unemployed.pop(0)
                    candidate.work_id = ent.building_id
                    ent.add_employee(candidate.id)
                    prof_map = {
                        'farm': 'Фермер',
                        'workshop': 'Механик',
                        'construction': 'Строитель',
                        'shop': 'Продавец',
                        'cafe': 'Повар',
                        'hospital': 'Врач',
                        'school': 'Учитель'
                    }
                    candidate.profession = prof_map.get(ent.enterprise_type, 'Разнорабочий')
                    candidate.career_level = 1
                    if hasattr(self.simulation, 'event_aggregator'):
                        self.simulation.event_aggregator.publish_event(
                            event_type=EventType.JOB_CHANGE,
                            importance=EventImportance.LOW,
                            message=f"💼 Биржа труда: {candidate.get_full_name()} принят(а) в {ent.name} на должность '{candidate.profession}'.",
                            participants=[candidate.id]
                        )

    def process_supply_chains(self):
        # 1. Производство сырья на фермах
        farms = [e for e in self.enterprises.values() if e.is_active and e.enterprise_type == 'farm']
        for farm in farms:
            produced_raw = max(5.0, len(farm.employees) * 10.0)
            farm.raw_materials += produced_raw

        # 2. Мастерские и магазины закупают сырье у ферм
        processors = [e for e in self.enterprises.values() if e.is_active and e.enterprise_type in ['workshop', 'shop']]
        for proc in processors:
            needed = 15.0
            for farm in farms:
                if farm.raw_materials >= 5.0 and proc.budget >= 300.0:
                    bought = min(needed, farm.raw_materials)
                    cost = bought * 20.0
                    if proc.budget >= cost:
                        proc.pay_expense(cost)
                        farm.receive_revenue(cost)
                        farm.raw_materials -= bought
                        proc.raw_materials += bought
                        needed -= bought
                if needed <= 0:
                    break

            if proc.raw_materials >= 5.0:
                conv = min(proc.raw_materials, 15.0)
                proc.raw_materials -= conv
                proc.finished_goods += conv * 1.5

        # 3. Кафе закупают готовую продукцию у магазинов
        cafes = [e for e in self.enterprises.values() if e.is_active and e.enterprise_type == 'cafe']
        shops = [e for e in self.enterprises.values() if e.is_active and e.enterprise_type == 'shop']
        for cafe in cafes:
            if cafe.finished_goods < 20.0 and shops and cafe.budget >= 300.0:
                supplier = max(shops, key=lambda s: s.finished_goods)
                if supplier.finished_goods >= 10.0:
                    transfer_goods = min(15.0, supplier.finished_goods)
                    cost = transfer_goods * 25.0
                    if cafe.budget >= cost:
                        cafe.pay_expense(cost)
                        supplier.receive_revenue(cost)
                        supplier.finished_goods -= transfer_goods
                        cafe.finished_goods += transfer_goods

    def process_banking_and_welfare(self):
        from living_world.engine.observer.world_event import EventType, EventImportance
        from living_world.engine.life_cycle_manager import LifeStage

        # 1. Погашение ипотечных кредитов
        for npc in self.simulation.npcs:
            if not npc.is_alive:
                continue
            if getattr(npc, 'mortgage_debt', 0.0) > 0:
                pay = min(npc.money, getattr(npc, 'mortgage_payment', 100.0))
                if pay > 0:
                    npc.money -= pay
                    npc.mortgage_debt = max(0.0, npc.mortgage_debt - pay)
                    self.city_treasury += pay
                    if npc.mortgage_debt == 0.0:
                        npc.mortgage_payment = 0.0
                        if hasattr(self.simulation, 'event_aggregator'):
                            self.simulation.event_aggregator.publish_event(
                                event_type=EventType.ECONOMIC,
                                importance=EventImportance.HIGH,
                                message=f"🎉 {npc.get_full_name()} полностью выплатил(а) ипотечный кредит за жилье!",
                                participants=[npc.id]
                            )

        # 2. Выплата детских пособий матерям с младенцами
        pol = getattr(self.simulation, 'politics_manager', None)
        allowance = pol.get_child_allowance() if pol else 200.0
        current_date = self.simulation.time.current_datetime
        for npc in self.simulation.npcs:
            if npc.is_alive and npc.gender == 'Ж':
                children = self.simulation.family_manager.get_children(npc.id) if hasattr(self.simulation, 'family_manager') else []
                has_baby = any(c.is_alive and c.get_life_stage(current_date) == LifeStage.BABY for c in children)
                if has_baby and self.city_treasury >= allowance:
                    self.city_treasury -= allowance
                    npc.money += allowance
