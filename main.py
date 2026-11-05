# -*- coding: utf-8 -*-
"""RiseSim Kivy App - Main entry"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.lang import Builder

import threading
from typing import List, Optional

from core import (
    load_all_data, Simulator, SearchCondition, Skill, Masters, EquipSet
)

Builder.load_string("""
<SkillRow>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(36)
    spacing: dp(4)
    Label:
        text: root.skill_name
        size_hint_x: 0.45
        text_size: self.size
        halign: 'left'
        valign: 'middle'
    Spinner:
        id: level_spinner
        text: str(root.level)
        values: root.level_values
        size_hint_x: 0.25
        on_text: root.on_level_change(self.text)
    Button:
        text: '削除'
        size_hint_x: 0.3
        on_press: root.remove_me()

<ResultCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: dp(8)
    spacing: dp(2)
    canvas.before:
        Color:
            rgba: 0.15, 0.15, 0.2, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [6]
    Label:
        text: root.title
        size_hint_y: None
        height: dp(24)
        bold: True
        color: 0.4, 0.8, 1, 1
    Label:
        text: root.body
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
        halign: 'left'
        valign: 'top'
        color: 0.9, 0.9, 0.9, 1

<MainLayout>:
    orientation: 'vertical'
    padding: dp(8)
    spacing: dp(6)

    # --- Condition area ---
    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(6)
        Label:
            text: '武器スロ'
            size_hint_x: 0.2
        Spinner:
            id: ws1
            text: '0'
            values: [str(i) for i in range(5)]
            size_hint_x: 0.15
        Spinner:
            id: ws2
            text: '0'
            values: [str(i) for i in range(5)]
            size_hint_x: 0.15
        Spinner:
            id: ws3
            text: '0'
            values: [str(i) for i in range(5)]
            size_hint_x: 0.15
        Label:
            text: '件数'
            size_hint_x: 0.15
        Spinner:
            id: limit_spin
            text: '10'
            values: ['5', '10', '20', '50']
            size_hint_x: 0.2

    BoxLayout:
        size_hint_y: None
        height: dp(36)
        spacing: dp(6)
        CheckBox:
            id: ideal_check
            size_hint_x: 0.1
            active: False
        Label:
            text: '理想錬成を含める'
            size_hint_x: 0.4
            text_size: self.size
            halign: 'left'
            valign: 'middle'
        Label:
            text: ''
            size_hint_x: 0.5

    # Skill add
    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(4)
        Spinner:
            id: skill_spinner
            text: 'スキルを選択'
            values: root.skill_names
            size_hint_x: 0.5
        Spinner:
            id: skill_lv_spinner
            text: '1'
            values: [str(i) for i in range(1, 8)]
            size_hint_x: 0.2
        Button:
            text: '追加'
            size_hint_x: 0.3
            on_press: root.add_skill()

    Label:
        text: '選択中スキル'
        size_hint_y: None
        height: dp(24)
        bold: True

    ScrollView:
        size_hint_y: 0.25
        GridLayout:
            id: skill_list
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(2)

    BoxLayout:
        size_hint_y: None
        height: dp(44)
        spacing: dp(8)
        Button:
            text: '検索開始'
            on_press: root.do_search()
            background_color: 0.2, 0.6, 0.9, 1
        Button:
            text: '追加検索'
            on_press: root.do_search_more()
        Button:
            text: 'クリア'
            on_press: root.clear_results()

    Label:
        id: status_label
        text: '準備完了'
        size_hint_y: None
        height: dp(28)
        color: 0.7, 0.9, 0.7, 1

    ScrollView:
        id: result_scroll
        GridLayout:
            id: result_list
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(8)
            padding: dp(4)
