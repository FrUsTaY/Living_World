import uuid
from typing import List, Optional, Dict
from living_world.city.city import Building
from living_world.city.district import District
from living_world.engine.event_bus import bus
from living_world.engine.observer.world_event import EventType, EventImportance

class ConstructionProject:
    """
    Строительный проект в городе.
    Требует труда строителей для завершения и ввода здания в эксплуатацию.
    """
    def __init__(
        self,
        name: str,
        building_type: str,
        target_capacity: int = 4,
        enterprise_type: Optional[str] = None,
        district_id: Optional[str] = None,
        project_id: Optional[str] = None,
        progress: float = 0.0,
        cost: float = 30000.0,
        is_completed: bool = False,
        commissioner_id: Optional[str] = None
    ):
        self.commissioner_id = commissioner_id
        self.id = project_id or str(uuid.uuid4())
        self.name = name
        self.building_type = building_type  # 'home', 'work'
        self.target_capacity = target_capacity
        self.enterprise_type = enterprise_type  # 'workshop', 'cafe', 'shop', 'farm', etc.
        self.district_id = district_id
        self.progress = float(progress)  # 0.0 to 100.0
        self.cost = float(cost)
        self.is_completed = is_completed

    def advance(self, amount: float = 1.0) -> bool:
        if not self.is_completed:
            self.progress = min(100.0, self.progress + amount)
            if self.progress >= 100.0:
                self.is_completed = True
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "building_type": self.building_type,
            "target_capacity": self.target_capacity,
            "enterprise_type": self.enterprise_type,
            "district_id": self.district_id,
            "progress": self.progress,
            "cost": self.cost,
            "is_completed": self.is_completed,
            "commissioner_id": self.commissioner_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ConstructionProject':
        return cls(
            name=data["name"],
            building_type=data["building_type"],
            target_capacity=data.get("target_capacity", 4),
            enterprise_type=data.get("enterprise_type"),
            district_id=data.get("district_id"),
            project_id=data["id"],
            progress=data.get("progress", 0.0),
            cost=data.get("cost", 30000.0),
            is_completed=data.get("is_completed", False),
            commissioner_id=data.get("commissioner_id")
        )


