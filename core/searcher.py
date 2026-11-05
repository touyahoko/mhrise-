# -*- coding: utf-8 -*-
"""
Searcher - OR-Tools based equipment skill searcher
Ported from SimModel/Domain/Searcher.cs
Includes 風雷合一 (Furai Goi) special handling.
"""

from __future__ import annotations
from typing import Dict, List, Optional

from ortools.linear_solver import pywraplp

from .models import (
    Equipment, EquipKind, EquipSet, Masters, SearchCondition, Sex, Skill,
    CludeKind
)
from .data_loader import LogicConfig


HEAD_ROW = "head"
BODY_ROW = "body"
ARM_ROW = "arm"
WAIST_ROW = "waist"
LEG_ROW = "leg"
CHARM_ROW = "charm"
SLOT1_ROW = "slot1"
SLOT2_ROW = "slot2"
SLOT3_ROW = "slot3"
SLOT4_ROW = "slot4"
DEF_ROW = "def"
FIRE_ROW = "fire"
WATER_ROW = "water"
THUNDER_ROW = "thunder"
ICE_ROW = "ice"
DRAGON_ROW = "dragon"
C3_ROW = "c3"
C6_ROW = "c6"
C9_ROW = "c9"
C12_ROW = "c12"
C15_ROW = "c15"
SKILL_ROW_PREFIX = "skill_"
FURAI_EXIST_ROW_PREFIX = "furaiExist_"
FURAI_FLAG_ROW_PREFIX = "furaiFlag_"
SET_ROW_PREFIX = "set_"
CLUDE_ROW_PREFIX = "clude_"
IDEAL_ROW_PREFIX = "ideal_"
EQUIP_COL_PREFIX = "equip_"
FURAI4_COL_PREFIX = "furai4_"
FURAI5_COL_PREFIX = "furai5_"


def slot_calc(s1: int, s2: int, s3: int) -> List[int]:
    slots = [s1, s2, s3]
    result = [0, 0, 0, 0]
    for s in slots:
        if s >= 1:
            result[0] += 1
        if s >= 2:
            result[1] += 1
        if s >= 3:
            result[2] += 1
        if s >= 4:
            result[3] += 1
    return result


