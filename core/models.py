# -*- coding: utf-8 -*-
"""RiseSim core models (ported from C# SimModel)"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Tuple


class Sex(IntEnum):
    ALL = 0
    MALE = 1
    FEMALE = 2


class EquipKind(Enum):
    HEAD = "head"
    BODY = "body"
    ARM = "arm"
    WAIST = "waist"
    LEG = "leg"
    CHARM = "charm"
    DECO = "deco"
    GSKILL = "gskill"
    ERROR = "error"

    def str_jp(self) -> str:
        return {
            EquipKind.HEAD: "頭",
            EquipKind.BODY: "胴",
            EquipKind.ARM: "腕",
            EquipKind.WAIST: "腰",
            EquipKind.LEG: "足",
            EquipKind.CHARM: "護石",
            EquipKind.DECO: "装飾品",
            EquipKind.GSKILL: "錬成スキル",
            EquipKind.ERROR: "エラー",
        }.get(self, "")

    def str_with_colon(self) -> str:
        return self.str_jp() + "："


class CludeKind(IntEnum):
    EXCLUDE = 0
    INCLUDE = 1


@dataclass
class Skill:
    name: str
    level: int = 0
    is_additional: bool = False
    is_fixed: bool = False
    category: str = "未分類"
    specific_names: Dict[int, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.level < 0:
            self.level = 0

    def copy(self, level: Optional[int] = None, is_additional: Optional[bool] = None) -> "Skill":
        return Skill(
            name=self.name,
            level=self.level if level is None else level,
            is_additional=self.is_additional if is_additional is None else is_additional,
            is_fixed=self.is_fixed,
            category=self.category,
            specific_names=dict(self.specific_names),
        )

    def display_name(self) -> str:
        if self.level in self.specific_names:
            return self.specific_names[self.level]
        return f"{self.name}Lv{self.level}"


@dataclass
class Equipment:
    name: str = ""
    disp_name: str = ""
    kind: EquipKind = EquipKind.ERROR
    sex: Sex = Sex.ALL
    rare: int = 0
    slot1: int = 0
    slot2: int = 0
    slot3: int = 0
    mindef: int = 0
    maxdef: int = 0
    fire: int = 0
    water: int = 0
    thunder: int = 0
    ice: int = 0
    dragon: int = 0
    row_no: int = 2**31 - 1
    skills: List[Skill] = field(default_factory=list)
    generic_skills: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    augmentation_table: int = 0
    base_equipment: Optional["Equipment"] = None
    ideal: Optional[object] = None

    def __post_init__(self):
        if not self.disp_name:
            self.disp_name = self.name

    @property
    def marged_skills(self) -> List[Skill]:
        merged: Dict[str, Skill] = {}
        for s in self.skills:
            if s.name in merged:
                merged[s.name].level += s.level
            else:
                merged[s.name] = s.copy()
        return list(merged.values())

    def slots(self) -> Tuple[int, int, int]:
        return (self.slot1, self.slot2, self.slot3)

    def simple_description(self) -> str:
        parts = [self.kind.str_with_colon(), self.disp_name]
        if self.kind not in (EquipKind.DECO, EquipKind.CHARM, EquipKind.GSKILL):
            parts.append(f",{self.slot1}-{self.slot2}-{self.slot3}")
        return "".join(parts)


@dataclass
class Clude:
    name: str
    kind: CludeKind


@dataclass
class Augmentation:
    name: str = ""
    disp_name: str = ""
    kind: EquipKind = EquipKind.ERROR
    base_name: str = ""
    slot1: int = 0
    slot2: int = 0
    slot3: int = 0
    def_: int = 0
    fire: int = 0
    water: int = 0
    thunder: int = 0
    ice: int = 0
    dragon: int = 0
    skills: List[Skill] = field(default_factory=list)


@dataclass
class IdealAugmentation:
    name: str = ""
    disp_name: str = ""
    table: int = 0
    is_include_lower: bool = False
    slot_increment: int = 0
    def_: int = 0
    fire: int = 0
    water: int = 0
    thunder: int = 0
    ice: int = 0
    dragon: int = 0
    skills: List[Skill] = field(default_factory=list)
    generic_skills: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    skill_minuses: List[int] = field(default_factory=list)
    is_one: bool = False
    is_enabled: bool = True
    is_required: bool = False


@dataclass
class SearchCondition:
    skills: List[Skill] = field(default_factory=list)
    weapon_slot1: int = 0
    weapon_slot2: int = 0
    weapon_slot3: int = 0
    sex: Sex = Sex.ALL
    def_req: int = 0
    fire_req: int = -20
    water_req: int = -20
    thunder_req: int = -20
    ice_req: int = -20
    dragon_req: int = -20
    include_ideal_augmentation: bool = False
    prioritize_no_ideal: bool = True
    exclude_abstract: bool = False
    additional_fix_data: Optional[Dict[str, int]] = None

    def add_skill(self, skill: Skill) -> bool:
        for s in self.skills:
            if s.name == skill.name:
                if s.level < skill.level:
                    s.level = skill.level
                    return True
                return False
        self.skills.append(skill.copy())
        return True

    def skill_level(self, name: str) -> int:
        for s in self.skills:
            if s.name == name:
                return s.level
        return 0


@dataclass
class EquipSet:
    head: Optional[Equipment] = None
    body: Optional[Equipment] = None
    arm: Optional[Equipment] = None
    waist: Optional[Equipment] = None
    leg: Optional[Equipment] = None
    charm: Optional[Equipment] = None
    decos: List[Equipment] = field(default_factory=list)
    free_slot1: int = 0
    free_slot2: int = 0
    free_slot3: int = 0
    free_slot4: int = 0
    total_def: int = 0
    fire: int = 0
    water: int = 0
    thunder: int = 0
    ice: int = 0
    dragon: int = 0
    skills: List[Skill] = field(default_factory=list)
    glpk_row_name: str = ""

    def existing_equips_without_decos(self) -> List[Equipment]:
        result = []
        for e in (self.head, self.body, self.arm, self.waist, self.leg, self.charm):
            if e is not None and e.name:
                result.append(e)
        return result

    def all_equips(self) -> List[Equipment]:
        result = self.existing_equips_without_decos()
        result.extend(self.decos)
        return result

    def compute_totals(self) -> None:
        self.total_def = 0
        self.fire = self.water = self.thunder = self.ice = self.dragon = 0
        skill_map: Dict[str, int] = {}
        for e in self.all_equips():
            self.total_def += e.maxdef
            self.fire += e.fire
            self.water += e.water
            self.thunder += e.thunder
            self.ice += e.ice
            self.dragon += e.dragon
            for s in e.marged_skills:
                skill_map[s.name] = skill_map.get(s.name, 0) + s.level
        self.skills = [Skill(name=n, level=lv) for n, lv in sorted(skill_map.items())]

    def apply_furai_bonus(self, furai_name: str = "風雷合一") -> None:
        """
        風雷合一 Lv4 → 防具固有スキル +1 / Lv5 → +2
        (装飾品・護石・錬成追加スキルは対象外)
        """
        furai_lv = 0
        for s in self.skills:
            if s.name == furai_name:
                furai_lv = s.level
                break
        if furai_lv < 4:
            return
        bonus = 1 if furai_lv == 4 else 2

        armor_skill_names = set()
        for e in (self.head, self.body, self.arm, self.waist, self.leg):
            if e is None:
                continue
            for s in e.skills:
                if not s.is_additional and s.name != furai_name:
                    armor_skill_names.add(s.name)

        if not armor_skill_names:
            return

        skill_map = {s.name: s.level for s in self.skills}
        for name in armor_skill_names:
            skill_map[name] = skill_map.get(name, 0) + bonus
            max_lv = Masters.skill_max_level(name)
            if max_lv > 0 and skill_map[name] > max_lv:
                skill_map[name] = max_lv

        self.skills = [Skill(name=n, level=lv) for n, lv in sorted(skill_map.items())]

    def summary(self) -> str:
        lines = []
        for e in (self.head, self.body, self.arm, self.waist, self.leg, self.charm):
            if e and e.name:
                lines.append(e.simple_description())
        if self.decos:
            deco_names: Dict[str, int] = {}
            for d in self.decos:
                deco_names[d.disp_name] = deco_names.get(d.disp_name, 0) + 1
            deco_str = ", ".join(f"{n}x{c}" for n, c in deco_names.items())
            lines.append(f"装飾品：{deco_str}")
        lines.append(f"防御力：{self.total_def}")
        lines.append(
            f"耐性：火{self.fire} 水{self.water} 雷{self.thunder} 氷{self.ice} 龍{self.dragon}"
        )
        skill_str = " / ".join(f"{s.name}Lv{s.level}" for s in self.skills if s.level > 0)
        lines.append(f"スキル：{skill_str}")
        return "\n".join(lines)


class Masters:
    skills: List[Skill] = []
    generic_skills: List[Equipment] = []
    original_heads: List[Equipment] = []
    original_bodys: List[Equipment] = []
    original_arms: List[Equipment] = []
    original_waists: List[Equipment] = []
    original_legs: List[Equipment] = []
    heads: List[Equipment] = []
    bodys: List[Equipment] = []
    arms: List[Equipment] = []
    waists: List[Equipment] = []
    legs: List[Equipment] = []
    ideal_heads: List[Equipment] = []
    ideal_bodys: List[Equipment] = []
    ideal_arms: List[Equipment] = []
    ideal_waists: List[Equipment] = []
    ideal_legs: List[Equipment] = []
    charms: List[Equipment] = []
    decos: List[Equipment] = []
    cludes: List[Clude] = []
    augmentations: List[Augmentation] = []
    ideals: List[IdealAugmentation] = []
    _skill_max_level: Dict[str, int] = {}

    @classmethod
    def skill_max_level(cls, name: str) -> int:
        return cls._skill_max_level.get(name, 0)

    @classmethod
    def _apply_augmentation(cls, base: Equipment, aug: Augmentation) -> Equipment:
        return Equipment(
            name=aug.name,
            disp_name=aug.disp_name or f"{base.disp_name}(錬成)",
            kind=base.kind,
            sex=base.sex,
            rare=base.rare,
            slot1=aug.slot1,
            slot2=aug.slot2,
            slot3=aug.slot3,
            mindef=base.mindef + aug.def_,
            maxdef=base.maxdef + aug.def_,
            fire=base.fire + aug.fire,
            water=base.water + aug.water,
            thunder=base.thunder + aug.thunder,
            ice=base.ice + aug.ice,
            dragon=base.dragon + aug.dragon,
            row_no=base.row_no,
            skills=list(base.skills) + [s.copy(is_additional=True) for s in aug.skills],
            augmentation_table=base.augmentation_table,
            base_equipment=base,
        )

    @classmethod
    def _make_equipment_master(cls, originals: List[Equipment], kind: EquipKind) -> List[Equipment]:
        result = list(originals)
        for aug in cls.augmentations:
            if aug.kind != kind:
                continue
            base = next((o for o in originals if o.name == aug.base_name), None)
            if base is None:
                continue
            result.append(cls._apply_augmentation(base, aug))
        return result

    @classmethod
    def _calc_ideal_slot(cls, slot: List[int], increment: int) -> List[int]:
        slot = list(slot)
        while increment > 0:
            advanced = False
            for i in range(3):
                if slot[i] < 1:
                    slot[i] = 1
                    increment -= 1
                    advanced = True
                    break
            if advanced:
                continue
            for i in range(3):
                if slot[i] < 4:
                    slot[i] += 1
                    increment -= 1
                    advanced = True
                    break
            if not advanced:
                break
        return slot

    @classmethod
    def _make_minus_patterns(cls, skill_minuses: List[int], base_skill_count: int, min_idx: int = 0) -> List[List[int]]:
        result: List[List[int]] = []
        first_zero = -1
        for i, v in enumerate(skill_minuses):
            if v == 0:
                first_zero = i
                break
        if first_zero < 0:
            result.append(list(skill_minuses))
        else:
            for i in range(min_idx, base_skill_count):
                sub = list(skill_minuses)
                sub[first_zero] = i + 1
                result.extend(cls._make_minus_patterns(sub, base_skill_count, i))
        return result

    @classmethod
    def _make_ideal_equipment_master(cls, equips: List[Equipment]) -> List[Equipment]:
        ideal_equips: List[Equipment] = []
        for equip in equips:
            ideal_equips.append(equip)
            if equip.base_equipment is not None:
                continue
            for ideal in cls.ideals:
                if not ideal.is_enabled:
                    continue
                if not (ideal.table == equip.augmentation_table or
                        (ideal.is_include_lower and equip.augmentation_table < ideal.table)):
                    continue
                base_skill_count = max(len(equip.skills), 1)
                minus_patterns = cls._make_minus_patterns(ideal.skill_minuses, base_skill_count)
                if not minus_patterns:
                    minus_patterns = [[]]
                for pidx, minus_pat in enumerate(minus_patterns):
                    new_e = Equipment(
                        name=f"{equip.name}_{pidx}_{ideal.name}",
                        disp_name=f"{equip.disp_name}_{ideal.disp_name}({pidx})",
                        kind=equip.kind,
                        sex=equip.sex,
                        rare=equip.rare,
                        mindef=equip.mindef + ideal.def_,
                        maxdef=equip.maxdef + ideal.def_,
                        fire=equip.fire + ideal.fire,
                        water=equip.water + ideal.water,
                        thunder=equip.thunder + ideal.thunder,
                        ice=equip.ice + ideal.ice,
                        dragon=equip.dragon + ideal.dragon,
                        row_no=equip.row_no,
                        skills=[],
                        generic_skills=list(ideal.generic_skills),
                        augmentation_table=equip.augmentation_table,
                        base_equipment=equip,
                        ideal=ideal,
                    )
                    slots = cls._calc_ideal_slot([equip.slot1, equip.slot2, equip.slot3], ideal.slot_increment)
                    new_e.slot1, new_e.slot2, new_e.slot3 = slots[0], slots[1], slots[2]
                    base_skills = [s.copy() for s in equip.skills]
                    for mi in minus_pat:
                        if 1 <= mi <= len(base_skills):
                            base_skills[mi - 1].level = max(0, base_skills[mi - 1].level - 1)
                    new_e.skills = [s for s in base_skills if s.level > 0]
                    for s in ideal.skills:
                        new_e.skills.append(s.copy(is_additional=True))
                    ideal_equips.append(new_e)
        return ideal_equips

    @classmethod
    def refresh_equipment_masters(cls) -> None:
        cls.heads = cls._make_equipment_master(cls.original_heads, EquipKind.HEAD)
        cls.bodys = cls._make_equipment_master(cls.original_bodys, EquipKind.BODY)
        cls.arms = cls._make_equipment_master(cls.original_arms, EquipKind.ARM)
        cls.waists = cls._make_equipment_master(cls.original_waists, EquipKind.WAIST)
        cls.legs = cls._make_equipment_master(cls.original_legs, EquipKind.LEG)

        cls.ideal_heads = cls._make_ideal_equipment_master(cls.heads)
        cls.ideal_bodys = cls._make_ideal_equipment_master(cls.bodys)
        cls.ideal_arms = cls._make_ideal_equipment_master(cls.arms)
        cls.ideal_waists = cls._make_ideal_equipment_master(cls.waists)
        cls.ideal_legs = cls._make_ideal_equipment_master(cls.legs)

    @classmethod
    def get_equip_by_name(cls, name: str) -> Optional[Equipment]:
        for lst in (
            cls.heads, cls.bodys, cls.arms, cls.waists, cls.legs,
            cls.ideal_heads, cls.ideal_bodys, cls.ideal_arms, cls.ideal_waists, cls.ideal_legs,
            cls.charms, cls.decos, cls.generic_skills,
        ):
            for e in lst:
                if e.name == name:
                    return e
        return None

    @classmethod
    def get_clude_names_by_base(cls, name: str) -> List[str]:
        names = {name}
        for lst in (
            cls.heads, cls.bodys, cls.arms, cls.waists, cls.legs,
            cls.ideal_heads, cls.ideal_bodys, cls.ideal_arms, cls.ideal_waists, cls.ideal_legs,
        ):
            for e in lst:
                if e.name == name:
                    names.add(e.name)
                if e.base_equipment and e.base_equipment.name == name:
                    names.add(e.name)
        return list(names)
