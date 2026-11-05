# -*- coding: utf-8 -*-
"""
Pure-Python fallback searcher (no ortools / native solver).
Used on Android where Google OR-Tools binaries are unavailable.
Strategy: filter candidate gear by required skills, then recursive combination
search with pruning. Good enough for typical skill counts on mobile.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import itertools

from .models import (
    Equipment, EquipKind, EquipSet, Masters, SearchCondition, Skill, CludeKind
)
from .data_loader import LogicConfig


def _slot_levels(s1: int, s2: int, s3: int) -> List[int]:
    """Return sorted list of slot sizes (descending)."""
    return sorted([s for s in (s1, s2, s3) if s > 0], reverse=True)


def _can_fit_decos(armor_slots: List[int], weapon_slots: List[int],
                  deco_sizes: List[int]) -> bool:
    """Greedy check if decorations fit into available slots."""
    slots = sorted(armor_slots + weapon_slots, reverse=True)
    need = sorted(deco_sizes, reverse=True)
    for d in need:
        placed = False
        for i, s in enumerate(slots):
            if s >= d:
                slots[i] = 0  # consumed
                slots.sort(reverse=True)
                placed = True
                break
        if not placed:
            return False
    return True


def _skill_map(equips: List[Equipment]) -> Dict[str, int]:
    m: Dict[str, int] = {}
    for e in equips:
        for s in e.marged_skills:
            m[s.name] = m.get(s.name, 0) + s.level
    return m


class PureSearcher:
    """Lightweight pure-Python searcher for Android."""

    def __init__(self, condition: SearchCondition):
        self.condition = condition
        self.result_sets: List[EquipSet] = []
        self.is_canceling = False
        self.furai_name = LogicConfig.instance().furai_name

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

        self.charms = list(Masters.charms) or [Equipment(name="", kind=EquipKind.CHARM)]
        self.decos = list(Masters.decos)

        # Apply cludes
        exclude = {c.name for c in Masters.cludes if c.kind == CludeKind.EXCLUDE}
        include = {c.name for c in Masters.cludes if c.kind == CludeKind.INCLUDE}

        def filt(lst: List[Equipment]) -> List[Equipment]:
            out = [e for e in lst if e.name not in exclude]
            if include:
                forced = [e for e in out if e.name in include]
                if forced:
                    return forced
            return out

        self.heads = filt(self.heads)
        self.bodys = filt(self.bodys)
        self.arms = filt(self.arms)
        self.waists = filt(self.waists)
        self.legs = filt(self.legs)

        # Pre-filter by relevant skills to reduce search space
        needed = {s.name for s in condition.skills}
        self.heads = self._filter_relevant(self.heads, needed) or self.heads[:30]
        self.bodys = self._filter_relevant(self.bodys, needed) or self.bodys[:30]
        self.arms = self._filter_relevant(self.arms, needed) or self.arms[:30]
        self.waists = self._filter_relevant(self.waists, needed) or self.waists[:30]
        self.legs = self._filter_relevant(self.legs, needed) or self.legs[:30]

        # Limit candidates for mobile performance
        MAX = 40
        self.heads = sorted(self.heads, key=lambda e: -e.maxdef)[:MAX]
        self.bodys = sorted(self.bodys, key=lambda e: -e.maxdef)[:MAX]
        self.arms = sorted(self.arms, key=lambda e: -e.maxdef)[:MAX]
        self.waists = sorted(self.waists, key=lambda e: -e.maxdef)[:MAX]
        self.legs = sorted(self.legs, key=lambda e: -e.maxdef)[:MAX]

        # Relevant decos
        self.rel_decos = [
            d for d in self.decos
            if any(s.name in needed for s in d.skills)
        ]

    def _filter_relevant(self, equips: List[Equipment], needed: set) -> List[Equipment]:
        scored = []
        for e in equips:
            sc = sum(s.level for s in e.marged_skills if s.name in needed)
            sc += e.slot1 + e.slot2 + e.slot3  # slot value
            if sc > 0 or e.maxdef > 100:
                scored.append((sc, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored]

    def exec_search(self, limit: int = 10) -> bool:
        """Search up to `limit` results. Returns True if exhausted."""
        needed = {s.name: s.level for s in self.condition.skills}
        weapon_slots = _slot_levels(
            self.condition.weapon_slot1,
            self.condition.weapon_slot2,
            self.condition.weapon_slot3,
        )
        found = 0
        seen = set()

        # Include empty option for each part
        heads = self.heads + [None]
        bodys = self.bodys + [None]
        arms = self.arms + [None]
        waists = self.waists + [None]
        legs = self.legs + [None]
        charms = self.charms

        for h, b, a, w, l in itertools.product(heads, bodys, arms, waists, legs):
            if self.is_canceling or found >= limit:
                break
            parts = [p for p in (h, b, a, w, l) if p is not None]
            # sex filter
            if self.condition.sex.value != 0:
                bad = any(
                    p.sex.value not in (0, self.condition.sex.value) for p in parts
                )
                if bad:
                    continue

            for charm in charms:
                if self.is_canceling or found >= limit:
                    break
                equips = parts + ([charm] if charm and charm.name else [])
                base_skills = _skill_map(equips)

                # Furai bonus estimate
                furai_lv = base_skills.get(self.furai_name, 0)
                if furai_lv >= 4:
                    bonus = 1 if furai_lv == 4 else 2
                    for p in parts:
                        for s in p.skills:
                            if not s.is_additional and s.name != self.furai_name:
                                base_skills[s.name] = base_skills.get(s.name, 0) + bonus

                # Remaining skill deficits
                deficit: Dict[str, int] = {}
                ok = True
                for name, req in needed.items():
                    cur = base_skills.get(name, 0)
                    if cur < req:
                        deficit[name] = req - cur
                # Cap skills at max
                # Try to fill deficit with decorations
                deco_combo = self._fill_with_decos(deficit, equips, weapon_slots)
                if deco_combo is None:
                    continue

                # Build set
                es = EquipSet(
                    head=h, body=b, arm=a, waist=w, leg=l,
                    charm=charm if charm and charm.name else None,
                    decos=deco_combo,
                )
                key = es.glpk_row_name = "|".join(
                    (p.name if p else "") for p in (h, b, a, w, l, charm)
                )
                if key in seen:
                    continue
                seen.add(key)
                es.compute_totals()
                es.apply_furai_bonus(self.furai_name)

                # Verify final skills
                final = {s.name: s.level for s in es.skills}
                if all(final.get(n, 0) >= lv for n, lv in needed.items()):
                    self.result_sets.append(es)
                    found += 1

        return found < limit  # exhausted if we couldn't fill limit

    def _fill_with_decos(
        self,
        deficit: Dict[str, int],
        equips: List[Equipment],
        weapon_slots: List[int],
    ) -> Optional[List[Equipment]]:
        if not deficit:
            return []

        armor_slots = []
        for e in equips:
            if e.kind != EquipKind.CHARM:
                armor_slots.extend(_slot_levels(e.slot1, e.slot2, e.slot3))
            else:
                armor_slots.extend(_slot_levels(e.slot1, e.slot2, e.slot3))

        # Greedy: pick highest-value deco for remaining deficit
        remaining = dict(deficit)
        chosen: List[Equipment] = []
        deco_sizes: List[int] = []

        # Sort decos by skill contribution density
        candidates = []
        for d in self.rel_decos:
            contrib = sum(
                min(s.level, remaining.get(s.name, 0))
                for s in d.skills
                if s.name in remaining
            )
            if contrib > 0:
                candidates.append((contrib / max(d.slot1, 1), contrib, d))
        candidates.sort(key=lambda x: -x[0])

        for _, contrib, d in candidates:
            if not remaining:
                break
            # Check if still useful
            c = sum(
                min(s.level, remaining.get(s.name, 0))
                for s in d.skills
                if s.name in remaining
            )
            if c <= 0:
                continue
            trial_sizes = deco_sizes + [d.slot1]
            if not _can_fit_decos(armor_slots, weapon_slots, trial_sizes):
                continue
            # Accept
            chosen.append(d)
            deco_sizes.append(d.slot1)
            for s in d.skills:
                if s.name in remaining:
                    remaining[s.name] -= s.level
                    if remaining[s.name] <= 0:
                        del remaining[s.name]

        if remaining:
            return None
        return chosen


# Unified Simulator that picks backend
class Simulator:
    def __init__(self):
        self.searcher = None
        self.is_searched_all = False
        self.is_canceling = False
        self._backend = "unknown"

    def load_data(self):
        from .data_loader import load_all_data
        load_all_data()

    def _make_searcher(self, condition: SearchCondition):
        try:
            from .searcher import Searcher
            s = Searcher(condition)
            self._backend = "ortools"
            return s
        except Exception:
            self._backend = "pure"
            return PureSearcher(condition)

    def search(self, condition: SearchCondition, limit: int = 10) -> List[EquipSet]:
        self.is_canceling = False
        self.searcher = self._make_searcher(condition)
        if hasattr(self.searcher, "is_canceling"):
            self.searcher.is_canceling = False
        self.is_searched_all = self.searcher.exec_search(limit)
        return self.searcher.result_sets

    def search_more(self, limit: int = 10) -> List[EquipSet]:
        if self.searcher is None:
            return []
        self.is_canceling = False
        if hasattr(self.searcher, "is_canceling"):
            self.searcher.is_canceling = False
        self.is_searched_all = self.searcher.exec_search(limit)
        return self.searcher.result_sets

    def cancel(self):
        self.is_canceling = True
        if self.searcher and hasattr(self.searcher, "is_canceling"):
            self.searcher.is_canceling = True
