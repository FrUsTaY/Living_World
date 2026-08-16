import random
from living_world.population.npc import NPC
from living_world.city.city import Building

MALE_FIRST_NAMES = ["Иван", "Петр", "Александр", "Сергей", "Дмитрий", "Алексей", "Николай", "Михаил", "Андрей", "Владимир"]
FEMALE_FIRST_NAMES = ["Мария", "Анна", "Елена", "Ольга", "Наталья", "Екатерина", "Татьяна", "Ирина", "Светлана", "Юлия"]
LAST_NAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков", "Федоров"]
PROFESSIONS = ["Строитель", "Врач", "Учитель", "Продавец", "Фермер", "Механик", "Инженер", "Пекарь", "Разнорабочий"]

def generate_initial_world(city, simulation, num_npcs=25):
    # Создаем базовые дома
    for i in range(10):
        city.add_building(Building(f"Дом №{i+1}", "home", 4))

    # Создаем базовые рабочие места
    workplaces = ["Ферма", "Мастерская", "Магазин", "Школа", "Стройка"]
    for w in workplaces:
        city.add_building(Building(w, "work", 10))

    homes = city.get_homes()
    works = city.get_workplaces()

    # Счетчик населения в каждом доме
    home_occupants = {h.id: 0 for h in homes}
    home_households = {}

    # Заранее создаем домохозяйства для начальных домов
    for h in homes:
        hh = simulation.household_manager.create_household(h.id)
        home_households[h.id] = hh.id

    for _ in range(num_npcs):
        gender = random.choice(["М", "Ж"])
        if gender == "М":
            first_name = random.choice(MALE_FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
        else:
            first_name = random.choice(FEMALE_FIRST_NAMES)
            last_name = random.choice(LAST_NAMES) + "а"

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

        # Немного рандомизируем начальные потребности
        npc.hunger = random.uniform(70, 100)
        npc.energy = random.uniform(70, 100)

        simulation.add_npc(npc)

    from living_world.engine.event_bus import bus
    bus.publish("log_event", f"Мир создан. Население: {num_npcs} человек.")
