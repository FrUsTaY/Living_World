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
    tension REAL
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_npc_id TEXT,
    target_npc_id TEXT,
    event_type TEXT,
    description TEXT,
    timestamp TEXT,
    sim_time TEXT,
    significance REAL
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
                    (id, first_name, last_name, age, gender, profession, home_id, work_id, money, hunger, energy, mood, current_location, state,
                    trait_sociability, trait_friendliness, trait_conflict, trait_empathy, trait_boldness, trait_patience, family_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (npc.id, npc.first_name, npc.last_name, npc.age, npc.gender, npc.profession,
                     npc.home_id, npc.work_id, npc.money, npc.hunger, npc.energy, npc.mood, npc.current_location, npc.state,
                     npc.traits.get('sociability', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('friendliness', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('conflict', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('empathy', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('boldness', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.traits.get('patience', 0.0) if hasattr(npc, 'traits') else 0.0,
                     npc.family_id if hasattr(npc, 'family_id') else None)
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
                    (source_npc_id, target_npc_id, familiarity, affinity, trust, respect, romantic_interest, tension)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (r['source_npc_id'], r['target_npc_id'], r['familiarity'], r['affinity'],
                     r['trust'], r['respect'], r['romantic_interest'], r['tension'])
                )


            # Сохраняем память
            cursor.execute("DELETE FROM memories")
            for m in memories:
                cursor.execute(
                    "INSERT INTO memories (owner_npc_id, target_npc_id, event_type, description, timestamp, sim_time, significance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (m['owner_npc_id'], m.get('target_npc_id'), m['event_type'], m['description'], m['timestamp'], m['sim_time'], m['significance'])
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
