from typing import List, Dict, Optional
from datetime import datetime

class CityChronicle:
    """
    Городская хроника и ежемесячный 'Вестник Города'.
    Формирует и хранит исторические выпуски новостей, отражающие жизнь города.
    """
    MONTH_NAMES = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    def __init__(self, simulation):
        self.simulation = simulation
        self.editions: List[Dict] = []
        self._last_published_month = None

    def check_and_publish_monthly(self, current_datetime: datetime):
        month_key = (current_datetime.year, current_datetime.month)
        if self._last_published_month == month_key:
            return

        # Публикуем выпуск в первый день месяца в 09:00
        if current_datetime.day == 1 and current_datetime.hour >= 9:
            self._last_published_month = month_key
            self.publish_edition(current_datetime)

    def publish_edition(self, current_datetime: datetime) -> Dict:
        prev_month = current_datetime.month - 1 if current_datetime.month > 1 else 12
        year = current_datetime.year if current_datetime.month > 1 else current_datetime.year - 1
        m_name = self.MONTH_NAMES[prev_month]

        articles = []
        headline = f"Итоги месяца: жизнь и развитие нашего города в {m_name}е {year} г."

        # 1. Демография
        total_pop = sum(1 for n in self.simulation.npcs if n.is_alive)
        articles.append(f"Население города составляет {total_pop} жителей.")

        # 2. Экономика
        treasury = getattr(self.simulation.economy_manager, 'city_treasury', 100000.0) if hasattr(self.simulation, 'economy_manager') else 100000.0
        articles.append(f"Баланс городской казны: {treasury:,.0f} ₽.")

        # 3. Знаковые события из журнала
        journal = getattr(self.simulation, 'event_journal', None)
        if journal:
            high_events = [e for e in journal.events if getattr(e, 'importance', None) and e.importance.value in ["HIGH", "CRITICAL"]]
            if high_events:
                recent_events = high_events[-3:]
                for ev in recent_events:
                    articles.append(f"• {ev.message}")

        edition = {
            "month": prev_month,
            "year": year,
            "title": f"«Вестник Города» №{len(self.editions) + 1} ({m_name} {year})",
            "headline": headline,
            "articles": articles,
            "published_at": current_datetime.isoformat()
        }
        self.editions.append(edition)

        if hasattr(self.simulation, 'event_aggregator'):
            from living_world.engine.observer.world_event import EventType, EventImportance
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.SOCIAL_INTERACTION,
                importance=EventImportance.HIGH,
                message=f"📰 Вышел свежий номер «Вестника Города» за {m_name} {year} г. ({len(articles)} новостей).",
                participants=[]
            )

        return edition

    def get_latest_edition(self) -> Optional[Dict]:
        return self.editions[-1] if self.editions else None
