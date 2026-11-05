#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test of the ported Searcher"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import load_all_data, Simulator, SearchCondition, Skill, Masters


def main():
    print("=== RiseSim Kivy - OR-Tools Searcher Test ===\n")
    load_all_data()

    sim = Simulator()

    # Example: 攻撃Lv7 + 見切りLv7  (common test)
    cond = SearchCondition()
    cond.skills = [
        Skill(name="攻撃", level=7),
        Skill(name="見切り", level=7),
    ]
    # 4-3-1 weapon slots for example
    cond.weapon_slot1 = 4
    cond.weapon_slot2 = 3
    cond.weapon_slot3 = 1

    print("Search condition:")
    for s in cond.skills:
        print(f"  {s.name} Lv{s.level}")
    print(f"  Weapon slots: {cond.weapon_slot1}-{cond.weapon_slot2}-{cond.weapon_slot3}")
    print()

    print("Searching (limit=5)...")
    results = sim.search(cond, limit=5)

    print(f"\nFound {len(results)} set(s):\n")
    for i, es in enumerate(results, 1):
        print(f"===== Result #{i} =====")
        print(es.summary())
        print()

    if not results:
        print("No results. Trying a lighter condition (攻撃Lv4 only)...")
        cond2 = SearchCondition()
        cond2.skills = [Skill(name="攻撃", level=4)]
        results2 = sim.search(cond2, limit=3)
        for i, es in enumerate(results2, 1):
            print(f"===== Result #{i} =====")
            print(es.summary())
            print()


if __name__ == "__main__":
    main()
