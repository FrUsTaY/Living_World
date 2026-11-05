import uuid
from typing import Optional, List, Dict

class Enterprise:
    """
    Предприятие города (магазин, кафе, ферма, мастерская, школа, стройка и т.д.).
    Может быть муниципальным или принадлежать конкретному NPC.
    """
    def __init__(
        self,
        name: str,
        enterprise_type: str,
        building_id: str,
        owner_id: Optional[str] = None,
        budget: float = 50000.0,
        wage_rate: float = 250.0,
        enterprise_id: Optional[str] = None,
        is_active: bool = True
    ):
        self.id = enterprise_id or str(uuid.uuid4())
        self.name = name
        self.enterprise_type = enterprise_type  # 'shop', 'cafe', 'workshop', 'farm', 'construction', 'school', 'hospital'
        self.building_id = building_id
        self.owner_id = owner_id
        self.budget = float(budget)
        self.wage_rate = float(wage_rate)
        self.is_active = is_active
        self.employees: List[str] = []
        self.daily_revenue: float = 0.0
        self.daily_expenses: float = 0.0

    def add_employee(self, npc_id: str):
        if npc_id not in self.employees:
            self.employees.append(npc_id)

    def remove_employee(self, npc_id: str):
        if npc_id in self.employees:
            self.employees.remove(npc_id)

    def receive_revenue(self, amount: float):
        if amount > 0:
            self.budget += amount
            self.daily_revenue += amount

    def pay_expense(self, amount: float) -> bool:
        if amount <= 0:
            return True
        if self.budget >= amount:
            self.budget -= amount
            self.daily_expenses += amount
            return True
        else:
            # Дефицит бюджета
            self.daily_expenses += amount
            self.budget -= amount
            return False

    def reset_daily_stats(self):
        self.daily_revenue = 0.0
        self.daily_expenses = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.enterprise_type,
            "building_id": self.building_id,
            "owner_id": self.owner_id,
            "budget": self.budget,
            "wage_rate": self.wage_rate,
            "is_active": self.is_active,
            "employees_count": len(self.employees)
        }
