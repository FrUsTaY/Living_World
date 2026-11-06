import random

class WeatherManager:
    WEATHER_TYPES = {
        "Зима": ["Снегопад", "Пасмурно", "Морозно, ясно", "Метель"],
        "Весна": ["Ясно", "Небольшой дождь", "Переменная облачность", "Теплый день"],
        "Лето": ["Солнечно", "Теплый дождь", "Гроза", "Жарко, ясно"],
        "Осень": ["Затяжной дождь", "Туман", "Пасмурно", "Ветрено, ясно"]
    }

    TEMP_RANGES = {
        "Зима": (-18.0, -2.0),
        "Весна": (4.0, 16.0),
        "Лето": (19.0, 31.0),
        "Осень": (3.0, 13.0)
    }

    def __init__(self, simulation):
        self.simulation = simulation
        self.temperature = -8.0
        self.weather_condition = "Снегопад"
        self._last_day = None

    def update_weather(self, current_datetime):
        cur_day = (current_datetime.year, current_datetime.month, current_datetime.day)
        if self._last_day == cur_day:
            return
        self._last_day = cur_day

        season = self.simulation.time.season_name if hasattr(self.simulation, 'time') else "Весна"
        t_min, t_max = self.TEMP_RANGES.get(season, (10.0, 20.0))
        self.temperature = round(random.uniform(t_min, t_max), 1)
        choices = self.WEATHER_TYPES.get(season, ["Ясно"])
        self.weather_condition = random.choice(choices)

        if self.weather_condition in ["Метель", "Гроза"] and hasattr(self.simulation, 'event_aggregator'):
            from living_world.engine.observer.world_event import EventType, EventImportance
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.SOCIAL_INTERACTION,
                importance=EventImportance.LOW,
                message=f"🌧 Погода в городе: {self.weather_condition}, {self.temperature:+.1f}°C.",
                participants=[]
            )

    def get_weather_summary(self) -> str:
        return f"{self.temperature:+.1f}°C, {self.weather_condition}"
