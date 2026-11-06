import sqlite3
import os
import json
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS npcs (
    id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    age INTEGER,
    gender TEXT,
    profession TEXT,
    home_id TEXT,
    work_id TEXT,
    money REAL,
    hunger REAL,
    energy REAL,
    mood REAL,
    current_location TEXT,
    state TEXT,
    trait_sociability REAL,
    trait_friendliness REAL,
    trait_conflict REAL,
    trait_empathy REAL,
    trait_boldness REAL,
    trait_patience REAL,
    trait_ambition REAL DEFAULT 0.0,
    trait_frugality REAL DEFAULT 0.0,
    trait_diligence REAL DEFAULT 0.0,
    health REAL DEFAULT 100.0,
    family_id TEXT,
    date_of_birth TEXT,
    date_of_death TEXT,
    is_alive INTEGER,
    current_education_id TEXT,
    education_status TEXT,
    hygiene REAL DEFAULT 100.0,
    stress REAL DEFAULT 0.0,
    hobby TEXT DEFAULT 'Чтение',
    chronotype TEXT DEFAULT 'lark',
    is_sick INTEGER DEFAULT 0,
    sick_days INTEGER DEFAULT 0,
    alimony_to_id TEXT DEFAULT NULL,
    career_level INTEGER DEFAULT 1,
    work_experience_days INTEGER DEFAULT 0,
    is_renting INTEGER DEFAULT 0,
    mortgage_debt REAL DEFAULT 0.0,
    mortgage_payment REAL DEFAULT 0.0,
    transport_mode TEXT DEFAULT 'foot',
    has_criminal_record INTEGER DEFAULT 0,
    jail_days INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS buildings (
    id TEXT PRIMARY KEY,
    type TEXT,
    name TEXT,
    capacity INTEGER,
    district_id TEXT DEFAULT NULL,
    x REAL DEFAULT 0.0,
    y REAL DEFAULT 0.0,
    condition REAL DEFAULT 100.0
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    sim_time TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS world_events (
    id TEXT PRIMARY KEY,
    timestamp TEXT,
    type TEXT,
    importance TEXT,
    message TEXT,
    participants TEXT,
    data TEXT
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_npc_id TEXT,
    target_npc_id TEXT,
    familiarity REAL,
    affinity REAL,
    trust REAL,
    respect REAL,
    romantic_interest REAL,
    tension REAL,
    last_interaction_time INTEGER DEFAULT 0,
    last_meaningful_interaction_time INTEGER DEFAULT 0,
    daily_interactions_count INTEGER DEFAULT 0,
    initiations_sent INTEGER DEFAULT 0,
    initiations_received INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_npc_id TEXT,
    target_npc_id TEXT,
    event_type TEXT,
    description TEXT,
    timestamp TEXT,
    sim_time TEXT,
    significance REAL,
    valence REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS families (
    id TEXT PRIMARY KEY,
    creation_time TEXT,
    is_active INTEGER
);

CREATE TABLE IF NOT EXISTS educational_institutions (
    id TEXT PRIMARY KEY,
    type TEXT,
    name TEXT,
    capacity INTEGER,
    building_id TEXT
);

CREATE TABLE IF NOT EXISTS education_programs (
    id TEXT PRIMARY KEY,
    institution_id TEXT,
    name TEXT,
    type TEXT,
    duration INTEGER,
    requirements TEXT
);

CREATE TABLE IF NOT EXISTS education_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id TEXT,
    institution_id TEXT,
    program_id TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT,
    qualification TEXT
);

CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    home_id TEXT,
    creation_time TEXT,
    stress REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS enterprises (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    building_id TEXT,
    owner_id TEXT,
    budget REAL,
    wage_rate REAL,
    is_active INTEGER DEFAULT 1,
    raw_materials REAL DEFAULT 20.0,
    finished_goods REAL DEFAULT 20.0
);
"""

class Database:
    def __init__(self, db_path="world.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA)
            cursor = conn.cursor()

            # Migrations for existing npcs table
            cursor.execute("PRAGMA table_info(npcs)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'trait_sociability' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_sociability REAL DEFAULT 0.0")
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_friendliness REAL DEFAULT 0.0")
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_conflict REAL DEFAULT 0.0")
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_empathy REAL DEFAULT 0.0")
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_boldness REAL DEFAULT 0.0")
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_patience REAL DEFAULT 0.0")
                cursor.execute("ALTER TABLE npcs ADD COLUMN family_id TEXT DEFAULT NULL")

            if 'date_of_birth' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN date_of_birth TEXT DEFAULT NULL")
                cursor.execute("ALTER TABLE npcs ADD COLUMN date_of_death TEXT DEFAULT NULL")
                cursor.execute("ALTER TABLE npcs ADD COLUMN is_alive INTEGER DEFAULT 1")

            if 'current_education_id' not in columns:
                 cursor.execute("ALTER TABLE npcs ADD COLUMN current_education_id TEXT DEFAULT NULL")
                 cursor.execute("ALTER TABLE npcs ADD COLUMN education_status TEXT DEFAULT NULL")

            if 'household_id' not in columns:
                 cursor.execute("ALTER TABLE npcs ADD COLUMN household_id TEXT DEFAULT NULL")
            if 'dating_partner_id' not in columns:
                 cursor.execute("ALTER TABLE npcs ADD COLUMN dating_partner_id TEXT DEFAULT NULL")

            # Fetch sim_time from meta to calculate date_of_birth for existing NPCs
            if 'date_of_birth' not in columns:
                cursor.execute("SELECT value FROM meta WHERE key = 'sim_time'")
                row = cursor.fetchone()
                current_date = datetime(2000, 1, 1, 8, 0)
                if row:
                    try:
                        time_dict = json.loads(row[0])
                        if 'year' in time_dict and 'month' in time_dict:
                            current_date = datetime(
                                time_dict.get('year', 2000),
                                time_dict.get('month', 1),
                                time_dict.get('day', 1),
                                time_dict.get('hour', 8),
                                time_dict.get('minute', 0)
                            )
                        else:
                            from datetime import timedelta
                            day = time_dict.get('day', 1)
                            hour = time_dict.get('hour', 8)
                            minute = time_dict.get('minute', 0)
                            delta = timedelta(days=day - 1, hours=hour - 8, minutes=minute)
                            current_date = current_date + delta
                    except Exception:
                        pass

                # Migrate existing NPCs
                cursor.execute("SELECT id, age FROM npcs")
                existing_npcs = cursor.fetchall()
                from datetime import timedelta
                for npc_id, age in existing_npcs:
                    if age is not None:
                        dob = current_date - timedelta(days=int(age) * 365)
                        cursor.execute("UPDATE npcs SET date_of_birth = ?, is_alive = 1 WHERE id = ?", (dob.isoformat(), npc_id))


            cursor.execute('''CREATE TABLE IF NOT EXISTS pregnancies (
                id TEXT PRIMARY KEY,
                mother_id TEXT,
                father_id TEXT,
                start_date TEXT,
                expected_birth_date TEXT,
                status TEXT
            )''')

            cursor.execute("PRAGMA table_info(npcs)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'mother_id' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN mother_id TEXT")
            if 'father_id' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN father_id TEXT")
            if 'children_desire' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN children_desire REAL DEFAULT 0.5")
            if 'health' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN health REAL DEFAULT 100.0")
            if 'trait_ambition' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_ambition REAL DEFAULT 0.0")
            if 'trait_frugality' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_frugality REAL DEFAULT 0.0")
            if 'trait_diligence' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN trait_diligence REAL DEFAULT 0.0")
            if 'hygiene' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN hygiene REAL DEFAULT 100.0")
            if 'stress' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN stress REAL DEFAULT 0.0")
            if 'hobby' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN hobby TEXT DEFAULT 'Чтение'")
            if 'chronotype' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN chronotype TEXT DEFAULT 'lark'")
            if 'is_sick' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN is_sick INTEGER DEFAULT 0")
            if 'sick_days' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN sick_days INTEGER DEFAULT 0")
            if 'alimony_to_id' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN alimony_to_id TEXT DEFAULT NULL")
            if 'career_level' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN career_level INTEGER DEFAULT 1")
            if 'work_experience_days' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN work_experience_days INTEGER DEFAULT 0")
            if 'is_renting' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN is_renting INTEGER DEFAULT 0")
            if 'mortgage_debt' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN mortgage_debt REAL DEFAULT 0.0")
            if 'mortgage_payment' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN mortgage_payment REAL DEFAULT 0.0")

            cursor.execute("PRAGMA table_info(enterprises)")
            columns_ent = [info[1] for info in cursor.fetchall()]
            if 'raw_materials' not in columns_ent:
                cursor.execute("ALTER TABLE enterprises ADD COLUMN raw_materials REAL DEFAULT 20.0")
            if 'finished_goods' not in columns_ent:
                cursor.execute("ALTER TABLE enterprises ADD COLUMN finished_goods REAL DEFAULT 20.0")

            if 'transport_mode' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN transport_mode TEXT DEFAULT 'foot'")
            if 'has_criminal_record' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN has_criminal_record INTEGER DEFAULT 0")
            if 'jail_days' not in columns:
                cursor.execute("ALTER TABLE npcs ADD COLUMN jail_days INTEGER DEFAULT 0")

            cursor.execute("PRAGMA table_info(buildings)")
            columns_b = [info[1] for info in cursor.fetchall()]
            if 'district_id' not in columns_b:
                cursor.execute("ALTER TABLE buildings ADD COLUMN district_id TEXT DEFAULT NULL")
            if 'x' not in columns_b:
                cursor.execute("ALTER TABLE buildings ADD COLUMN x REAL DEFAULT 0.0")
            if 'y' not in columns_b:
                cursor.execute("ALTER TABLE buildings ADD COLUMN y REAL DEFAULT 0.0")
            if 'condition' not in columns_b:
                cursor.execute("ALTER TABLE buildings ADD COLUMN condition REAL DEFAULT 100.0")

            cursor.execute("PRAGMA table_info(families)")
            columns_fam = [info[1] for info in cursor.fetchall()]
            if 'last_reproduction_check' not in columns_fam:
                cursor.execute("ALTER TABLE families ADD COLUMN last_reproduction_check TEXT")

            cursor.execute("PRAGMA table_info(relationships)")
            columns_rel = [info[1] for info in cursor.fetchall()]
            if 'last_interaction_time' not in columns_rel:
                cursor.execute("ALTER TABLE relationships ADD COLUMN last_interaction_time INTEGER DEFAULT 0")
            if 'initiations_sent' not in columns_rel:
                cursor.execute("ALTER TABLE relationships ADD COLUMN initiations_sent INTEGER DEFAULT 0")
            if 'initiations_received' not in columns_rel:
                cursor.execute("ALTER TABLE relationships ADD COLUMN initiations_received INTEGER DEFAULT 0")

            cursor.execute("PRAGMA table_info(households)")
            columns_hh = [info[1] for info in cursor.fetchall()]
            if 'stress' not in columns_hh:
                cursor.execute("ALTER TABLE households ADD COLUMN stress REAL DEFAULT 0.0")

            cursor.execute('''CREATE TABLE IF NOT EXISTS enterprises (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                building_id TEXT,
                owner_id TEXT,
                budget REAL,
                wage_rate REAL,
                is_active INTEGER DEFAULT 1
            )''')

            cursor.execute("PRAGMA table_info(memories)")
            columns_mem = [info[1] for info in cursor.fetchall()]
            if 'valence' not in columns_mem:
                cursor.execute("ALTER TABLE memories ADD COLUMN valence REAL DEFAULT 0.0")

            # Migration: Create households for existing NPCs if they don't have household_id
            cursor.execute("SELECT id, home_id FROM npcs WHERE household_id IS NULL AND home_id IS NOT NULL")
            npcs_without_household = cursor.fetchall()
            if npcs_without_household:
                home_households = {}
                import uuid
                current_time = datetime.now().isoformat()
                for npc_id, home_id in npcs_without_household:
                    if home_id not in home_households:
                        hh_id = str(uuid.uuid4())
                        home_households[home_id] = hh_id
                        cursor.execute("INSERT INTO households (id, home_id, creation_time) VALUES (?, ?, ?)", (hh_id, home_id, current_time))
                    hh_id = home_households[home_id]
                    cursor.execute("UPDATE npcs SET household_id = ? WHERE id = ?", (hh_id, npc_id))
            conn.commit()
        finally:
            conn.close()

    def save_world(self, sim_time, npcs, buildings, events, families=None, relationships=None, memories=None, educational_institutions=None, education_programs=None, education_history=None, pregnancies=None, households=None, world_events=None, enterprises=None, city_treasury=None, politics=None, crimes=None, culture=None):
        if memories is None: memories = []
        if families is None: families = []
        if relationships is None: relationships = []
        if educational_institutions is None: educational_institutions = []
        if education_programs is None: education_programs = []
        if education_history is None: education_history = []
        if pregnancies is None: pregnancies = []
        if households is None: households = []
        if world_events is None: world_events = []
        if enterprises is None: enterprises = []

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Сохраняем мету (время)
            cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("sim_time", json.dumps(sim_time)))
            if city_treasury is not None:
                cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("city_treasury", str(city_treasury)))
            if politics is not None:
                cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("politics", json.dumps(politics)))
            if crimes is not None:
                cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("crimes", json.dumps(crimes)))
            if culture is not None:
                cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("culture", json.dumps(culture)))

            # Сохраняем образование
            cursor.execute("DELETE FROM educational_institutions")
            for inst in educational_institutions:
                cursor.execute(
                    "INSERT INTO educational_institutions (id, type, name, capacity, building_id) VALUES (?, ?, ?, ?, ?)",
                    (inst.id, inst.type, inst.name, inst.capacity, inst.building_id)
                )

            cursor.execute("DELETE FROM education_programs")
            for prog in education_programs:
                cursor.execute(
                    "INSERT INTO education_programs (id, institution_id, name, type, duration, requirements) VALUES (?, ?, ?, ?, ?, ?)",
                    (prog.id, prog.institution_id, prog.name, prog.type, prog.duration, json.dumps(prog.requirements))
                )

            cursor.execute("DELETE FROM education_history")
            for hist in education_history:
                if isinstance(hist, dict):
                     cursor.execute(
                         "INSERT INTO education_history (npc_id, institution_id, program_id, start_date, end_date, status, qualification) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (hist['npc_id'], hist['institution_id'], hist['program_id'], hist['start_date'], hist['end_date'], hist['status'], hist.get('qualification'))
                     )
                else:
                     cursor.execute(
                         "INSERT INTO education_history (npc_id, institution_id, program_id, start_date, end_date, status, qualification) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (hist.npc_id, hist.institution_id, hist.program_id, hist.start_date, hist.end_date, hist.status, getattr(hist, 'qualification', None))
                     )

            # Сохраняем домохозяйства
            cursor.execute("DELETE FROM households")
            for h in households:
                if isinstance(h, dict):
                    cursor.execute(
                        "INSERT INTO households (id, home_id, creation_time, stress) VALUES (?, ?, ?, ?)",
                        (h['id'], h['home_id'], h['creation_time'], h.get('stress', 0.0))
                    )
                else:
                    cursor.execute(
                        "INSERT INTO households (id, home_id, creation_time, stress) VALUES (?, ?, ?, ?)",
                        (h.id, h.home_id, h.creation_time, getattr(h, 'stress', 0.0))
                    )

            # Сохраняем здания
            cursor.execute("DELETE FROM buildings")
            for b in buildings:
                cursor.execute(
                    "INSERT INTO buildings (id, type, name, capacity, district_id, x, y, condition) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (b.id, b.b_type, b.name, b.capacity, getattr(b, 'district_id', None), getattr(b, 'x', 0.0), getattr(b, 'y', 0.0), getattr(b, 'condition', 100.0))
                )

            # Сохраняем NPC
            cursor.execute("DELETE FROM npcs")
            for npc in npcs:
                cursor.execute(
                    """INSERT INTO npcs
                    (id, first_name, last_name, gender, profession, home_id, work_id, money, hunger, energy, mood, current_location, state, trait_sociability, trait_friendliness, trait_conflict, trait_empathy, trait_boldness, trait_patience, trait_ambition, trait_frugality, trait_diligence, health, family_id, date_of_birth, date_of_death, is_alive, current_education_id, education_status, mother_id, father_id, children_desire, household_id, dating_partner_id, hygiene, stress, hobby, chronotype, is_sick, sick_days, alimony_to_id, career_level, work_experience_days, is_renting, mortgage_debt, mortgage_payment, transport_mode, has_criminal_record, jail_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (npc.id, npc.first_name, npc.last_name, npc.gender, npc.profession,
                     npc.home_id, npc.work_id, npc.money, npc.hunger, npc.energy, npc.mood, npc.current_location, npc.state,
                     npc.traits.get('sociability', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('friendliness', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('conflict', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('empathy', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('boldness', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('patience', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('ambition', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('frugality', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('diligence', 0.0) if hasattr(npc, 'traits') else 0.0,
                     getattr(npc, 'health', 100.0),
                     npc.family_id if hasattr(npc, 'family_id') else None,
                     npc.date_of_birth.isoformat() if npc.date_of_birth else None,
                     npc.date_of_death.isoformat() if getattr(npc, 'date_of_death', None) else None,
                     1 if getattr(npc, 'is_alive', True) else 0,
                     getattr(npc, 'current_education_id', None),
                     getattr(npc, 'education_status', None),
                     getattr(npc, 'mother_id', None),
                     getattr(npc, 'father_id', None),
                     getattr(npc, 'children_desire', 0.5),
                     getattr(npc, 'household_id', None),
                     getattr(npc, 'dating_partner_id', None),
                     getattr(npc, 'hygiene', 100.0),
                     getattr(npc, 'stress', 0.0),
                     getattr(npc, 'hobby', 'Чтение'),
                     getattr(npc, 'chronotype', 'lark'),
                     1 if getattr(npc, 'is_sick', False) else 0,
                     getattr(npc, 'sick_days', 0),
                     getattr(npc, 'alimony_to_id', None),
                     getattr(npc, 'career_level', 1),
                     getattr(npc, 'work_experience_days', 0),
                     1 if getattr(npc, 'is_renting', False) else 0,
                     getattr(npc, 'mortgage_debt', 0.0),
                     getattr(npc, 'mortgage_payment', 0.0),
                     getattr(npc, 'transport_mode', 'foot'),
                     1 if getattr(npc, 'has_criminal_record', False) else 0,
                     getattr(npc, 'jail_days', 0))
                )

            # Сохраняем семьи
            cursor.execute("DELETE FROM families")
            for f in families:
                cursor.execute(
                    "INSERT INTO families (id, creation_time, is_active, last_reproduction_check) VALUES (?, ?, ?, ?)",
                    (f['id'], f['creation_time'], f['is_active'], f.get('last_reproduction_check'))
                )


            # Сохраняем беременности
            cursor.execute("DELETE FROM pregnancies")
            for p in pregnancies:
                cursor.execute(
                    "INSERT INTO pregnancies (id, mother_id, father_id, start_date, expected_birth_date, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (p.id, p.mother_id, p.father_id, p.start_date.isoformat(), p.expected_birth_date.isoformat(), p.status)
                )

            # Сохраняем отношения
            # Сохраняем отношения (полная перезапись на сохранении)
            cursor.execute("DELETE FROM relationships")
            for r in relationships:
                cursor.execute(
                    """INSERT INTO relationships
                    (source_npc_id, target_npc_id, familiarity, affinity, trust, respect, romantic_interest, tension,
                    last_interaction_time, last_meaningful_interaction_time, daily_interactions_count, initiations_sent, initiations_received)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (r['source_npc_id'], r['target_npc_id'], r['familiarity'], r['affinity'],
                     r['trust'], r['respect'], r['romantic_interest'], r['tension'], r.get('last_interaction_time', 0),
                     r.get('last_meaningful_interaction_time', 0), r.get('daily_interactions_count', 0),
                     r.get('initiations_sent', 0), r.get('initiations_received', 0))
                )


            # Сохраняем память
            cursor.execute("DELETE FROM memories")
            for m in memories:
                cursor.execute(
                    "INSERT INTO memories (owner_npc_id, target_npc_id, event_type, description, timestamp, sim_time, significance, valence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (m['owner_npc_id'], m.get('target_npc_id'), m['event_type'], m['description'], m['timestamp'], m['sim_time'], m['significance'], m.get('valence', 0.0))
                )

            # The in-memory history is the complete source of truth.  Replacing the
            # table prevents every subsequent save from appending the same history.
            cursor.execute("DELETE FROM events")
            for event in events:
                cursor.execute(
                    "INSERT INTO events (timestamp, sim_time, message) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), event['time'], event['msg'])
                )

            # Сохраняем world_events (новые структурированные события)
            cursor.execute("DELETE FROM world_events")
            for we in world_events:
                cursor.execute(
                    "INSERT INTO world_events (id, timestamp, type, importance, message, participants, data) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (we['id'], we['timestamp'], we['type'], we['importance'], we['message'], json.dumps(we['participants']), json.dumps(we['data']))
                )

            # Сохраняем предприятия
            cursor.execute("DELETE FROM enterprises")
            for ent in enterprises:
                if isinstance(ent, dict):
                    cursor.execute(
                        "INSERT INTO enterprises (id, name, type, building_id, owner_id, budget, wage_rate, is_active, raw_materials, finished_goods) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (ent['id'], ent['name'], ent.get('type') or ent.get('enterprise_type'), ent['building_id'], ent.get('owner_id'), ent.get('budget', 50000.0), ent.get('wage_rate', 250.0), 1 if ent.get('is_active', True) else 0, ent.get('raw_materials', 20.0), ent.get('finished_goods', 20.0))
                    )
                else:
                    cursor.execute(
                        "INSERT INTO enterprises (id, name, type, building_id, owner_id, budget, wage_rate, is_active, raw_materials, finished_goods) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (ent.id, ent.name, ent.enterprise_type, ent.building_id, ent.owner_id, ent.budget, ent.wage_rate, 1 if ent.is_active else 0, getattr(ent, 'raw_materials', 20.0), getattr(ent, 'finished_goods', 20.0))
                    )
            conn.commit()
        finally:
            conn.close()

    def load_world(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM meta WHERE key = 'sim_time'")
            row = cursor.fetchone()
            sim_time = json.loads(row['value']) if row else None

            cursor.execute("SELECT * FROM educational_institutions")
            educational_institutions = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM education_programs")
            education_programs = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM education_history ORDER BY id ASC")
            education_history = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM buildings")
            buildings = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM npcs")
            npcs = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM events ORDER BY id ASC")
            events = [dict(r) for r in cursor.fetchall()]
            events = [{"time": e["sim_time"], "msg": e["message"]} for e in events]

            cursor.execute("SELECT * FROM families")
            families = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM relationships")
            relationships = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM memories ORDER BY id ASC")
            memories = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM pregnancies")
            pregnancies = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM households")
            households = [dict(r) for r in cursor.fetchall()]

            # Handle backward compatibility: older save files may not have world_events table
            world_events = []
            try:
                cursor.execute("SELECT * FROM world_events")
                world_events_raw = [dict(r) for r in cursor.fetchall()]
                for we in world_events_raw:
                    we_dict = dict(we)
                    we_dict['participants'] = json.loads(we_dict['participants']) if we_dict['participants'] else []
                    we_dict['data'] = json.loads(we_dict['data']) if we_dict['data'] else {}
                    world_events.append(we_dict)
            except sqlite3.OperationalError:
                pass

            enterprises = []
            try:
                cursor.execute("SELECT * FROM enterprises")
                enterprises = [dict(r) for r in cursor.fetchall()]
            except sqlite3.OperationalError:
                pass

            cursor.execute("SELECT value FROM meta WHERE key = 'city_treasury'")
            row_tr = cursor.fetchone()
            city_treasury = float(row_tr['value']) if row_tr else 100000.0

            cursor.execute("SELECT value FROM meta WHERE key = 'politics'")
            row_pol = cursor.fetchone()
            politics_data = json.loads(row_pol['value']) if row_pol and row_pol['value'] else None

            cursor.execute("SELECT value FROM meta WHERE key = 'crimes'")
            row_cr = cursor.fetchone()
            crimes_data = json.loads(row_cr['value']) if row_cr and row_cr['value'] else None

            cursor.execute("SELECT value FROM meta WHERE key = 'culture'")
            row_cult = cursor.fetchone()
            culture_data = json.loads(row_cult['value']) if row_cult and row_cult['value'] else None

            return sim_time, buildings, npcs, events, families, relationships, memories, educational_institutions, education_programs, education_history, pregnancies, households, world_events, enterprises, city_treasury, politics_data, crimes_data, culture_data
        finally:
            conn.close()
