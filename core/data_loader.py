# -*- coding: utf-8 -*-
"""CSV data loader (ported from CsvOperation.cs)"""

from __future__ import annotations
import csv
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    Equipment, EquipKind, Masters, Sex, Skill, Clude, CludeKind,
    Augmentation, IdealAugmentation
)

def _resolve_dirs():
    """Resolve data/save dirs for desktop and Android (Buildozer)."""
    base = Path(__file__).resolve().parent.parent
    data = base / "data"
    save = base / "save"
    if data.exists():
        return data, save
    # Android: try app storage / assets
    try:
        from kivy.app import App
        from kivy.utils import platform
        if platform == "android":
            from android.storage import app_storage_path  # type: ignore
            root = Path(app_storage_path())
            data_a = root / "data"
            save_a = root / "save"
            # assets are unpacked beside the app; also try cwd
            for cand in (Path("data"), base / "data", data_a):
                if cand.exists():
                    data = cand
                    break
            save = save_a
            save.mkdir(parents=True, exist_ok=True)
            return data, save
    except Exception:
        pass
    # fallback: cwd
    if (Path.cwd() / "data").exists():
        return Path.cwd() / "data", Path.cwd() / "save"
    return data, save


DATA_DIR, SAVE_DIR = _resolve_dirs()


def _parse_int(s: str, default: int = 0) -> int:
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return default


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    lines = content.splitlines()
    if not lines:
        return []
    header_line = None
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            header_line = line.lstrip("#").strip()
            data_start = i + 1
            break
        elif line.strip():
            header_line = line
            data_start = i + 1
            break
    if header_line is None:
        return []
    reader = csv.DictReader([header_line] + lines[data_start:], skipinitialspace=True)
    rows = []
    for row in reader:
        clean = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
        if any(clean.values()):
            rows.append(clean)
    return rows


