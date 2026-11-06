from typing import Dict, List, Optional

class FamilyTreeBuilder:
    """
    Построение многопоколенного генеалогического древа жителей города.
    """
    @classmethod
    def get_npc_node(cls, npc, simulation) -> Dict:
        if not npc:
            return None
        dt = simulation.time.current_datetime
        age = npc.get_age(dt) if hasattr(npc, 'get_age') else 0
        gen = getattr(npc, 'genetics', {})
        return {
            "id": npc.id,
            "full_name": npc.get_full_name(),
            "first_name": npc.first_name,
            "last_name": npc.last_name,
            "gender": npc.gender,
            "age": age,
            "is_alive": npc.is_alive,
            "profession": npc.profession,
            "eye_color": gen.get("eye_color", "Неизвестно"),
            "hair_color": gen.get("hair_color", "Неизвестно"),
            "height_cm": gen.get("height_cm", 175),
            "body_type": gen.get("body_type", "Нормальное")
        }

    @classmethod
    def build_tree(cls, npc_id: str, simulation) -> Dict:
        """
        Собирает полное семейное древо для заданного жителя:
        - Предыдущие поколения (родители, дедушки/бабушки)
        - Текущее поколение (сам житель, супруг/партнер, родные братья и сестры)
        - Следующие поколения (дети, внуки)
        """
        npc_map = {n.id: n for n in simulation.npcs}
        subject_npc = npc_map.get(npc_id)
        if not subject_npc:
            return {}

        subject_node = cls.get_npc_node(subject_npc, simulation)

        # 1. Родители
        father_npc = npc_map.get(subject_npc.father_id) if getattr(subject_npc, 'father_id', None) else None
        mother_npc = npc_map.get(subject_npc.mother_id) if getattr(subject_npc, 'mother_id', None) else None

        parents = {
            "father": cls.get_npc_node(father_npc, simulation),
            "mother": cls.get_npc_node(mother_npc, simulation)
        }

        # 2. Дедушки и бабушки
        paternal_grandfather = npc_map.get(father_npc.father_id) if father_npc and getattr(father_npc, 'father_id', None) else None
        paternal_grandmother = npc_map.get(father_npc.mother_id) if father_npc and getattr(father_npc, 'mother_id', None) else None
        maternal_grandfather = npc_map.get(mother_npc.father_id) if mother_npc and getattr(mother_npc, 'father_id', None) else None
        maternal_grandmother = npc_map.get(mother_npc.mother_id) if mother_npc and getattr(mother_npc, 'mother_id', None) else None

        grandparents = {
            "paternal_grandfather": cls.get_npc_node(paternal_grandfather, simulation),
            "paternal_grandmother": cls.get_npc_node(paternal_grandmother, simulation),
            "maternal_grandfather": cls.get_npc_node(maternal_grandfather, simulation),
            "maternal_grandmother": cls.get_npc_node(maternal_grandmother, simulation)
        }

        # 3. Братья и сестры (общий отец или общая мать)
        siblings = []
        for n in simulation.npcs:
            if n.id != subject_npc.id:
                has_common_father = (subject_npc.father_id and n.father_id and subject_npc.father_id == n.father_id)
                has_common_mother = (subject_npc.mother_id and n.mother_id and subject_npc.mother_id == n.mother_id)
                if has_common_father or has_common_mother:
                    siblings.append(cls.get_npc_node(n, simulation))

        # 4. Партнер / супруг
        spouse_npc = None
        if getattr(subject_npc, 'dating_partner_id', None):
            spouse_npc = npc_map.get(subject_npc.dating_partner_id)
        elif getattr(subject_npc, 'family_id', None) and hasattr(simulation, 'family_manager'):
            fam = simulation.family_manager.get_family(subject_npc.family_id)
            if fam and fam.is_active:
                p_id = fam.partner_b_id if fam.partner_a_id == subject_npc.id else fam.partner_a_id
                spouse_npc = npc_map.get(p_id)

        spouse_node = cls.get_npc_node(spouse_npc, simulation)

        # 5. Дети
        children = []
        for n in simulation.npcs:
            if n.father_id == subject_npc.id or n.mother_id == subject_npc.id:
                children.append(cls.get_npc_node(n, simulation))

        # 6. Внуки
        grandchildren = []
        child_ids = {c["id"] for c in children}
        for n in simulation.npcs:
            if (n.father_id in child_ids) or (n.mother_id in child_ids):
                grandchildren.append(cls.get_npc_node(n, simulation))

        return {
            "subject": subject_node,
            "grandparents": grandparents,
            "parents": parents,
            "spouse": spouse_node,
            "siblings": siblings,
            "children": children,
            "grandchildren": grandchildren
        }
