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
    family_id TEXT
);

CREATE TABLE IF NOT EXISTS buildings (
    id TEXT PRIMARY KEY,
    type TEXT,
    name TEXT,
    capacity INTEGER
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    sim_time TEXT,
    message TEXT
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
"""

class Database:
    def __init__(self, db_path="world.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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

                # Fetch sim_time from meta to calculate date_of_birth for existing NPCs
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

            cursor.execute("PRAGMA table_info(relationships)")
            columns_rel = [info[1] for info in cursor.fetchall()]
            if 'last_interaction_time' not in columns_rel:
                cursor.execute("ALTER TABLE relationships ADD COLUMN last_interaction_time INTEGER DEFAULT 0")
            if 'initiations_sent' not in columns_rel:
                cursor.execute("ALTER TABLE relationships ADD COLUMN initiations_sent INTEGER DEFAULT 0")
            if 'initiations_received' not in columns_rel:
                cursor.execute("ALTER TABLE relationships ADD COLUMN initiations_received INTEGER DEFAULT 0")

            cursor.execute("PRAGMA table_info(memories)")
            columns_mem = [info[1] for info in cursor.fetchall()]
            if 'valence' not in columns_mem:
                cursor.execute("ALTER TABLE memories ADD COLUMN valence REAL DEFAULT 0.0")

    def save_world(self, sim_time, npcs, buildings, events, families=None, relationships=None, memories=None):
        if memories is None: memories = []
        if families is None: families = []
        if relationships is None: relationships = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Сохраняем мету (время)
            cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("sim_time", json.dumps(sim_time)))

            # Сохраняем здания
            cursor.execute("DELETE FROM buildings")
            for b in buildings:
                cursor.execute(
                    "INSERT INTO buildings (id, type, name, capacity) VALUES (?, ?, ?, ?)",
                    (b.id, b.b_type, b.name, b.capacity)
                )

            # Сохраняем NPC
            cursor.execute("DELETE FROM npcs")
            for npc in npcs:
                cursor.execute(
                    """INSERT INTO npcs
                    (id, first_name, last_name, gender, profession, home_id, work_id, money, hunger, energy, mood, current_location, state,
                    trait_sociability, trait_friendliness, trait_conflict, trait_empathy, trait_boldness, trait_patience, family_id,
                    date_of_birth, date_of_death, is_alive)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (npc.id, npc.first_name, npc.last_name, npc.gender, npc.profession,
                     npc.home_id, npc.work_id, npc.money, npc.hunger, npc.energy, npc.mood, npc.current_location, npc.state,
                     npc.traits.get('sociability', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('friendliness', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('conflict', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('empathy', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('boldness', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('patience', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.family_id if hasattr(npc, 'family_id') else None,
                     npc.date_of_birth.isoformat() if npc.date_of_birth else None,
                     npc.date_of_death.isoformat() if npc.date_of_death else None,
                     1 if npc.is_alive else 0)
                )

            # Сохраняем семьи
            cursor.execute("DELETE FROM families")
            for f in families:
                cursor.execute(
                    "INSERT INTO families (id, creation_time, is_active) VALUES (?, ?, ?)",
                    (f['id'], f['creation_time'], f['is_active'])
                )

            # Сохраняем отношения (полная перезапись на сохранении)
            cursor.execute("DELETE FROM relationships")
            for r in relationships:
                cursor.execute(
                    """INSERT INTO relationships
                    (source_npc_id, target_npc_id, familiarity, affinity, trust, respect, romantic_interest, tension, last_interaction_time, initiations_sent, initiations_received)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (r['source_npc_id'], r['target_npc_id'], r['familiarity'], r['affinity'],
                     r['trust'], r['respect'], r['romantic_interest'], r['tension'], r.get('last_interaction_time', 0), r.get('initiations_sent', 0), r.get('initiations_received', 0))
                )


            # Сохраняем память
            cursor.execute("DELETE FROM memories")
            for m in memories:
                cursor.execute(
                    "INSERT INTO memories (owner_npc_id, target_npc_id, event_type, description, timestamp, sim_time, significance, valence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (m['owner_npc_id'], m.get('target_npc_id'), m['event_type'], m['description'], m['timestamp'], m['sim_time'], m['significance'], m.get('valence', 0.0))
                )

            # Сохраняем только новые (несохраненные) события
            for event in events:
                cursor.execute(
                    "INSERT INTO events (timestamp, sim_time, message) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), event['time'], event['msg'])
                )

    def load_world(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM meta WHERE key = 'sim_time'")
            row = cursor.fetchone()
            sim_time = json.loads(row['value']) if row else None

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

            return sim_time, buildings, npcs, events, families, relationships, memories
