from typing import Dict, List
import random
from datetime import datetime
from living_world.engine.education.models import EducationalInstitution, EducationProgram, EducationHistoryRecord
from living_world.engine.event_bus import bus

class EducationManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.institutions: Dict[str, EducationalInstitution] = {}
        self.programs: Dict[str, EducationProgram] = {}
        self.history: List[EducationHistoryRecord] = []

    def add_institution(self, institution: EducationalInstitution):
        self.institutions[institution.id] = institution

    def add_program(self, program: EducationProgram):
        self.programs[program.id] = program

    def update_npc_education(self, npc, time_dict):
        if not npc.is_alive:
            return

        current_world_date = datetime(
            time_dict.get('year', 2000),
            time_dict.get('month', 1),
            time_dict.get('day', 1),
            time_dict['hour'],
            time_dict['minute']
        )

        age = npc.get_age(current_world_date)
        status = getattr(npc, 'education_status', None)
        current_prog_id = getattr(npc, 'current_education_id', None)

        if status == "Обучается" and current_prog_id:
            self._process_active_education(npc, current_prog_id, current_world_date)
        else:
            self._process_new_education_decisions(npc, age, current_world_date)

    def _process_active_education(self, npc, prog_id: str, current_world_date: datetime):
        records = [r for r in self.history if r.npc_id == npc.id and r.program_id == prog_id and r.status == "Обучается"]
        if not records:
            return

        record = records[-1]
        prog = self.programs.get(prog_id)
        if not prog:
             return

        start_date = datetime.fromisoformat(record.start_date)
        years_passed = current_world_date.year - start_date.year

        if years_passed >= prog.duration:
             self._complete_education(npc, record, prog, current_world_date)
        else:
             if random.random() < 0.001 and npc.traits.get('patience', 0) < -0.5:
                 self._dropout(npc, record, prog, current_world_date)

    def _complete_education(self, npc, record: EducationHistoryRecord, prog: EducationProgram, current_world_date: datetime):
        record.status = "Окончил"
        record.end_date = current_world_date.isoformat()

        if prog.type == "school_9":
            record.qualification = "Основное общее образование"
        elif prog.type == "school_11":
            record.qualification = "Среднее общее образование"
        elif prog.type == "bachelor":
            record.qualification = "Бакалавр"
        elif prog.type == "college":
            record.qualification = "СПО"

        npc.current_education_id = None
        npc.education_status = None

        inst = self.institutions.get(prog.institution_id)
        if inst:
             inst.unenroll(npc.id)

        from living_world.engine.observer.world_event import EventType, EventImportance
        if hasattr(self.simulation, 'event_aggregator'):
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.EDUCATION_GRADUATE,
                importance=EventImportance.HIGH,
                message=f"{npc.get_full_name()} успешно окончил обучение по программе {prog.name}.",
                participants=[npc.id],
                data={"program_name": prog.name, "qualification": record.qualification}
            )
        else:
            bus.publish("log_event", f"{npc.get_full_name()} успешно окончил обучение по программе {prog.name}.")

    def _dropout(self, npc, record: EducationHistoryRecord, prog: EducationProgram, current_world_date: datetime):
        record.status = "Отчислен"
        record.end_date = current_world_date.isoformat()
        npc.current_education_id = None
        npc.education_status = None

        inst = self.institutions.get(prog.institution_id)
        if inst:
             inst.unenroll(npc.id)

        from living_world.engine.observer.world_event import EventType, EventImportance
        if hasattr(self.simulation, 'event_aggregator'):
            self.simulation.event_aggregator.publish_event(
                event_type=EventType.EDUCATION_EXPEL,
                importance=EventImportance.HIGH,
                message=f"{npc.get_full_name()} был отчислен с программы {prog.name}.",
                participants=[npc.id],
                data={"program_name": prog.name}
            )
        else:
            bus.publish("log_event", f"{npc.get_full_name()} был отчислен с программы {prog.name}.")

    def _process_new_education_decisions(self, npc, age: int, current_world_date: datetime):
        # 1. Eligibility (что NPC может делать по возрасту/квалификации)
        eligible_for = []

        if 3 <= age <= 6:
             eligible_for.append("kindergarten")
        elif 7 <= age <= 15 and not self._has_qualification(npc.id, "Основное общее образование") and not self._has_qualification(npc.id, "Среднее общее образование"):
             eligible_for.append("school_9")
        elif 16 <= age <= 17 and self._has_qualification(npc.id, "Основное общее образование") and not self._has_qualification(npc.id, "Среднее общее образование"):
             eligible_for.extend(["school_11", "college"])
        elif age >= 18 and age < 25 and (self._has_qualification(npc.id, "Среднее общее образование") or self._has_qualification(npc.id, "СПО")):
             if not self._has_qualification(npc.id, "Бакалавр"):
                 eligible_for.append("bachelor")

        if not eligible_for:
            return

        # 2. Decision (что NPC решает делать)
        decision = None

        # Автоматическое (обязательное) зачисление
        if "kindergarten" in eligible_for:
            decision = "kindergarten"
        elif "school_9" in eligible_for:
            decision = "school_9"
        else:
            # Для дальнейшего образования - взвешенный выбор
            choices = []
            if "school_11" in eligible_for: choices.append("school_11")
            if "college" in eligible_for: choices.append("college")
            if "bachelor" in eligible_for: choices.append("bachelor")

            # Добавляем вариант "ничего не делать / работать"
            choices.append("none")

            # TODO: В будущем вес выбора будет зависеть от денег, семьи, целей.
            # Сейчас - базовые вероятности с учетом черт характера
            weights = []
            for choice in choices:
                if choice == "none":
                    weight = 30 + (npc.traits.get('boldness', 0) * 10)
                elif choice == "bachelor":
                    weight = 40 + (npc.traits.get('patience', 0) * 20)
                elif choice == "college":
                    weight = 40 + (npc.traits.get('patience', 0) * 10)
                elif choice == "school_11":
                    weight = 50 + (npc.traits.get('patience', 0) * 15)
                weights.append(max(1, weight))

            decision = random.choices(choices, weights=weights)[0]

        if decision and decision != "none":
            # 3. Enrollment
            self._try_enroll(npc, decision, current_world_date)

    def _try_enroll(self, npc, prog_type: str, current_world_date: datetime):
        available_progs = [p for p in self.programs.values() if p.type == prog_type]
        if not available_progs:
            return

        prog = random.choice(available_progs)
        inst = self.institutions.get(prog.institution_id)

        if inst and inst.enroll(npc.id):
             npc.current_education_id = prog.id
             npc.education_status = "Обучается"

             record = EducationHistoryRecord(
                 npc_id=npc.id,
                 institution_id=inst.id,
                 program_id=prog.id,
                 start_date=current_world_date.isoformat(),
                 status="Обучается"
             )
             self.history.append(record)

             from living_world.engine.observer.world_event import EventType, EventImportance
             if hasattr(self.simulation, 'event_aggregator'):
                 self.simulation.event_aggregator.publish_event(
                     event_type=EventType.EDUCATION_ENROLL,
                     importance=EventImportance.MEDIUM,
                     message=f"{npc.get_full_name()} поступил в {inst.name} на программу {prog.name}.",
                     participants=[npc.id],
                     data={"program_name": prog.name, "institution_name": inst.name}
                 )
             else:
                 bus.publish("log_event", f"{npc.get_full_name()} поступил в {inst.name} на программу {prog.name}.")

    def _has_qualification(self, npc_id: str, qualification: str) -> bool:
        for r in self.history:
            if r.npc_id == npc_id and r.status == "Окончил" and r.qualification == qualification:
                return True
        return False
