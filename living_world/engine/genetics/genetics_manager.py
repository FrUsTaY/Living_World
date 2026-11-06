import random
from typing import Optional, Dict, Tuple

class GeneticsManager:
    """
    Менделевская генетика, наследование аллелей, фенотип (глаза, волосы, рост)
    и биологические предрасположенности (иммунитет, долголетие).
    """
    EYE_ALLELES_POOL = ["B", "B", "g", "b"]  # B: карие (дом.), g: зеленые, b: голубые (рец.)
    HAIR_ALLELES_POOL = ["D", "D", "C", "R", "b"] # D: брюнет, C: шатен, R: рыжий, b: блондин
    BODY_TYPES = ["Худощавое", "Нормальное", "Атлетическое", "Плотное"]

    @classmethod
    def determine_eye_color(cls, alleles: Tuple[str, str]) -> str:
        if "B" in alleles:
            return "Карие"
        elif "g" in alleles:
            return "Зеленые"
        else:
            return "Голубые"

    @classmethod
    def determine_hair_color(cls, alleles: Tuple[str, str]) -> str:
        if "D" in alleles:
            return "Брюнет"
        elif "C" in alleles:
            return "Шатен"
        elif "R" in alleles:
            return "Рыжий"
        else:
            return "Блондин"

    @classmethod
    def generate_genome(cls, father=None, mother=None, gender: str = "М") -> Dict:
        """
        Генерирует генотип и фенотип либо на основе менделевского скрещивания родителей,
        либо первично для основателей города.
        """
        f_gen = getattr(father, 'genetics', None) if father else None
        m_gen = getattr(mother, 'genetics', None) if mother else None

        # 1. Аллели цвета глаз
        if f_gen and m_gen:
            f_allele = random.choice(f_gen.get("eye_alleles", ("B", "b")))
            m_allele = random.choice(m_gen.get("eye_alleles", ("B", "b")))
            eye_alleles = (f_allele, m_allele)
        else:
            eye_alleles = (random.choice(cls.EYE_ALLELES_POOL), random.choice(cls.EYE_ALLELES_POOL))
        eye_color = cls.determine_eye_color(eye_alleles)

        # 2. Аллели цвета волос
        if f_gen and m_gen:
            f_hair = random.choice(f_gen.get("hair_alleles", ("C", "b")))
            m_hair = random.choice(m_gen.get("hair_alleles", ("C", "b")))
            hair_alleles = (f_hair, m_hair)
        else:
            hair_alleles = (random.choice(cls.HAIR_ALLELES_POOL), random.choice(cls.HAIR_ALLELES_POOL))
        hair_color = cls.determine_hair_color(hair_alleles)

        # 3. Рост (см)
        base_m = 178 if gender == "М" else 165
        if f_gen and m_gen:
            mid_height = (f_gen.get("height_cm", 178) + m_gen.get("height_cm", 165)) / 2.0
            height_cm = int(mid_height + (6 if gender == "М" else -6) + random.uniform(-4, 4))
        else:
            height_cm = int(base_m + random.uniform(-10, 12))
        height_cm = max(150, min(205, height_cm))

        # 4. Комплекция
        if f_gen and random.random() < 0.6:
            body_type = f_gen.get("body_type", "Нормальное")
        elif m_gen and random.random() < 0.6:
            body_type = m_gen.get("body_type", "Нормальное")
        else:
            body_type = random.choice(cls.BODY_TYPES)

        # 5. Иммунитет и долголетие
        if f_gen and m_gen:
            imm = (f_gen.get("immunity", 0.75) + m_gen.get("immunity", 0.75)) / 2.0 + random.uniform(-0.05, 0.05)
            longevity = (f_gen.get("longevity", 0.75) + m_gen.get("longevity", 0.75)) / 2.0 + random.uniform(-0.05, 0.05)
        else:
            imm = random.uniform(0.55, 0.95)
            longevity = random.uniform(0.55, 0.95)

        imm = round(max(0.3, min(0.99, imm)), 2)
        longevity = round(max(0.3, min(0.99, longevity)), 2)

        return {
            "eye_alleles": eye_alleles,
            "eye_color": eye_color,
            "hair_alleles": hair_alleles,
            "hair_color": hair_color,
            "height_cm": height_cm,
            "body_type": body_type,
            "immunity": imm,
            "longevity": longevity
        }