class Searcher:
    def __init__(self, condition: SearchCondition):
        self.condition = condition
        self.result_sets: List[EquipSet] = []
        self.failure_sets: List[EquipSet] = []
        self.is_canceling = False
        self.furai_name = LogicConfig.instance().furai_name  # "風雷合一"

        if condition.include_ideal_augmentation:
            self.heads = list(Masters.ideal_heads)
            self.bodys = list(Masters.ideal_bodys)
            self.arms = list(Masters.ideal_arms)
            self.waists = list(Masters.ideal_waists)
            self.legs = list(Masters.ideal_legs)
        else:
            self.heads = list(Masters.heads)
            self.bodys = list(Masters.bodys)
            self.arms = list(Masters.arms)
            self.waists = list(Masters.waists)
            self.legs = list(Masters.legs)

        self.charms = list(Masters.charms)
        self.decos = list(Masters.decos)
        self.generic_skills = list(Masters.generic_skills) if condition.include_ideal_augmentation else []

        self.solver = pywraplp.Solver.CreateSolver("SCIP")
        if self.solver is None:
            self.solver = pywraplp.Solver.CreateSolver("CBC")
        if self.solver is None:
            raise RuntimeError("No MIP solver available")

        self.variables: Dict[str, pywraplp.Variable] = {}
        self.constraints: Dict[str, pywraplp.Constraint] = {}

        self._set_variables()
        self._set_constraints()
        self._set_objective()
        self._set_datas()

    def dispose(self):
        self.solver = None
        self.variables.clear()
        self.constraints.clear()

    def _all_equips(self) -> List[Equipment]:
        return (
            self.heads + self.bodys + self.arms + self.waists + self.legs
            + self.charms + self.decos + self.generic_skills
        )

    # ------------------------------------------------------------------
    def _set_variables(self):
        for equip in self._all_equips():
            key = EQUIP_COL_PREFIX + equip.name
            var = self.solver.IntVar(0, self.solver.infinity(), key)
            self.variables[key] = var

        # 風雷合一: per-skill bonus variables (Lv4 → +1, Lv5 → +2)
        for skill in self.condition.skills:
            key4 = FURAI4_COL_PREFIX + skill.name
            self.variables[key4] = self.solver.IntVar(0, self.solver.infinity(), key4)
            key5 = FURAI5_COL_PREFIX + skill.name
            self.variables[key5] = self.solver.IntVar(0, self.solver.infinity(), key5)

    # ------------------------------------------------------------------
    def _set_constraints(self):
        self.constraints[HEAD_ROW] = self.solver.Constraint(0, 1, HEAD_ROW)
        self.constraints[BODY_ROW] = self.solver.Constraint(0, 1, BODY_ROW)
        self.constraints[ARM_ROW] = self.solver.Constraint(0, 1, ARM_ROW)
        self.constraints[WAIST_ROW] = self.solver.Constraint(0, 1, WAIST_ROW)
        self.constraints[LEG_ROW] = self.solver.Constraint(0, 1, LEG_ROW)
        self.constraints[CHARM_ROW] = self.solver.Constraint(0, 1, CHARM_ROW)

        wslot = slot_calc(
            self.condition.weapon_slot1,
            self.condition.weapon_slot2,
            self.condition.weapon_slot3,
        )
        self.constraints[SLOT1_ROW] = self.solver.Constraint(-wslot[0], self.solver.infinity(), SLOT1_ROW)
        self.constraints[SLOT2_ROW] = self.solver.Constraint(-wslot[1], self.solver.infinity(), SLOT2_ROW)
        self.constraints[SLOT3_ROW] = self.solver.Constraint(-wslot[2], self.solver.infinity(), SLOT3_ROW)
        self.constraints[SLOT4_ROW] = self.solver.Constraint(-wslot[3], self.solver.infinity(), SLOT4_ROW)

        self.constraints[DEF_ROW] = self.solver.Constraint(self.condition.def_req, self.solver.infinity(), DEF_ROW)
        self.constraints[FIRE_ROW] = self.solver.Constraint(self.condition.fire_req, self.solver.infinity(), FIRE_ROW)
        self.constraints[WATER_ROW] = self.solver.Constraint(self.condition.water_req, self.solver.infinity(), WATER_ROW)
        self.constraints[THUNDER_ROW] = self.solver.Constraint(self.condition.thunder_req, self.solver.infinity(), THUNDER_ROW)
        self.constraints[ICE_ROW] = self.solver.Constraint(self.condition.ice_req, self.solver.infinity(), ICE_ROW)
        self.constraints[DRAGON_ROW] = self.solver.Constraint(self.condition.dragon_req, self.solver.infinity(), DRAGON_ROW)

        if self.condition.include_ideal_augmentation:
            self.constraints[C3_ROW] = self.solver.Constraint(0, self.solver.infinity(), C3_ROW)
            self.constraints[C6_ROW] = self.solver.Constraint(0, self.solver.infinity(), C6_ROW)
            self.constraints[C9_ROW] = self.solver.Constraint(0, self.solver.infinity(), C9_ROW)
            self.constraints[C12_ROW] = self.solver.Constraint(0, self.solver.infinity(), C12_ROW)
            self.constraints[C15_ROW] = self.solver.Constraint(0, self.solver.infinity(), C15_ROW)

        for skill in self.condition.skills:
            key = SKILL_ROW_PREFIX + skill.name
            # fixed skill → equality, otherwise lower bound
            if skill.is_fixed:
                self.constraints[key] = self.solver.Constraint(skill.level, skill.level, key)
            else:
                self.constraints[key] = self.solver.Constraint(skill.level, self.solver.infinity(), key)

            # 風雷合一: exist / flag constraints ( >= 0 )
            exist_key = FURAI_EXIST_ROW_PREFIX + skill.name
            self.constraints[exist_key] = self.solver.Constraint(0, self.solver.infinity(), exist_key)
            flag_key = FURAI_FLAG_ROW_PREFIX + skill.name
            self.constraints[flag_key] = self.solver.Constraint(0, self.solver.infinity(), flag_key)

        # Clude
        for clude in Masters.cludes:
            names = Masters.get_clude_names_by_base(clude.name)
            fix = 1 if clude.kind == CludeKind.INCLUDE else 0
            key = CLUDE_ROW_PREFIX + clude.name
            self.constraints[key] = self.solver.Constraint(fix, fix, key)

        # Ideal required / one-part
        if self.condition.include_ideal_augmentation:
            for ideal in Masters.ideals:
                if not ideal.is_enabled and not ideal.is_required:
                    key = IDEAL_ROW_PREFIX + ideal.name
                    self.constraints[key] = self.solver.Constraint(0, 0, key)
                    continue
                key = IDEAL_ROW_PREFIX + ideal.name
                min_v = 1.0 if ideal.is_required else 0.0
                max_v = 1.0 if ideal.is_one else 5.0
                if not ideal.is_enabled:
                    max_v = 0.0
                self.constraints[key] = self.solver.Constraint(min_v, max_v, key)

    # ------------------------------------------------------------------
    def _score(self, equip: Equipment) -> int:
        if equip.kind == EquipKind.DECO:
            slot1 = -equip.slot1
            slot2 = slot3 = 0
        else:
            slot1, slot2, slot3 = equip.slot1, equip.slot2, equip.slot3

        score = 0
        if self.condition.prioritize_no_ideal and equip.ideal is not None:
            score -= 100
        score += equip.maxdef
        score *= 100
        if equip.kind == EquipKind.GSKILL:
            for i in range(5):
                score -= equip.generic_skills[i] * (i + 1) * 3
        score *= 20
        score += (1 if slot1 else 0) + (1 if slot2 else 0) + (1 if slot3 else 0)
        score *= 80
        score += slot1 + slot2 + slot3
        return score

    def _set_objective(self):
        objective = self.solver.Objective()
        for equip in self._all_equips():
            key = EQUIP_COL_PREFIX + equip.name
            objective.SetCoefficient(self.variables[key], self._score(equip))
        objective.SetMaximization()

    # ------------------------------------------------------------------
    def _set_equip_data(self, var: pywraplp.Variable, equip: Equipment):
        is_deco_or_gskill = equip.kind in (EquipKind.DECO, EquipKind.GSKILL)

        if equip.kind == EquipKind.HEAD:
            self.constraints[HEAD_ROW].SetCoefficient(var, 1)
        elif equip.kind == EquipKind.BODY:
            self.constraints[BODY_ROW].SetCoefficient(var, 1)
        elif equip.kind == EquipKind.ARM:
            self.constraints[ARM_ROW].SetCoefficient(var, 1)
        elif equip.kind == EquipKind.WAIST:
            self.constraints[WAIST_ROW].SetCoefficient(var, 1)
        elif equip.kind == EquipKind.LEG:
            self.constraints[LEG_ROW].SetCoefficient(var, 1)
        elif equip.kind == EquipKind.CHARM:
            self.constraints[CHARM_ROW].SetCoefficient(var, 1)

        if is_deco_or_gskill:
            s = equip.slot1
            if s >= 1:
                self.constraints[SLOT1_ROW].SetCoefficient(var, -1)
            if s >= 2:
                self.constraints[SLOT2_ROW].SetCoefficient(var, -1)
            if s >= 3:
                self.constraints[SLOT3_ROW].SetCoefficient(var, -1)
            if s >= 4:
                self.constraints[SLOT4_ROW].SetCoefficient(var, -1)
        else:
            sc = slot_calc(equip.slot1, equip.slot2, equip.slot3)
            self.constraints[SLOT1_ROW].SetCoefficient(var, sc[0])
            self.constraints[SLOT2_ROW].SetCoefficient(var, sc[1])
            self.constraints[SLOT3_ROW].SetCoefficient(var, sc[2])
            self.constraints[SLOT4_ROW].SetCoefficient(var, sc[3])

        if self.condition.sex != Sex.ALL:
            if equip.sex != Sex.ALL and equip.sex != self.condition.sex:
                var.SetUB(0)

        self.constraints[DEF_ROW].SetCoefficient(var, equip.maxdef)
        self.constraints[FIRE_ROW].SetCoefficient(var, equip.fire)
        self.constraints[WATER_ROW].SetCoefficient(var, equip.water)
        self.constraints[THUNDER_ROW].SetCoefficient(var, equip.thunder)
        self.constraints[ICE_ROW].SetCoefficient(var, equip.ice)
        self.constraints[DRAGON_ROW].SetCoefficient(var, equip.dragon)

        if self.condition.include_ideal_augmentation and C3_ROW in self.constraints:
            costs = list(equip.generic_skills[:5]) if equip.generic_skills else [0] * 5
            if is_deco_or_gskill:
                costs = [-c for c in costs]
            self.constraints[C3_ROW].SetCoefficient(var, costs[0])
            self.constraints[C6_ROW].SetCoefficient(var, costs[1])
            self.constraints[C9_ROW].SetCoefficient(var, costs[2])
            self.constraints[C12_ROW].SetCoefficient(var, costs[3])
            self.constraints[C15_ROW].SetCoefficient(var, costs[4])

        # Skill coefficients
        for cond_skill in self.condition.skills:
            for eq_skill in equip.marged_skills:
                if eq_skill.name == cond_skill.name:
                    key = SKILL_ROW_PREFIX + cond_skill.name
                    self.constraints[key].SetCoefficient(var, eq_skill.level)

        # --- 風雷合一: skill exist (armor only, non-additional skills) ---
        if equip.kind not in (EquipKind.DECO, EquipKind.CHARM, EquipKind.GSKILL):
            for cond_skill in self.condition.skills:
                for eq_skill in equip.skills:
                    if eq_skill.name == cond_skill.name and not eq_skill.is_additional:
                        exist_key = FURAI_EXIST_ROW_PREFIX + cond_skill.name
                        self.constraints[exist_key].SetCoefficient(var, 1)

        # --- 風雷合一: flag (piece has 風雷合一) ---
        has_furai = any(s.name == self.furai_name for s in equip.skills)
        if has_furai:
            for cond_skill in self.condition.skills:
                flag_key = FURAI_FLAG_ROW_PREFIX + cond_skill.name
                self.constraints[flag_key].SetCoefficient(var, 1)

        # Clude
        for clude in Masters.cludes:
            names = Masters.get_clude_names_by_base(clude.name)
            if equip.name in names:
                key = CLUDE_ROW_PREFIX + clude.name
                if key in self.constraints:
                    self.constraints[key].SetCoefficient(var, 1)

        # Ideal
        if equip.ideal is not None and self.condition.include_ideal_augmentation:
            key = IDEAL_ROW_PREFIX + equip.ideal.name
            if key in self.constraints:
                self.constraints[key].SetCoefficient(var, 1)

    def _set_datas(self):
        for equip in self._all_equips():
            key = EQUIP_COL_PREFIX + equip.name
            self._set_equip_data(self.variables[key], equip)

        # 風雷合一 bonus variables → skill / exist / flag coefficients
        for skill in self.condition.skills:
            if skill.name == self.furai_name:
                continue  # 風雷合一 itself is not boosted by itself

            furai4 = self.variables[FURAI4_COL_PREFIX + skill.name]
            furai5 = self.variables[FURAI5_COL_PREFIX + skill.name]

            # skill level +1 / +2
            self.constraints[SKILL_ROW_PREFIX + skill.name].SetCoefficient(furai4, 1)
            self.constraints[SKILL_ROW_PREFIX + skill.name].SetCoefficient(furai5, 2)

            # exist: need at least one armor skill (furai vars consume 1)
            self.constraints[FURAI_EXIST_ROW_PREFIX + skill.name].SetCoefficient(furai4, -1)
            self.constraints[FURAI_EXIST_ROW_PREFIX + skill.name].SetCoefficient(furai5, -1)

            # flag: need 4 / 5 pieces with 風雷合一
            self.constraints[FURAI_FLAG_ROW_PREFIX + skill.name].SetCoefficient(furai4, -4)
            self.constraints[FURAI_FLAG_ROW_PREFIX + skill.name].SetCoefficient(furai5, -5)

    # ------------------------------------------------------------------
    def exec_search(self, limit: int = 10) -> bool:
        target = len(self.result_sets) + limit
        while len(self.result_sets) < target:
            if self.is_canceling:
                return False
            status = self.solver.Solve()
            if status != pywraplp.Solver.OPTIMAL:
                return True
            equip_set = self._make_set()
            if equip_set is None:
                return True
            equips = equip_set.existing_equips_without_decos()
            if equips:
                key = SET_ROW_PREFIX + equip_set.glpk_row_name
                new_c = self.solver.Constraint(0, len(equips) - 1, key)
                self.constraints[key] = new_c
                for e in equips:
                    vkey = EQUIP_COL_PREFIX + e.name
                    if vkey in self.variables:
                        new_c.SetCoefficient(self.variables[vkey], 1)
            self.result_sets.append(equip_set)
        return False

    def _make_set(self) -> Optional[EquipSet]:
        equip_set = EquipSet()
        has_data = False
        for key, var in self.variables.items():
            if not key.startswith(EQUIP_COL_PREFIX):
                continue
            val = var.solution_value()
            if val < 0.5:
                continue
            name = key[len(EQUIP_COL_PREFIX):]
            equip = Masters.get_equip_by_name(name)
            if equip is None or not equip.name:
                continue
            has_data = True
            cnt = int(round(val))
            if equip.kind == EquipKind.HEAD:
                equip_set.head = equip
            elif equip.kind == EquipKind.BODY:
                equip_set.body = equip
            elif equip.kind == EquipKind.ARM:
                equip_set.arm = equip
            elif equip.kind == EquipKind.WAIST:
                equip_set.waist = equip
            elif equip.kind == EquipKind.LEG:
                equip_set.leg = equip
            elif equip.kind == EquipKind.CHARM:
                equip_set.charm = equip
            elif equip.kind == EquipKind.DECO:
                for _ in range(cnt):
                    equip_set.decos.append(equip)
        if not has_data:
            return None
        names = []
        for e in (equip_set.head, equip_set.body, equip_set.arm, equip_set.waist, equip_set.leg, equip_set.charm):
            names.append(e.name if e else "")
        equip_set.glpk_row_name = "|".join(names)
        equip_set.compute_totals()
        # Apply 風雷合一 bonus for display
        equip_set.apply_furai_bonus(self.furai_name)
        return equip_set


class Simulator:
    def __init__(self):
        self.searcher: Optional[Searcher] = None
        self.is_searched_all = False
        self.is_canceling = False

    def load_data(self):
        from .data_loader import load_all_data
        load_all_data()

    def search(self, condition: SearchCondition, limit: int = 10) -> List[EquipSet]:
        self.is_canceling = False
        if self.searcher is not None:
            self.searcher.dispose()
        self.searcher = Searcher(condition)
        self.is_searched_all = self.searcher.exec_search(limit)
        return self.searcher.result_sets

    def search_more(self, limit: int = 10) -> List[EquipSet]:
        if self.searcher is None:
            return []
        self.is_canceling = False
        self.is_searched_all = self.searcher.exec_search(limit)
        return self.searcher.result_sets

    def cancel(self):
        self.is_canceling = True
        if self.searcher:
            self.searcher.is_canceling = True
