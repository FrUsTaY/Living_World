import random
from typing import Optional, List, Dict
from datetime import datetime

class PoliticsManager:
    """
    Управление политической жизнью города, институтом Мэра, выборами и бюджетной политикой.
    """
    PLATFORMS = {
        "SOCIAL": {
            "name": "Социал-демократическая",
            "tax_rate": 0.18,
            "pension": 850.0,
            "child_allowance": 300.0,
            "description": "Повышенные социальные выплаты, защита уязвимых слоев, налог 18%"
        },
        "MARKET": {
            "name": "Либерально-рыночная",
            "tax_rate": 0.08,
            "pension": 500.0,
            "child_allowance": 150.0,
            "description": "Минимальные налоги 8%, стимулы для частного предпринимательства"
        },
        "URBANIST": {
            "name": "Инфраструктурно-технократическая",
            "tax_rate": 0.13,
            "pension": 650.0,
            "child_allowance": 200.0,
            "description": "Сбалансированный налог 13%, упор на парки, школы, дороги и капремонт"
        }
    }

    def __init__(self, simulation):
        self.simulation = simulation
        self.current_mayor_id: Optional[str] = None
        self.mayor_platform: str = "URBANIST"
        self.approval_rating: float = 75.0
        self.days_in_office: int = 0
        self.election_cycle_days: int = 1095  # 3 года
        self.days_until_election: int = 365
        self.low_approval_streak: int = 0

    def get_tax_rate(self) -> float:
        return self.PLATFORMS.get(self.mayor_platform, self.PLATFORMS["URBANIST"])["tax_rate"]

    def get_pension_amount(self) -> float:
        return self.PLATFORMS.get(self.mayor_platform, self.PLATFORMS["URBANIST"])["pension"]

    def get_child_allowance(self) -> float:
        return self.PLATFORMS.get(self.mayor_platform, self.PLATFORMS["URBANIST"])["child_allowance"]

    def get_mayor(self) -> Optional['NPC']:
        if not self.current_mayor_id:
            return None
        return next((n for n in self.simulation.npcs if n.id == self.current_mayor_id and n.is_alive), None)

    def daily_update(self, current_datetime: datetime):
        self.days_until_election -= 1
        if self.current_mayor_id:
            self.days_in_office += 1
            mayor = self.get_mayor()
            if not mayor:
                # Мэр умер или покинул город — досрочные выборы
                self.trigger_election(current_datetime, reason="кончины действующего градоначальника")
                return

            # Выплата зарплаты Мэру из казны
            if hasattr(self.simulation, 'economy_manager'):
                econ = self.simulation.economy_manager
                salary = 600.0
                if econ.city_treasury >= salary:
                    econ.city_treasury -= salary
                    mayor.money += salary

            # Расчет рейтинга одобрения Мэра
            self._evaluate_approval_rating()

            if self.approval_rating < 25.0:
                self.low_approval_streak += 1
                if self.low_approval_streak >= 60:
                    # Вотум недоверия
                    self.trigger_election(current_datetime, reason="вотума недоверия из-за падения рейтинга ниже 25%")
                    return
            else:
                self.low_approval_streak = 0

        # Очередные выборы
        if self.days_until_election <= 0:
            self.trigger_election(current_datetime, reason="истечения трехлетнего срока полномочий")

    def _evaluate_approval_rating(self):
        rating = 50.0
        econ = getattr(self.simulation, 'economy_manager', None)
        if econ:
            # Казна
            if econ.city_treasury > 100000.0:
                rating += 20.0
            elif econ.city_treasury < 20000.0:
                rating -= 25.0

        alive_npcs = [n for n in self.simulation.npcs if n.is_alive]
        if alive_npcs:
            # Бедность / голод
            starving_cnt = sum(1 for n in alive_npcs if n.hunger < 15.0 or n.money < 300.0)
            rating -= (starving_cnt / len(alive_npcs)) * 40.0

            # Среднее настроение
            avg_mood = sum(getattr(n, 'mood', 50.0) for n in alive_npcs) / len(alive_npcs)
            rating += (avg_mood - 50.0) * 0.4

        self.approval_rating = max(5.0, min(98.0, round(rating, 1)))

    def trigger_election(self, current_datetime: datetime, reason: str = "плановых выборов"):
        alive_npcs = [n for n in self.simulation.npcs if n.is_alive and n.get_age(current_datetime) >= 18]
        if len(alive_npcs) < 2:
            self.days_until_election = 365
            return

        # Подбор кандидатов: возраст 30+, высокий капитал или высокий разряд или высокая амбиция
        potential_candidates = [
            n for n in alive_npcs
            if n.get_age(current_datetime) >= 30 and (n.money >= 5000.0 or getattr(n, 'career_level', 1) >= 2 or n.traits.get('ambition', 0) > 0.0)
        ]
        if not potential_candidates:
            potential_candidates = alive_npcs

        candidates_pool = random.sample(potential_candidates, min(3, len(potential_candidates)))
        candidate_platforms = {}
        platform_keys = list(self.PLATFORMS.keys())

        for idx, cand in enumerate(candidates_pool):
            # Кандидат выбирает платформу по профилю
            if cand.money >= 40000.0 or any(e.owner_id == cand.id for e in getattr(self.simulation.economy_manager, 'enterprises', {}).values()):
                platform = "MARKET"
            elif cand.profession in ["Строитель", "Инженер"]:
                platform = "URBANIST"
            else:
                platform = "SOCIAL"
            candidate_platforms[cand.id] = platform

        # Голосование избирателей
        votes = {c.id: 0 for c in candidates_pool}
        from living_world.engine.life_cycle_manager import LifeStage

        for voter in alive_npcs:
            scores = {}
            voter_age = voter.get_age(current_datetime)
            voter_stage = voter.get_life_stage(current_datetime)
            voter_money = voter.money
            children = self.simulation.family_manager.get_children(voter.id) if hasattr(self.simulation, 'family_manager') else []
            has_babies = any(c.is_alive and c.get_life_stage(current_datetime) == LifeStage.BABY for c in children)

            for cand in candidates_pool:
                score = 10.0
                cand_platform = candidate_platforms[cand.id]

                # Классовые предпочтения
                if cand_platform == "SOCIAL":
                    if voter.profession == "Пенсионер" or voter_age >= 65:
                        score += 50.0
                    if has_babies or voter.gender == 'Ж':
                        score += 30.0
                    if voter_money < 3000.0:
                        score += 40.0
                elif cand_platform == "MARKET":
                    if voter_money > 35000.0 or cand.id == voter.id:
                        score += 45.0
                    if voter.traits.get('frugality', 0) > 0.3:
                        score += 25.0
                elif cand_platform == "URBANIST":
                    if len(children) > 0:
                        score += 35.0
                    if voter.profession in ["Строитель", "Инженер", "Механик"]:
                        score += 30.0

                # Личная симпатия / знакомство
                if hasattr(self.simulation, 'relationship_manager'):
                    rel = self.simulation.relationship_manager.get_relationship(voter.id, cand.id)
                    score += rel.get('affinity', 0) * 0.3
                    score += rel.get('trust', 0) * 0.3

                scores[cand.id] = max(1.0, score)

            chosen_cand_id = max(scores, key=scores.get)
            votes[chosen_cand_id] += 1

        winner_id = max(votes, key=votes.get)
        winner = next(c for c in candidates_pool if c.id == winner_id)
        chosen_platform = candidate_platforms[winner_id]

        self.current_mayor_id = winner_id
        self.mayor_platform = chosen_platform
        self.days_in_office = 0
        self.days_until_election = self.election_cycle_days
        self.low_approval_streak = 0
        self.approval_rating = 75.0

        p_info = self.PLATFORMS[chosen_platform]
        total_votes = len(alive_npcs)

        if hasattr(self.simulation, 'memory_manager'):
            self.simulation.memory_manager.add_memory(
                winner.id, None, "Выборы Мэра", f"Избран(а) Мэром города ({p_info['name']})", 1.0, 1.0
            )

        if hasattr(self.simulation, 'event_aggregator'):
            from living_world.engine.observer.world_event import EventType, EventImportance
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.SOCIAL_INTERACTION,
                importance=EventImportance.HIGH,
                message=f"🏛 Выборы Мэра по причине {reason}: победу одержал(а) {winner.get_full_name()} ({p_info['name']} программа) с {votes[winner_id]}/{total_votes} голосов!",
                participants=[winner.id]
            )

    def to_dict(self) -> dict:
        return {
            "current_mayor_id": self.current_mayor_id,
            "mayor_platform": self.mayor_platform,
            "approval_rating": self.approval_rating,
            "days_in_office": self.days_in_office,
            "days_until_election": self.days_until_election,
            "low_approval_streak": self.low_approval_streak
        }

    def load_from_dict(self, data: dict):
        if not data:
            return
        self.current_mayor_id = data.get("current_mayor_id")
        self.mayor_platform = data.get("mayor_platform", "URBANIST")
        self.approval_rating = float(data.get("approval_rating", 75.0))
        self.days_in_office = int(data.get("days_in_office", 0))
        self.days_until_election = int(data.get("days_until_election", 365))
        self.low_approval_streak = int(data.get("low_approval_streak", 0))