class ConstructionManager:
    """
    Управляет градостроительным развитием:
    - Оценивает потребность города в новом жилье и рабочих местах
    - Инициирует строительные проекты
    - Координирует работу строителей
    - Создает новые районы при расширении городской черты
    """
    def __init__(self, simulation):
        self.simulation = simulation
        self.active_projects: List[ConstructionProject] = []
        self.completed_projects: List[ConstructionProject] = []

    def get_or_create_target_district(self) -> District:
        city = self.simulation.city
        if not city.districts:
            center = District("Центральный район", "center")
            city.add_district(center)
            # Привязываем существующие здания к центру
            for b in city.buildings:
                center.add_building(b.id)
                b.district_id = center.id

        # Ищем жилой район с менее чем 8 зданиями
        for d in city.districts:
            if d.district_type in ["residential", "suburb"] and len(d.building_ids) < 8:
                return d

        # Если все районы заполнены — основываем новый район!
        names_pool = [
            "Заречный район", "Северный жилой массив", "Зеленый квартал",
            "Южный пригород", "Восточный квартал", "Парковый район", "Солнечный микрорайон"
        ]
        idx = len(city.districts) - 1
        d_name = names_pool[idx % len(names_pool)] if idx >= 0 else "Новый район"
        new_district = District(d_name, "residential")
        city.add_district(new_district)

        self.simulation.event_aggregator.publish_event(
            event_type=EventType.ECONOMIC,
            importance=EventImportance.HIGH,
            message=f"🗺 Город расширяется! Основан новый район: '{new_district.name}'.",
            participants=[]
        )
        return new_district

    def evaluate_city_growth(self):
        """
        Ежедневный аудит инфраструктуры города:
        1. Проверка нехватки жилья
        2. Проверка нехватки предприятий
        """
        city = self.simulation.city
        alive_npcs = [n for n in self.simulation.npcs if n.is_alive]
        total_pop = len(alive_npcs)

        homes = city.get_homes()
        total_capacity = sum(h.capacity for h in homes)

        # 1. Спрос на жилье: если свободных мест <= 3 или заселенность >= 85%
        has_active_home_project = any(p.building_type == "home" and not p.is_completed for p in self.active_projects)
        free_slots = total_capacity - total_pop

        if (free_slots <= 3 or (total_capacity > 0 and total_pop / total_capacity >= 0.85)) and not has_active_home_project:
            district = self.get_or_create_target_district()
            next_num = len(homes) + len(self.active_projects) + 1
            project = ConstructionProject(
                name=f"Дом №{next_num}",
                building_type="home",
                target_capacity=4,
                district_id=district.id,
                cost=40000.0
            )
            self.active_projects.append(project)

            self.simulation.event_aggregator.publish_event(
                event_type=EventType.ECONOMIC,
                importance=EventImportance.MEDIUM,
                message=f"🏗 В связи с ростом населения начато строительство жилого объекта '{project.name}' в районе '{district.name}'.",
                participants=[]
            )

        # 2. Спрос на коммерческие объекты: 1 предприятие на каждые 6-8 жителей
        enterprises_cnt = len(self.simulation.economy_manager.enterprises) if hasattr(self.simulation, "economy_manager") else len(city.get_workplaces())
        has_active_work_project = any(p.building_type == "work" and not p.is_completed for p in self.active_projects)

        if total_pop >= 20 and (enterprises_cnt * 6 < total_pop) and not has_active_work_project:
            district = self.get_or_create_target_district()
            catalog = [
                ("Новая пекарня", "shop"),
                ("Ремонтная мастерская", "workshop"),
                ("Уютное кафе", "cafe"),
                ("Городская аптека", "shop"),
                ("Сельхозферма", "farm")
            ]
            choice_idx = enterprises_cnt % len(catalog)
            biz_name, biz_type = catalog[choice_idx]
            full_name = f"{biz_name} №{enterprises_cnt + 1}"

            project = ConstructionProject(
                name=full_name,
                building_type="work",
                target_capacity=8,
                enterprise_type=biz_type,
                district_id=district.id,
                cost=60000.0
            )
            self.active_projects.append(project)

            self.simulation.event_aggregator.publish_event(
                event_type=EventType.ECONOMIC,
                importance=EventImportance.MEDIUM,
                message=f"🏗 Растущий город привлекает инвестиции: заложен фундамент предприятия '{project.name}'.",
                participants=[]
            )

        # 3. Муниципальные инвестиции города в общественную инфраструктуру
        econ = getattr(self.simulation, "economy_manager", None)
        if econ and econ.city_treasury >= 120000.0 and total_pop >= 25 and not any(p.building_type == "park" for p in self.active_projects):
            parks_cnt = len(city.get_places_by_type("park"))
            districts_cnt = len(city.districts)
            if parks_cnt < districts_cnt:
                district = self.get_or_create_target_district()
                park_cost = 30000.0
                econ.city_treasury -= park_cost
                project = ConstructionProject(
                    name=f"Сквер '{district.name}'",
                    building_type="park",
                    target_capacity=25,
                    district_id=district.id,
                    cost=park_cost
                )
                self.active_projects.append(project)
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.ECONOMIC,
                    importance=EventImportance.HIGH,
                    message=f"🏛 Муниципалитет выделил {park_cost:,.0f} ₽ на благоустройство нового сквера в районе '{district.name}'!",
                    participants=[]
                )

        # 4. Частные заказы на строительство домов от зажиточных горожан
        for npc in alive_npcs:
            if npc.money >= 60000.0:
                current_home_occupants = sum(1 for n in alive_npcs if n.home_id == npc.home_id)
                if current_home_occupants >= 3 or getattr(npc, 'family_id', None) is not None:
                    already_commissioned = any(p.commissioner_id == npc.id for p in self.active_projects)
                    if not already_commissioned and random.random() < 0.2:
                        self.order_private_home(npc)

    def order_private_home(self, npc, house_name: Optional[str] = None) -> Optional[ConstructionProject]:
        cost = 35000.0
        if npc.money < cost:
            return None

        npc.money -= cost
        district = self.get_or_create_target_district()
        final_name = house_name or f"Усадьба {npc.last_name}"

        project = ConstructionProject(
            name=final_name,
            building_type="home",
            target_capacity=5,
            district_id=district.id,
            cost=cost,
            commissioner_id=npc.id
        )
        self.active_projects.append(project)

        self.simulation.event_aggregator.publish_event(
            event_type=EventType.ECONOMIC,
            importance=EventImportance.HIGH,
            message=f"🏡 {npc.get_full_name()} профинансировал(а) строительство семейного дома '{project.name}' ({district.name}).",
            participants=[npc.id]
        )
        return project

    def advance_construction(self, builder_npc, minutes: float = 1.0) -> Optional[ConstructionProject]:
        """
        Строитель трудится на стройплощадке.
        Продвигает первый незавершенный проект.
        """
        if not self.active_projects:
            return None

        project = self.active_projects[0]
        # 1 минута труда строителя добавляет 0.25% к прогрессу (~400 минут = 1 рабочий день на дом)
        completed = project.advance(amount=0.25 * minutes)

        if completed:
            self._finalize_completed_project(project)
            return project
        return None

    def _finalize_completed_project(self, project: ConstructionProject):
        self.active_projects.remove(project)
        self.completed_projects.append(project)

        city = self.simulation.city
        b = Building(
            name=project.name,
            b_type=project.building_type,
            capacity=project.target_capacity,
            district_id=project.district_id
        )
        city.add_building(b, district_id=project.district_id)

        district_name = "Город"
        if project.district_id:
            d = city.get_district(project.district_id)
            if d:
                district_name = d.name

        if project.building_type == "home":
            # Регистрируем новое домохозяйство
            hh = self.simulation.household_manager.create_household(b.id) if hasattr(self.simulation, "household_manager") else None

            # Если дом построен по частному заказу конкретного жителя
            if project.commissioner_id:
                commissioner = next((n for n in self.simulation.npcs if n.id == project.commissioner_id and n.is_alive), None)
                if commissioner:
                    commissioner.home_id = b.id
                    if hh: commissioner.household_id = hh.id

                    # Переселяем супруга и детей заказчика
                    spouse = self.simulation.family_manager.get_spouse(commissioner.id) if hasattr(self.simulation, 'family_manager') else None
                    if spouse and spouse.is_alive:
                        spouse.home_id = b.id
                        if hh: spouse.household_id = hh.id

                    children = self.simulation.family_manager.get_children(commissioner.id) if hasattr(self.simulation, 'family_manager') else []
                    for c in children:
                        if c.is_alive and c.get_age(self.simulation.time.current_datetime) < 18:
                            c.home_id = b.id
                            if hh: c.household_id = hh.id

                    self.simulation.event_aggregator.publish_event(
                        event_type=EventType.MOVE,
                        importance=EventImportance.HIGH,
                        message=f"🎉 Семья {commissioner.get_full_name()} отпраздновала новоселье в построенном доме '{b.name}'!",
                        participants=[commissioner.id]
                    )
            else:
                # Переселение: ищем взрослых жителей в переполненных домах для новоселья
                self._relocate_citizens_to_new_home(b.id, b.capacity)

        elif project.building_type == "work":
            # Регистрируем новое предприятие
            if hasattr(self.simulation, "economy_manager"):
                self.simulation.economy_manager.create_enterprise(
                    name=project.name,
                    enterprise_type=project.enterprise_type or "workshop",
                    building_id=b.id,
                    budget=50000.0
                )

        self.simulation.event_aggregator.publish_event(
            event_type=EventType.ECONOMIC,
            importance=EventImportance.CRITICAL,
            message=f"🏡 Завершено строительство: объект '{project.name}' сдан в эксплуатацию ({district_name})!",
            participants=[]
        )

    def _relocate_citizens_to_new_home(self, new_home_id: str, capacity: int):
        """
        Позволяет взрослым или парам без собственного отдельного жилья заселиться в новый дом.
        """
        moved = 0
        from living_world.engine.life_cycle_manager import LifeStage

        cur_date = self.simulation.time.current_datetime
        for npc in self.simulation.npcs:
            if not npc.is_alive:
                continue
            stage = npc.get_life_stage(cur_date)
            if stage in [LifeStage.YOUNG_ADULT, LifeStage.ADULT]:
                # Проверяем, сколько жителей в его текущем доме
                current_home_occupants = sum(1 for n in self.simulation.npcs if n.is_alive and n.home_id == npc.home_id)
                if current_home_occupants > 3:
                    # Переезжает в новый дом
                    npc.home_id = new_home_id
                    moved += 1
                    if moved >= capacity:
                        break
