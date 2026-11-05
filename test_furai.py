#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""風雷合一の動作確認テスト"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import load_all_data, Simulator, SearchCondition, Skill, Masters


def main():
    print("=== 風雷合一 テスト ===\n")
    load_all_data()
    sim = Simulator()

    # しまき/なるかみ4部位で風雷合一Lv4 → 防具スキル+1 を狙う
    # 例: 集中を条件に入れ、しまき頭(集中+風雷)を含むセットが出るか
    cond = SearchCondition()
    cond.skills = [
        Skill(name="風雷合一", level=4),
        Skill(name="集中", level=2),   # しまき頭に集中1 → 風雷で+1されて2に
        Skill(name="体術", level=2),
    ]
    cond.weapon_slot1 = 0
    cond.weapon_slot2 = 0
    cond.weapon_slot3 = 0

    print("条件: 風雷合一Lv4 + 集中Lv2 + 体術Lv2")
    print("検索中...\n")
    results = sim.search(cond, limit=3)

    print(f"ヒット数: {len(results)}\n")
    for i, es in enumerate(results, 1):
        print(f"===== Result #{i} =====")
        print(es.summary())
        # 風雷合一レベル確認
        furai = next((s for s in es.skills if s.name == "風雷合一"), None)
        focus = next((s for s in es.skills if s.name == "集中"), None)
        print(f"  → 風雷合一={furai.level if furai else 0}, 集中={focus.level if focus else 0}")
        print()

    if not results:
        print("結果なし。条件を緩めて再試行...")
        cond2 = SearchCondition()
        cond2.skills = [Skill(name="風雷合一", level=4)]
        results2 = sim.search(cond2, limit=3)
        for i, es in enumerate(results2, 1):
            print(f"===== Result #{i} =====")
            print(es.summary())
            print()


if __name__ == "__main__":
    main()