""")


class SkillRow(BoxLayout):
    skill_name = StringProperty("")
    level = StringProperty("1")
    level_values = ListProperty(["1"])
    remove_callback = ObjectProperty(None)

    def __init__(self, skill_name: str, level: int, max_level: int, remove_cb, **kwargs):
        super().__init__(**kwargs)
        self.skill_name = skill_name
        self.level = str(level)
        self.level_values = [str(i) for i in range(1, max_level + 1)]
        self.remove_callback = remove_cb
        self.ids.level_spinner.text = str(level)

    def on_level_change(self, text):
        self.level = text

    def remove_me(self):
        if self.remove_callback:
            self.remove_callback(self)


class ResultCard(BoxLayout):
    title = StringProperty("")
    body = StringProperty("")


class MainLayout(BoxLayout):
    skill_names = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sim = Simulator()
        self.selected_skills: List[Skill] = []
        self.results: List[EquipSet] = []
        Clock.schedule_once(self._init_data, 0.1)

    def _init_data(self, dt):
        self.ids.status_label.text = "データ読み込み中..."
        def load():
            load_all_data()
            names = sorted([s.name for s in Masters.skills])
            Clock.schedule_once(lambda dt: self._on_loaded(names), 0)
        threading.Thread(target=load, daemon=True).start()

    def _on_loaded(self, names):
        self.skill_names = names
        self.ids.skill_spinner.values = names
        if names:
            self.ids.skill_spinner.text = names[0]
        self.ids.status_label.text = f"準備完了（スキル{len(names)}種）"

    def add_skill(self):
        name = self.ids.skill_spinner.text
        if name == "スキルを選択" or not name:
            return
        try:
            lv = int(self.ids.skill_lv_spinner.text)
        except ValueError:
            lv = 1
        max_lv = Masters.skill_max_level(name) or 7
        lv = min(lv, max_lv)
        # update existing or add
        for s in self.selected_skills:
            if s.name == name:
                s.level = lv
                self._refresh_skill_list()
                return
        self.selected_skills.append(Skill(name=name, level=lv))
        self._refresh_skill_list()

    def _remove_skill(self, row: SkillRow):
        self.selected_skills = [s for s in self.selected_skills if s.name != row.skill_name]
        self._refresh_skill_list()

    def _refresh_skill_list(self):
        self.ids.skill_list.clear_widgets()
        for s in self.selected_skills:
            max_lv = Masters.skill_max_level(s.name) or 7
            row = SkillRow(s.name, s.level, max_lv, self._remove_skill)
            self.ids.skill_list.add_widget(row)

    def _build_condition(self) -> SearchCondition:
        cond = SearchCondition()
        # sync levels from UI
        for child in self.ids.skill_list.children:
            if isinstance(child, SkillRow):
                for s in self.selected_skills:
                    if s.name == child.skill_name:
                        try:
                            s.level = int(child.level)
                        except ValueError:
                            pass
        cond.skills = [s.copy() for s in self.selected_skills]
        cond.weapon_slot1 = int(self.ids.ws1.text)
        cond.weapon_slot2 = int(self.ids.ws2.text)
        cond.weapon_slot3 = int(self.ids.ws3.text)
        cond.include_ideal_augmentation = self.ids.ideal_check.active
        return cond

    def do_search(self):
        if not self.selected_skills:
            self.ids.status_label.text = "スキルを追加してください"
            return
        cond = self._build_condition()
        limit = int(self.ids.limit_spin.text)
        self.ids.status_label.text = "検索中..."
        self.ids.result_list.clear_widgets()

        def run():
            try:
                results = self.sim.search(cond, limit=limit)
                Clock.schedule_once(lambda dt: self._show_results(results), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)

        threading.Thread(target=run, daemon=True).start()

    def do_search_more(self):
        if self.sim.searcher is None:
            self.do_search()
            return
        limit = int(self.ids.limit_spin.text)
        self.ids.status_label.text = "追加検索中..."

        def run():
            try:
                results = self.sim.search_more(limit=limit)
                Clock.schedule_once(lambda dt: self._show_results(results), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._show_error(str(e)), 0)

        threading.Thread(target=run, daemon=True).start()

    def _show_results(self, results: List[EquipSet]):
        self.results = results
        self.ids.result_list.clear_widgets()
        for i, es in enumerate(results, 1):
            card = ResultCard()
            card.title = f"結果 #{i}  防御{es.total_def}"
            card.body = es.summary()
            self.ids.result_list.add_widget(card)
        done = "（全件完了）" if self.sim.is_searched_all else ""
        self.ids.status_label.text = f"{len(results)} 件ヒット {done}"

    def _show_error(self, msg: str):
        self.ids.status_label.text = f"エラー: {msg}"

    def clear_results(self):
        self.ids.result_list.clear_widgets()
        self.results = []
        self.ids.status_label.text = "結果をクリアしました"


class RiseSimApp(App):
    def build(self):
        self.title = "RiseSim Kivy"
        return MainLayout()


if __name__ == "__main__":
    RiseSimApp().run()
