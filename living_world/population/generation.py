import random
from living_world.population.npc import NPC
from living_world.city.city import Building

MALE_FIRST_NAMES = ["Иван", "Петр", "Александр", "Сергей", "Дмитрий", "Алексей", "Николай", "Михаил", "Андрей", "Владимир"]
FEMALE_FIRST_NAMES = ["Мария", "Анна", "Елена", "Ольга", "Наталья", "Екатерина", "Татьяна", "Ирина", "Светлана", "Юлия"]
LAST_NAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков", "Федоров"]
PROFESSIONS = ["Строитель", "Врач", "Учитель", "Продавец", "Фермер", "Механик", "Инженер", "Пекарь", "Разнорабочий"]

def generate_initial_world(city, simulation, num_npcs=25):
    from living_world.city.district import District

    center = District("Центральный район", "center")
    res_dist = District("Жилой район №1", "residential")
    city.add_district(center)
    city.add_district(res_dist)

    # Создаем базовые дома
    for i in range(10):
        b = Building(f"Дом №{i+1}", "home", 4, district_id=res_dist.id)
        city.add_building(b, district_id=res_dist.id)

    # Создаем базовые рабочие места и предприятия
    workplaces_data = [
        ("Ферма", "farm", 35000.0),
        ("Мастерская", "workshop", 45000.0),
        ("Магазин", "shop", 50000.0),
        ("Школа", "school", 60000.0),
        ("Стройка", "construction", 55000.0)
    ]
    for w_name, e_type, budget in workplaces_data:
        b = Building(w_name, "work", 10, district_id=center.id)
        city.add_building(b, district_id=center.id)
        if hasattr(simulation, 'economy_manager'):
            simulation.economy_manager.create_enterprise(w_name, e_type, b.id, budget=budget)

    city.add_building(Building("Городской парк", "park", 30, district_id=center.id), district_id=center.id)

    b_cafe = Building("Городское кафе", "cafe", 15, district_id=center.id)
    city.add_building(b_cafe, district_id=center.id)
    if hasattr(simulation, 'economy_manager'):
        simulation.economy_manager.create_enterprise("Городское кафе", "cafe", b_cafe.id, budget=40000.0)

    b_shop = Building("Центральный магазин", "shop", 15, district_id=center.id)
    city.add_building(b_shop, district_id=center.id)
    if hasattr(simulation, 'economy_manager'):
        simulation.economy_manager.create_enterprise("Центральный магазин", "shop", b_shop.id, budget=60000.0)

    homes = city.get_homes()
    works = city.get_workplaces()

    # Счетчик населения в каждом доме
    home_occupants = {h.id: 0 for h in homes}
    home_households = {}

    # Заранее создаем домохозяйства для начальных домов
    for h in homes:
        hh = simulation.household_manager.create_household(h.id)
        home_households[h.id] = hh.id

    generated_names = set()

    for i in range(num_npcs):
        gender = "М" if i % 2 == 0 else "Ж"

        # Ensure unique full names
        attempts = 0
        while True:
            if gender == "М":
                first_name = random.choice(MALE_FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
            else:
                first_name = random.choice(FEMALE_FIRST_NAMES)
                last_name = random.choice(LAST_NAMES) + "а"

            full_name = f"{first_name} {last_name}"
            if full_name not in generated_names or attempts > 100:
                generated_names.add(full_name)
                break
            attempts += 1

        # Generate age safely (YOUNG_ADULT and ADULT) to avoid independent children
        age = random.randint(20, 50)

        # Calculate date_of_birth relative to the simulation start time
        current_date = simulation.time.current_datetime
        from datetime import timedelta
        # Simple approximation, adding a bit of randomness to days so birthdays aren't all on Jan 1
        days_old = int(age * 365.25) + random.randint(-180, 180)
        date_of_birth = current_date - timedelta(days=days_old)

        profession = random.choice(PROFESSIONS)

        # Находим дом со свободными местами
        available_homes = [h for h in homes if home_occupants[h.id] < h.capacity]
        if not available_homes:
            # Если не хватило мест (например, генерация большого кол-ва жителей), спавним новый дом
            new_home = Building(f"Дом №{len(homes)+1}", "home", 4)
            city.add_building(new_home)
            homes.append(new_home)
            home_occupants[new_home.id] = 0

            # Создаем новое домохозяйство
            hh = simulation.household_manager.create_household(new_home.id)
            home_households[new_home.id] = hh.id

            available_homes = [new_home]

        home = random.choice(available_homes)
        home_occupants[home.id] += 1

        work = random.choice(works)

        npc = NPC(first_name, last_name, date_of_birth, gender, profession, home.id, work.id)
        npc.household_id = home_households[home.id]

        # Начальный капитал и привязка к предприятию
        npc.money = float(random.randint(2000, 8000))
        if hasattr(simulation, 'economy_manager'):
            ent = simulation.economy_manager.get_enterprise_for_building(work.id)
            if ent:
                ent.add_employee(npc.id)

        # Немного рандомизируем начальные потребности
        npc.hunger = random.uniform(70, 100)
        npc.energy = random.uniform(70, 100)

        simulation.add_npc(npc)

    from living_world.engine.event_bus import bus
    bus.publish("log_event", f"Мир создан. Население: {num_npcs} человек.")