def _write_csv(path: Path, header: List[str], body: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(body)


class LogicConfig:
    _instance: Optional["LogicConfig"] = None

    def __init__(self):
        self.max_recent_skill_count = 20
        self.max_equip_skill_count = 5
        self.max_deco_skill_count = 2
        self.max_charm_skill_count = 2
        self.max_augmentation_skill_count = 7
        self.max_degree_of_parallelism = 4
        self.furai_name = "風雷合一"
        self._load()

    def _load(self):
        path = DATA_DIR / "LogicConfig.csv"
        rows = _read_csv_rows(path)
        if rows:
            row = rows[0]
            self.max_recent_skill_count = _parse_int(row.get("最近使ったスキルの記憶容量", "20"), 20)
            self.max_equip_skill_count = _parse_int(row.get("防具のスキル最大個数", "5"), 5)
            self.max_deco_skill_count = _parse_int(row.get("装飾品のスキル最大個数", "2"), 2)
            self.max_charm_skill_count = _parse_int(row.get("護石のスキル最大個数", "2"), 2)
            self.max_augmentation_skill_count = _parse_int(row.get("傀異錬成防具のスキル最大個数", "7"), 7)
            self.max_degree_of_parallelism = _parse_int(row.get("最大並列処理数", "4"), 4)

    @classmethod
    def instance(cls) -> "LogicConfig":
        if cls._instance is None:
            cls._instance = LogicConfig()
        return cls._instance


def load_skill_csv() -> None:
    path = DATA_DIR / "MHR_SKILL.csv"
    rows = _read_csv_rows(path)
    skill_map: Dict[str, Skill] = {}
    Masters.generic_skills = []
    for row in rows:
        name = row.get("スキル系統", "")
        if not name:
            continue
        level = _parse_int(row.get("必要ポイント", "0"))
        category = row.get("カテゴリ", "未分類") or "未分類"
        specific = row.get("発動スキル", "")
        cost = _parse_int(row.get("コスト", "0"))

        if name not in skill_map or skill_map[name].level < level:
            skill_map[name] = Skill(name=name, level=level, category=category)
        if specific:
            skill_map[name].specific_names[level] = specific

        gname = f"{name}(c{cost})"
        if cost > 0 and not any(g.name == gname for g in Masters.generic_skills):
            ge = Equipment(name=gname, disp_name=gname, kind=EquipKind.GSKILL)
            ge.skills.append(Skill(name=name, level=1))
            idx = {3: 0, 6: 1, 9: 2, 12: 3, 15: 4}.get(cost, -1)
            if idx >= 0:
                ge.generic_skills[idx] = 1
            Masters.generic_skills.append(ge)

    Masters.skills = list(skill_map.values())
    Masters._skill_max_level = {s.name: s.level for s in Masters.skills}
    print(f"[OK] Loaded {len(Masters.skills)} skills, {len(Masters.generic_skills)} generic skills")


def _load_equip_csv(filename: str, kind: EquipKind) -> List[Equipment]:
    path = DATA_DIR / filename
    rows = _read_csv_rows(path)
    cfg = LogicConfig.instance()
    equips: List[Equipment] = []
    for row in rows:
        name = row.get("名前", "")
        if not name:
            continue
        equip = Equipment(
            name=name,
            disp_name=name,
            kind=kind,
            sex=Sex(_parse_int(row.get("性別(0=両,1=男,2=女)", "0"))),
            rare=_parse_int(row.get("レア度", "0")),
            slot1=_parse_int(row.get("スロット1", "0")),
            slot2=_parse_int(row.get("スロット2", "0")),
            slot3=_parse_int(row.get("スロット3", "0")),
            mindef=_parse_int(row.get("初期防御力", "0")),
            maxdef=_parse_int(row.get("最終防御力", "0")) or _parse_int(row.get("初期防御力", "0")),
            fire=_parse_int(row.get("火耐性", "0")),
            water=_parse_int(row.get("水耐性", "0")),
            thunder=_parse_int(row.get("雷耐性", "0")),
            ice=_parse_int(row.get("氷耐性", "0")),
            dragon=_parse_int(row.get("龍耐性", "0")),
            row_no=_parse_int(row.get("仮番号", str(2**31 - 1)), 2**31 - 1),
            augmentation_table=_parse_int(row.get("錬成テーブル", "0")),
        )
        skills = []
        for i in range(1, cfg.max_equip_skill_count + 1):
            sname = row.get(f"スキル系統{i}", "")
            if not sname:
                break
            skills.append(Skill(name=sname, level=_parse_int(row.get(f"スキル値{i}", "0"))))
        equip.skills = skills
        equips.append(equip)
    return equips


def load_equip_csvs() -> None:
    Masters.original_heads = _load_equip_csv("MHR_EQUIP_HEAD.csv", EquipKind.HEAD)
    Masters.original_bodys = _load_equip_csv("MHR_EQUIP_BODY.csv", EquipKind.BODY)
    Masters.original_arms = _load_equip_csv("MHR_EQUIP_ARM.csv", EquipKind.ARM)
    Masters.original_waists = _load_equip_csv("MHR_EQUIP_WST.csv", EquipKind.WAIST)
    Masters.original_legs = _load_equip_csv("MHR_EQUIP_LEG.csv", EquipKind.LEG)
    print(
        f"[OK] Loaded equips: "
        f"H={len(Masters.original_heads)} B={len(Masters.original_bodys)} "
        f"A={len(Masters.original_arms)} W={len(Masters.original_waists)} "
        f"L={len(Masters.original_legs)}"
    )


def load_deco_csv() -> None:
    path = DATA_DIR / "MHR_DECO.csv"
    rows = _read_csv_rows(path)
    cfg = LogicConfig.instance()
    Masters.decos = []
    for row in rows:
        name = row.get("名前", "")
        if not name:
            continue
        equip = Equipment(
            name=name, disp_name=name, kind=EquipKind.DECO, sex=Sex.ALL,
            rare=_parse_int(row.get("レア度", "0")),
            slot1=_parse_int(row.get("スロットサイズ", "0")),
        )
        skills = []
        for i in range(1, cfg.max_deco_skill_count + 1):
            sname = row.get(f"スキル系統{i}", "")
            if not sname:
                break
            skills.append(Skill(name=sname, level=_parse_int(row.get(f"スキル値{i}", "0"))))
        equip.skills = skills
        Masters.decos.append(equip)
    print(f"[OK] Loaded {len(Masters.decos)} decorations")


def load_charm_csv() -> None:
    path = SAVE_DIR / "charm.csv"
    rows = _read_csv_rows(path)
    cfg = LogicConfig.instance()
    Masters.charms = []
    for row in rows:
        charm = Equipment(kind=EquipKind.CHARM)
        charm.slot1 = _parse_int(row.get("スロット1", "0"))
        charm.slot2 = _parse_int(row.get("スロット2", "0"))
        charm.slot3 = _parse_int(row.get("スロット3", "0"))
        skills = []
        for i in range(1, cfg.max_charm_skill_count + 1):
            sname = row.get(f"スキル系統{i}", "")
            if sname:
                skills.append(Skill(name=sname, level=_parse_int(row.get(f"スキル値{i}", "0"))))
        charm.skills = skills
        charm.name = row.get("内部管理ID", "") or str(uuid.uuid4())
        skill_disp = " ".join(f"{s.name}{s.level}" for s in skills)
        charm.disp_name = f"{skill_disp} {charm.slot1}-{charm.slot2}-{charm.slot3}".strip() or charm.name
        Masters.charms.append(charm)
    print(f"[OK] Loaded {len(Masters.charms)} charms")


def save_charm_csv() -> None:
    cfg = LogicConfig.instance()
    header = ["スロット1", "スロット2", "スロット3"]
    for i in range(1, cfg.max_charm_skill_count + 1):
        header += [f"スキル系統{i}", f"スキル値{i}"]
    header.append("内部管理ID")
    body = []
    for c in Masters.charms:
        row = [str(c.slot1), str(c.slot2), str(c.slot3)]
        for i in range(cfg.max_charm_skill_count):
            if i < len(c.skills):
                row += [c.skills[i].name, str(c.skills[i].level)]
            else:
                row += ["", "0"]
        row.append(c.name)
        body.append(row)
    _write_csv(SAVE_DIR / "charm.csv", header, body)


def load_clude_csv() -> None:
    path = SAVE_DIR / "clude.csv"
    rows = _read_csv_rows(path)
    Masters.cludes = []
    for row in rows:
        name = row.get("名前", "") or row.get("装備名", "")
        kind_str = row.get("種別", "") or row.get("種類", "")
        if not name:
            continue
        kind = CludeKind.INCLUDE if "固定" in kind_str or kind_str == "1" else CludeKind.EXCLUDE
        Masters.cludes.append(Clude(name=name, kind=kind))
    print(f"[OK] Loaded {len(Masters.cludes)} cludes")


def save_clude_csv() -> None:
    header = ["名前", "種別"]
    body = [[c.name, "固定" if c.kind == CludeKind.INCLUDE else "除外"] for c in Masters.cludes]
    _write_csv(SAVE_DIR / "clude.csv", header, body)


def load_augmentation_csv() -> None:
    path = SAVE_DIR / "augmentation.csv"
    rows = _read_csv_rows(path)
    cfg = LogicConfig.instance()
    Masters.augmentations = []
    kind_map = {"頭": EquipKind.HEAD, "胴": EquipKind.BODY, "腕": EquipKind.ARM,
                "腰": EquipKind.WAIST, "足": EquipKind.LEG, "脚": EquipKind.LEG}
    for row in rows:
        base = row.get("ベース装備名", "") or row.get("ベース", "")
        if not base:
            continue
        aug = Augmentation(
            base_name=base,
            kind=kind_map.get(row.get("部位", ""), EquipKind.ERROR),
            slot1=_parse_int(row.get("スロット1", "0")),
            slot2=_parse_int(row.get("スロット2", "0")),
            slot3=_parse_int(row.get("スロット3", "0")),
            def_=_parse_int(row.get("防御力増減", "0")),
            fire=_parse_int(row.get("火耐性増減", "0")),
            water=_parse_int(row.get("水耐性増減", "0")),
            thunder=_parse_int(row.get("雷耐性増減", "0")),
            ice=_parse_int(row.get("氷耐性増減", "0")),
            dragon=_parse_int(row.get("龍耐性増減", "0")),
            disp_name=row.get("名前", ""),
            name=row.get("管理用ID", "") or str(uuid.uuid4()),
        )
        skills = []
        for i in range(1, cfg.max_augmentation_skill_count + 1):
            sname = row.get(f"スキル系統{i}", "")
            if not sname:
                break
            skills.append(Skill(name=sname, level=_parse_int(row.get(f"スキル値{i}", "0")), is_additional=True))
        aug.skills = skills
        if not aug.disp_name:
            aug.disp_name = f"{base}(錬成)"
        Masters.augmentations.append(aug)
    print(f"[OK] Loaded {len(Masters.augmentations)} augmentations")


def load_ideal_csv() -> None:
    path = SAVE_DIR / "ideal.csv"
    rows = _read_csv_rows(path)
    Masters.ideals = []
    for row in rows:
        ideal = IdealAugmentation(
            name=row.get("管理用ID", "") or str(uuid.uuid4()),
            disp_name=row.get("名前", "") or f"理想T{row.get('テーブル', '0')}",
            table=_parse_int(row.get("テーブル", "0")),
            is_include_lower=row.get("下位含む", "") in ("1", "true", "True", "はい"),
            slot_increment=_parse_int(row.get("スロット追加", "0")),
            def_=_parse_int(row.get("防御力増減", "0")),
            fire=_parse_int(row.get("火耐性増減", "0")),
            water=_parse_int(row.get("水耐性増減", "0")),
            thunder=_parse_int(row.get("雷耐性増減", "0")),
            ice=_parse_int(row.get("氷耐性増減", "0")),
            dragon=_parse_int(row.get("龍耐性増減", "0")),
            is_one=row.get("1部位のみ", "") in ("1", "true", "True"),
            is_enabled=row.get("有効", "1") not in ("0", "false", "False"),
            is_required=row.get("必須", "") in ("1", "true", "True"),
        )
        for i, cost in enumerate([3, 6, 9, 12, 15]):
            ideal.generic_skills[i] = _parse_int(row.get(f"c{cost}", "0"))
        minus_str = row.get("スキルマイナス", "")
        if minus_str:
            ideal.skill_minuses = [_parse_int(x) for x in minus_str.split(",") if x.strip()]
        for i in range(1, 8):
            sname = row.get(f"スキル系統{i}", "")
            if not sname:
                break
            ideal.skills.append(Skill(name=sname, level=_parse_int(row.get(f"スキル値{i}", "1")), is_additional=True))
        Masters.ideals.append(ideal)
    print(f"[OK] Loaded {len(Masters.ideals)} ideal patterns")


def load_all_data() -> None:
    global DATA_DIR, SAVE_DIR
    DATA_DIR, SAVE_DIR = _resolve_dirs()
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    load_skill_csv()
    load_equip_csvs()
    load_deco_csv()
    load_charm_csv()
    load_clude_csv()
    load_augmentation_csv()
    load_ideal_csv()
    Masters.refresh_equipment_masters()
    print(
        f"[OK] Equipment masters refreshed: "
        f"H={len(Masters.heads)} IdealH={len(Masters.ideal_heads)}"
    )
    print("[OK] All master data loaded.")
