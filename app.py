import sys
from datetime import datetime, date
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QFrame, QProgressBar, 
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout, 
    QLineEdit, QComboBox, QSpinBox, QMessageBox, QGroupBox, QGridLayout,
    QCheckBox, QMenu, QDoubleSpinBox, QTimeEdit, QScrollArea, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QTime
from PyQt6.QtGui import QFont, QColor, QAction

import storage
import logic
from models import AppState, TaskTemplate, BookProject

# --- Stylesheet ---
DARK_STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QFrame#Sidebar { background-color: #252526; border-right: 1px solid #333333; }
QPushButton.NavButton { background-color: transparent; color: #aaaaaa; text-align: left; padding: 10px 20px; border: none; font-size: 16px; }
QPushButton.NavButton:hover { background-color: #2a2d2e; color: #ffffff; }
QPushButton.NavButton:checked { background-color: #37373d; color: #ffffff; border-left: 3px solid #007acc; }
QPushButton.ActionButton { background-color: #007acc; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
QPushButton.ActionButton:hover { background-color: #0098ff; }
QPushButton.StartButton { background-color: #2da44e; color: white; border-radius: 4px; font-weight: bold; padding: 6px; }
QPushButton.StopButton { background-color: #d73a49; color: white; border-radius: 4px; font-weight: bold; padding: 6px; }
QTableWidget { background-color: #1e1e1e; gridline-color: #333333; border: 1px solid #333333; }
QHeaderView::section { background-color: #252526; padding: 4px; border: 1px solid #333333; font-weight: bold; }
QGroupBox { border: 1px solid #454545; border-radius: 6px; margin-top: 20px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #007acc; }
QProgressBar { border: 1px solid #454545; border-radius: 4px; text-align: center; background-color: #2d2d2d; color: white; }
QProgressBar::chunk { background-color: #007acc; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit { background-color: #3c3c3c; border: 1px solid #555555; border-radius: 3px; padding: 4px; color: white; }
QScrollArea { border: none; background-color: transparent; }
"""

class ProfileEditDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Edit Profile & Skills")
        self.resize(500, 600)
        self.setStyleSheet("background-color: #252526;")
        
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: General Info
        self.tab_general = QWidget()
        form = QFormLayout(self.tab_general)
        
        self.edit_username = QLineEdit(self.state.profile.username)
        
        self.spin_xp = QSpinBox()
        self.spin_xp.setRange(0, 9999999)
        self.spin_xp.setValue(self.state.profile.xp)
        self.spin_xp.valueChanged.connect(self.on_xp_changed)
        
        self.spin_level = QSpinBox()
        self.spin_level.setRange(1, 1000)
        self.spin_level.setValue(self.state.profile.level)
        self.spin_level.valueChanged.connect(self.on_level_changed)
        
        self.spin_streak = QSpinBox()
        self.spin_streak.setRange(0, 3650)
        self.spin_streak.setValue(self.state.profile.streak_days)
        
        self.spin_freezes = QSpinBox()
        self.spin_freezes.setRange(0, 100)
        self.spin_freezes.setValue(self.state.profile.streak_freezes)
        
        form.addRow("Username:", self.edit_username)
        form.addRow("Total XP:", self.spin_xp)
        form.addRow("Level (Approx):", self.spin_level)
        form.addRow("Streak Days:", self.spin_streak)
        form.addRow("Streak Freezes:", self.spin_freezes)
        
        self.tabs.addTab(self.tab_general, "General")
        
        # Tab 2: Skills (Stats)
        self.tab_skills = QWidget()
        skills_layout = QVBoxLayout(self.tab_skills)
        
        self.skills_table = QTableWidget()
        self.skills_table.setColumnCount(2)
        self.skills_table.setHorizontalHeaderLabels(["Skill Name", "Level"])
        self.skills_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.skills_table.verticalHeader().setVisible(False)
        skills_layout.addWidget(self.skills_table)
        
        self.load_skills_table()
        
        self.tabs.addTab(self.tab_skills, "Skills")
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save All Changes")
        btn_save.setProperty("class", "ActionButton")
        btn_save.clicked.connect(self.save_all)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

    def on_xp_changed(self, val):
        # Update level approx
        lvl = 1 + (val // 500)
        self.spin_level.blockSignals(True)
        self.spin_level.setValue(lvl)
        self.spin_level.blockSignals(False)

    def on_level_changed(self, val):
        # Update XP to min for that level
        xp = (val - 1) * 500
        self.spin_xp.blockSignals(True)
        self.spin_xp.setValue(xp)
        self.spin_xp.blockSignals(False)

    def load_skills_table(self):
        self.skills_table.setRowCount(len(self.state.stats))
        for row, (name, stat) in enumerate(self.state.stats.items()):
            self.skills_table.setItem(row, 0, QTableWidgetItem(name.title()))
            
            spin = QSpinBox()
            spin.setRange(1, 1000)
            spin.setValue(stat.level())
            # Store stat name in the widget for retrieval
            spin.setProperty("stat_name", name)
            self.skills_table.setCellWidget(row, 1, spin)

    def save_all(self):
        # 1. Save General
        logic.update_profile_general(
            self.state,
            self.edit_username.text(),
            self.spin_xp.value(),
            self.spin_streak.value(),
            self.spin_freezes.value()
        )
        
        # 2. Save Skills
        for row in range(self.skills_table.rowCount()):
            spin = self.skills_table.cellWidget(row, 1)
            stat_name = spin.property("stat_name")
            new_level = spin.value()
            logic.update_stat_level(self.state, stat_name, new_level)
            
        self.accept()

class TaskDialog(QDialog):
    """Unified Dialog for Adding or Editing Tasks"""
    def __init__(self, parent=None, task: Optional[TaskTemplate] = None):
        super().__init__(parent)
        self.setWindowTitle("Add Task" if not task else "Edit Task")
        self.setModal(True)
        self.resize(500, 500)
        self.setStyleSheet("background-color: #252526;")
        
        self.task = task
        layout = QFormLayout(self)
        
        self.title_input = QLineEdit(task.title if task else "")
        self.desc_input = QLineEdit(task.description if task else "")
        self.cat_input = QLineEdit(task.category if task else "general")
        
        self.recurrence_input = QComboBox()
        self.recurrence_input.addItems(["daily", "weekly", "monthly", "once", "custom"])
        if task: self.recurrence_input.setCurrentText(task.recurrence)
        self.recurrence_input.currentTextChanged.connect(self.toggle_custom_fields)
        
        # Custom Recurrence
        self.custom_group = QGroupBox("Custom Recurrence")
        self.custom_layout = QVBoxLayout()
        self.every_n_box = QCheckBox("Every N Days")
        self.every_n_spin = QSpinBox()
        self.every_n_spin.setRange(1, 365)
        self.every_n_spin.setValue(task.custom_every_n_days if task and task.custom_every_n_days else 3)
        h_n = QHBoxLayout()
        h_n.addWidget(self.every_n_box)
        h_n.addWidget(self.every_n_spin)
        self.custom_layout.addLayout(h_n)
        
        self.weekdays_box = QCheckBox("Specific Weekdays")
        self.days_checks = []
        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        h_days = QHBoxLayout()
        for i, name in enumerate(days_names):
            cb = QCheckBox(name)
            if task and task.custom_weekdays and i in task.custom_weekdays:
                cb.setChecked(True)
            cb.toggled.connect(self.on_day_checked)
            self.days_checks.append(cb)
            h_days.addWidget(cb)
        self.custom_layout.addLayout(h_days)
        self.custom_layout.addWidget(self.weekdays_box) 
        
        self.every_n_box.toggled.connect(lambda c: self.weekdays_box.setChecked(False) if c else None)
        self.weekdays_box.toggled.connect(lambda c: self.every_n_box.setChecked(False) if c else None)
        if task:
            if task.custom_every_n_days: self.every_n_box.setChecked(True)
            if task.custom_weekdays: self.weekdays_box.setChecked(True)
        self.custom_group.setLayout(self.custom_layout)
        
        self.xp_input = QSpinBox()
        self.xp_input.setRange(0, 10000)
        self.xp_input.setValue(task.xp_reward if task else 50)
        self.points_input = QSpinBox()
        self.points_input.setRange(0, 10000)
        self.points_input.setValue(task.point_reward if task else 10)
        self.target_input = QSpinBox()
        self.target_input.setRange(0, 1440) 
        self.target_input.setValue(task.target_minutes if task and task.target_minutes else 30)
        self.stat_input = QLineEdit(task.stat_name if task and task.stat_name else "")

        layout.addRow("Title:", self.title_input)
        layout.addRow("Description:", self.desc_input)
        layout.addRow("Category:", self.cat_input)
        layout.addRow("Recurrence:", self.recurrence_input)
        layout.addRow(self.custom_group)
        layout.addRow("Target Min (0=None):", self.target_input)
        layout.addRow("XP Reward:", self.xp_input)
        layout.addRow("Points:", self.points_input)
        layout.addRow("Stat Name:", self.stat_input)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Task")
        save_btn.clicked.connect(self.accept)
        save_btn.setProperty("class", "ActionButton")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)
        self.toggle_custom_fields(self.recurrence_input.currentText())

    def on_day_checked(self):
        if self.sender().isChecked():
            self.weekdays_box.setChecked(True)
            self.every_n_box.setChecked(False)

    def toggle_custom_fields(self, text):
        self.custom_group.setVisible(text == "custom")

    def get_data(self):
        custom_n = None
        custom_days = None
        if self.recurrence_input.currentText() == "custom":
            if self.every_n_box.isChecked(): custom_n = self.every_n_spin.value()
            elif self.weekdays_box.isChecked(): custom_days = [i for i, cb in enumerate(self.days_checks) if cb.isChecked()]
        target = self.target_input.value()
        return {
            "title": self.title_input.text(),
            "desc": self.desc_input.text(),
            "cat": self.cat_input.text(),
            "recurrence": self.recurrence_input.currentText(),
            "target": target if target > 0 else None,
            "xp": self.xp_input.value(),
            "points": self.points_input.value(),
            "stat": self.stat_input.text() if self.stat_input.text() else None,
            "custom_n": custom_n,
            "custom_days": custom_days
        }

class DashboardPage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        profile_group = QGroupBox("Profile Overview")
        profile_layout = QGridLayout()
        
        self.lbl_level = QLabel("Level ??")
        self.lbl_level.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        
        # New: Show username
        self.lbl_username = QLabel("User")
        self.lbl_username.setStyleSheet("color: #aaaaaa; font-style: italic;")
        
        self.lbl_xp = QLabel("XP: 0")
        self.lbl_streak = QLabel("Streak: 0 🔥")
        
        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 500)
        self.xp_bar.setTextVisible(True)
        self.xp_bar.setFormat("%v / 500 XP to next level")
        
        profile_layout.addWidget(self.lbl_level, 0, 0)
        profile_layout.addWidget(self.lbl_username, 0, 1) # Added username
        profile_layout.addWidget(self.lbl_xp, 1, 0)
        profile_layout.addWidget(self.lbl_streak, 1, 1)
        profile_layout.addWidget(self.xp_bar, 2, 0, 1, 2)
        
        profile_group.setLayout(profile_layout)
        main_layout.addWidget(profile_group)

        self.lbl_active_task = QLabel("")
        self.lbl_active_task.setStyleSheet("color: #2da44e; font-weight: bold; font-size: 15px;")
        main_layout.addWidget(self.lbl_active_task)

        stats_group = QGroupBox("Key Skills")
        stats_layout = QGridLayout()
        # Ensure we always show something, pick first 4 or default
        target_stats = ["yazılım", "yazarlık", "liderlik", "içerik üretme"]
        row, col = 0, 0
        self.stat_widgets = {} 
        for name in target_stats:
            _ = self.state.stats.get(name) # ensure exists logic handles this if missing by defaulting
            frame = QFrame()
            frame.setStyleSheet("background-color: #2d2d2d; border-radius: 5px; padding: 5px;")
            frame_layout = QVBoxLayout(frame)
            lbl_name = QLabel(name.title())
            lbl_name.setStyleSheet("font-weight: bold; color: #007acc;")
            lbl_lvl = QLabel("Lvl 1")
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setFixedHeight(10)
            progress.setTextVisible(False)
            frame_layout.addWidget(lbl_name)
            frame_layout.addWidget(lbl_lvl)
            frame_layout.addWidget(progress)
            stats_layout.addWidget(frame, row, col)
            self.stat_widgets[name] = {"lvl_lbl": lbl_lvl, "prog_bar": progress}
            col += 1
            if col > 1: col = 0; row += 1
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        main_layout.addStretch()

    def refresh(self):
        p = self.state.profile
        self.lbl_level.setText(f"{p.level_name} (Lvl {p.level})")
        self.lbl_username.setText(f"User: {p.username}")
        self.lbl_xp.setText(f"Total XP: {p.xp}")
        self.lbl_streak.setText(f"Streak: {p.streak_days} 🔥 (Frz: {p.streak_freezes})")
        self.xp_bar.setValue(p.xp % 500)
        for name, widgets in self.stat_widgets.items():
            stat_obj = self.state.stats.get(name)
            if stat_obj:
                widgets["lvl_lbl"].setText(f"Level {stat_obj.level()}")
                pct = int(stat_obj.progress_to_next_level() * 100)
                widgets["prog_bar"].setValue(pct)

    def update_active_task_label(self):
        active_sessions = logic.get_all_active_sessions(self.state)
        if not active_sessions:
            self.lbl_active_task.setText("")
            return
        sess = active_sessions[0]
        task = self.state.tasks.get(sess.task_id)
        if not task: return
        start_dt = datetime.fromisoformat(sess.start_time)
        duration = datetime.now() - start_dt
        total_seconds = int(duration.total_seconds())
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)
        self.lbl_active_task.setText(f"⏱️ Active: {task.title} — {h:02d}:{m:02d}:{s:02d}")

class TasksPage(QWidget):
    def __init__(self, state: AppState, on_action_callback: Callable, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_action_callback = on_action_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Today's Agenda")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        add_btn = QPushButton("+ New Task")
        add_btn.setProperty("class", "ActionButton")
        add_btn.clicked.connect(self.open_add_dialog)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(add_btn)
        layout.addLayout(header)
        
        layout.addWidget(QLabel("🚀 Active Tasks"))
        self.active_table = QTableWidget()
        self.setup_table(self.active_table, ["Title", "Recur", "Target", "Progress", "XP", "Stat", "Active Time", "Action"])
        self.active_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.active_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, self.active_table))
        layout.addWidget(self.active_table)
        
        layout.addWidget(QLabel("✅ Completed Today"))
        self.comp_table = QTableWidget()
        self.setup_table(self.comp_table, ["Title", "Cat", "Recur", "Target", "Total Time"])
        self.comp_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.comp_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, self.comp_table))
        layout.addWidget(self.comp_table)
        self.refresh()

    def setup_table(self, table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def refresh(self):
        today = date.today()
        all_tasks = logic.get_tasks_for_date(self.state, today)
        active_list = []
        completed_list = []
        for t in all_tasks:
            if logic.is_task_completed_for_date(self.state, t, today): completed_list.append(t)
            else: active_list.append(t)
        self.active_table.setRowCount(len(active_list))
        for r, t in enumerate(active_list): self.set_active_row(r, t, today)
        self.comp_table.setRowCount(len(completed_list))
        for r, t in enumerate(completed_list): self.set_completed_row(r, t, today)

    def set_active_row(self, row, t: TaskTemplate, today: date):
        item_title = QTableWidgetItem(t.title)
        item_title.setData(Qt.ItemDataRole.UserRole, t.id)
        self.active_table.setItem(row, 0, item_title)
        self.active_table.setItem(row, 1, QTableWidgetItem(t.recurrence))
        target_str = f"{t.target_minutes}m" if t.target_minutes else "-"
        self.active_table.setItem(row, 2, QTableWidgetItem(target_str))
        mins_done = logic.get_task_minutes_for_date(self.state, t.id, today)
        if t.target_minutes:
            pbar = QProgressBar()
            pbar.setRange(0, t.target_minutes)
            pbar.setValue(min(mins_done, t.target_minutes))
            pbar.setFormat(f"{mins_done}/{t.target_minutes} min")
            pbar.setStyleSheet("QProgressBar { text-align: center; }")
            self.active_table.setCellWidget(row, 3, pbar)
        else: self.active_table.setItem(row, 3, QTableWidgetItem("-"))
        self.active_table.setItem(row, 4, QTableWidgetItem(str(t.xp_reward)))
        self.active_table.setItem(row, 5, QTableWidgetItem(t.stat_name or "-"))
        active_sess = logic.get_active_session(self.state, t.id)
        dur_item = QTableWidgetItem("..." if active_sess else "-")
        dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_table.setItem(row, 6, dur_item)
        btn_widget = QWidget()
        l = QHBoxLayout(btn_widget); l.setContentsMargins(4,2,4,2)
        btn = QPushButton("Stop" if active_sess else "Start")
        btn.setProperty("class", "StopButton" if active_sess else "StartButton")
        btn.clicked.connect(lambda ch, tid=t.id: self.on_action_callback(tid))
        l.addWidget(btn)
        self.active_table.setCellWidget(row, 7, btn_widget)

    def set_completed_row(self, row, t: TaskTemplate, today: date):
        item_title = QTableWidgetItem(t.title)
        item_title.setData(Qt.ItemDataRole.UserRole, t.id)
        mins_done = logic.get_task_minutes_for_date(self.state, t.id, today)
        self.comp_table.setItem(row, 0, item_title)
        self.comp_table.setItem(row, 1, QTableWidgetItem(t.category))
        self.comp_table.setItem(row, 2, QTableWidgetItem(t.recurrence))
        self.comp_table.setItem(row, 3, QTableWidgetItem(str(t.target_minutes or "-")))
        self.comp_table.setItem(row, 4, QTableWidgetItem(f"{mins_done} min"))

    def show_context_menu(self, pos: QPoint, table: QTableWidget):
        index = table.indexAt(pos)
        if not index.isValid(): return
        item = table.item(index.row(), 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()
        edit_act = QAction("Edit Task", self)
        del_act = QAction("Delete Task", self)
        edit_act.triggered.connect(lambda: self.open_edit_dialog(task_id))
        del_act.triggered.connect(lambda: self.delete_task(task_id))
        menu.addAction(edit_act)
        menu.addAction(del_act)
        menu.exec(table.viewport().mapToGlobal(pos))

    def open_add_dialog(self):
        dlg = TaskDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            logic.add_task_definition(
                self.state, data["title"], data["desc"], data["cat"], 
                data["recurrence"], data["target"], data["xp"], data["points"], 
                data["stat"], custom_every_n_days=data["custom_n"], custom_weekdays=data["custom_days"]
            )
            self.refresh()
            storage.save_state(self.state)

    def open_edit_dialog(self, task_id):
        task = self.state.tasks.get(task_id)
        if not task: return
        dlg = TaskDialog(self, task)
        if dlg.exec():
            data = dlg.get_data()
            task.title = data["title"]
            task.description = data["desc"]
            task.category = data["cat"]
            task.recurrence = data["recurrence"]
            task.target_minutes = data["target"]
            task.xp_reward = data["xp"]
            task.point_reward = data["points"]
            task.stat_name = data["stat"]
            task.custom_every_n_days = data["custom_n"]
            task.custom_weekdays = data["custom_days"]
            storage.save_state(self.state)
            self.refresh()

    def delete_task(self, task_id):
        if QMessageBox.question(self, "Confirm", "Delete task?") == QMessageBox.StandardButton.Yes:
            if task_id in self.state.tasks:
                del self.state.tasks[task_id]
                storage.save_state(self.state)
                self.refresh()

    def update_timers(self):
        for row in range(self.active_table.rowCount()):
            item_title = self.active_table.item(row, 0)
            if not item_title: continue
            task_id = item_title.data(Qt.ItemDataRole.UserRole)
            task = self.state.tasks.get(task_id)
            if task and task.target_minutes:
                mins = logic.get_task_minutes_for_date(self.state, task_id, date.today())
                pbar = self.active_table.cellWidget(row, 3)
                if isinstance(pbar, QProgressBar):
                    pbar.setValue(min(mins, task.target_minutes))
                    pbar.setFormat(f"{mins}/{task.target_minutes} min")
            active_sess = logic.get_active_session(self.state, task_id)
            item_dur = self.active_table.item(row, 6)
            if active_sess:
                start_dt = datetime.fromisoformat(active_sess.start_time)
                delta = datetime.now() - start_dt
                ts = int(delta.total_seconds())
                m, s = divmod(ts, 60)
                h, m = divmod(m, 60)
                item_dur.setText(f"{h:02d}:{m:02d}:{s:02d}")
                item_dur.setForeground(QColor("#2da44e"))
            else:
                item_dur.setText("-")
                item_dur.setForeground(QColor("#e0e0e0"))

# --- NEW: Book Page ---
class BookPage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        # Header
        self.lbl_header = QLabel("Active Book Project")
        self.lbl_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.layout.addWidget(self.lbl_header)
        
        # Content Container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.layout.addWidget(self.content_widget)
        
        self.layout.addStretch()

    def refresh(self):
        # Clear previous UI
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        # Find active book
        active_book = next((b for b in self.state.book_projects.values() if not b.is_completed), None)
        
        if not active_book:
            lbl = QLabel("No active book project found.\nGo to 'Routines' tab to create one!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #888; font-size: 16px; margin-top: 50px;")
            self.content_layout.addWidget(lbl)
            return

        # Display Book Details
        title_lbl = QLabel(f"📖 {active_book.title}")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; margin-bottom: 10px;")
        
        # Progress Bar
        pbar = QProgressBar()
        pbar.setRange(0, active_book.total_pages)
        pbar.setValue(active_book.pages_written)
        pbar.setFormat(f"%v / {active_book.total_pages} pages")
        pbar.setStyleSheet("QProgressBar { height: 30px; font-size: 14px; }")
        
        stats_lbl = QLabel(f"Remaining: {active_book.total_pages - active_book.pages_written} pages | Daily Target: {active_book.daily_target_pages}")
        stats_lbl.setStyleSheet("font-size: 14px; color: #ccc; margin-bottom: 20px;")
        
        # Input Section
        input_group = QGroupBox("Log Progress")
        input_form = QFormLayout()
        
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 500)
        self.pages_spin.setValue(active_book.daily_target_pages)
        
        btn_save = QPushButton("Save Progress")
        btn_save.setProperty("class", "ActionButton")
        btn_save.clicked.connect(lambda: self.save_progress(active_book))
        
        input_form.addRow("Pages Written Today:", self.pages_spin)
        input_form.addRow(btn_save)
        input_group.setLayout(input_form)
        
        self.content_layout.addWidget(title_lbl)
        self.content_layout.addWidget(pbar)
        self.content_layout.addWidget(stats_lbl)
        self.content_layout.addWidget(input_group)

    def save_progress(self, book):
        count = self.pages_spin.value()
        logic.update_book_progress(self.state, book.id, count, date.today())
        storage.save_state(self.state)
        QMessageBox.information(self, "Success", f"Logged {count} pages for '{book.title}'!")
        self.refresh()

class RoutinesPage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.init_ui()

    def init_ui(self):
        # Scroll Area setup
        outer_layout = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        
        # 1. Book Project (Creation Only)
        self.book_group = QGroupBox("Create New Book Project")
        self.book_layout = QVBoxLayout()
        self.book_group.setLayout(self.book_layout)
        self.layout.addWidget(self.book_group)

        # 2. Zikr
        self.zikr_group = QGroupBox("Daily Zikr")
        zikr_layout = QFormLayout()
        
        self.lbl_zikr_target = QLabel()
        
        # Target Update Row
        h_target = QHBoxLayout()
        self.spin_zikr_target = QSpinBox(); self.spin_zikr_target.setRange(1, 100000)
        btn_update_target = QPushButton("Update Target"); btn_update_target.setProperty("class", "ActionButton")
        btn_update_target.clicked.connect(self.update_zikr_target)
        h_target.addWidget(self.spin_zikr_target)
        h_target.addWidget(btn_update_target)
        
        self.spin_zikr = QSpinBox(); self.spin_zikr.setRange(0, 100000)
        btn_zikr_save = QPushButton("Save Zikr Count"); btn_zikr_save.setProperty("class", "ActionButton")
        btn_zikr_save.clicked.connect(self.save_zikr)
        
        zikr_layout.addRow("Current Target:", self.lbl_zikr_target)
        zikr_layout.addRow("Set New Target:", h_target)
        zikr_layout.addRow("Count Today:", self.spin_zikr)
        zikr_layout.addRow(btn_zikr_save)
        self.zikr_group.setLayout(zikr_layout)
        self.layout.addWidget(self.zikr_group)

        # 3. Daily Income
        self.income_group = QGroupBox("Daily Income")
        income_layout = QFormLayout()
        self.lbl_income_target = QLabel()
        self.spin_income = QDoubleSpinBox(); self.spin_income.setRange(0, 1000000)
        btn_income_save = QPushButton("Save Income"); btn_income_save.setProperty("class", "ActionButton")
        btn_income_save.clicked.connect(self.save_income)
        income_layout.addRow(self.lbl_income_target)
        income_layout.addRow("Total Income Today:", self.spin_income)
        income_layout.addRow(btn_income_save)
        self.income_group.setLayout(income_layout)
        self.layout.addWidget(self.income_group)

        # 4. Amca Actions
        self.amca_group = QGroupBox("Amca Actions")
        amca_layout = QFormLayout()
        self.lbl_amca_today = QLabel()
        self.spin_amca_xp = QSpinBox(); self.spin_amca_xp.setValue(10)
        btn_amca_add = QPushButton("Add Amca Action"); btn_amca_add.setProperty("class", "ActionButton")
        btn_amca_add.clicked.connect(self.add_amca)
        amca_layout.addRow(self.lbl_amca_today)
        amca_layout.addRow("XP Reward:", self.spin_amca_xp)
        amca_layout.addRow(btn_amca_add)
        self.amca_group.setLayout(amca_layout)
        self.layout.addWidget(self.amca_group)

        # 5. Wake Time
        self.wake_group = QGroupBox("Wake Time")
        wake_layout = QFormLayout()
        self.time_target = QTimeEdit(); self.time_target.setDisplayFormat("HH:mm")
        self.time_actual = QTimeEdit(); self.time_actual.setDisplayFormat("HH:mm")
        self.lbl_wake_penalty = QLabel("Penalty: 0.0")
        btn_wake_save = QPushButton("Save Wake Times"); btn_wake_save.setProperty("class", "ActionButton")
        btn_wake_save.clicked.connect(self.save_wake)
        wake_layout.addRow("Target Time:", self.time_target)
        wake_layout.addRow("Actual Time:", self.time_actual)
        wake_layout.addRow(self.lbl_wake_penalty)
        wake_layout.addRow(btn_wake_save)
        self.wake_group.setLayout(wake_layout)
        self.layout.addWidget(self.wake_group)
        
        self.layout.addStretch()
        self.scroll.setWidget(self.content_widget)
        outer_layout.addWidget(self.scroll)

    def refresh(self):
        today = date.today()
        d_str = today.isoformat()
        log = self.state.daily_logs.get(d_str)

        # 1. Book Creation Refresh
        # Only show form if no active book exists, OR always show but maybe collapsed?
        # User requested: "Routines kısmından sadece proje oluşturulsun"
        # I'll hide the group if there is an active book to keep it clean, 
        # or show a label saying "Active book exists".
        
        while self.book_layout.count():
            child = self.book_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        active_book = next((b for b in self.state.book_projects.values() if not b.is_completed), None)
        
        if not active_book:
            self.book_group.setVisible(True)
            self.book_group.setTitle("Create New Book Project")
            form = QFormLayout()
            self.book_title_edit = QLineEdit()
            self.book_total_edit = QSpinBox(); self.book_total_edit.setRange(1, 5000)
            self.book_daily_edit = QSpinBox(); self.book_daily_edit.setRange(1, 500); self.book_daily_edit.setValue(5)
            btn_create = QPushButton("Create Book Project"); btn_create.setProperty("class", "ActionButton")
            btn_create.clicked.connect(self.create_book)
            form.addRow("Title:", self.book_title_edit)
            form.addRow("Total Pages:", self.book_total_edit)
            form.addRow("Daily Target:", self.book_daily_edit)
            form.addRow(btn_create)
            self.book_layout.addLayout(form)
        else:
            # Hide the creation group or show info
            self.book_group.setVisible(True)
            self.book_group.setTitle("Book Project Status")
            lbl = QLabel(f"Active Project: '{active_book.title}'\nGo to 'Book' tab to manage progress.")
            lbl.setStyleSheet("color: #2da44e;")
            self.book_layout.addWidget(lbl)

        # 2. Zikr Refresh
        target = self.state.settings.zikr_daily_target
        self.lbl_zikr_target.setText(f"{target}")
        self.spin_zikr_target.setValue(target)
        self.spin_zikr.setValue(log.zikr_count if log else 0)

        # 3. Income Refresh
        self.lbl_income_target.setText(f"Monthly Target: {self.state.settings.monthly_income_target}")
        self.spin_income.setValue(log.income_amount if log else 0.0)

        # 4. Amca Refresh
        count = log.amca_count if log else 0
        self.lbl_amca_today.setText(f"Amca Actions Today: {count}")

        # 5. Wake Refresh
        if log and log.wake_target_time:
            self.time_target.setTime(QTime.fromString(log.wake_target_time, "HH:mm"))
        else:
            self.time_target.setTime(QTime(6, 0))
        if log and log.wake_actual_time:
            self.time_actual.setTime(QTime.fromString(log.wake_actual_time, "HH:mm"))
        else:
            self.time_actual.setTime(QTime.currentTime())
        penalty = log.wake_penalty if log else 0.0
        self.lbl_wake_penalty.setText(f"Wake Penalty: {penalty:.2f}")

    # --- Actions ---

    def create_book(self):
        title = self.book_title_edit.text()
        if not title: return
        logic.create_book_project(self.state, title, self.book_total_edit.value(), self.book_daily_edit.value())
        self.save_and_notify("Book project created!")
        self.refresh()

    def update_zikr_target(self):
        val = self.spin_zikr_target.value()
        logic.update_zikr_target(self.state, val)
        self.save_and_notify(f"Zikr target updated to {val}!")
        self.refresh()

    def save_zikr(self):
        logic.set_daily_zikr(self.state, date.today(), self.spin_zikr.value())
        self.save_and_notify("Zikr count saved!")

    def save_income(self):
        logic.set_daily_income(self.state, date.today(), self.spin_income.value())
        self.save_and_notify("Daily income saved and wallet updated!")

    def add_amca(self):
        logic.add_amca_action(self.state, self.spin_amca_xp.value())
        self.save_and_notify("Amca action added!")
        self.refresh()

    def save_wake(self):
        t_str = self.time_target.time().toString("HH:mm")
        a_str = self.time_actual.time().toString("HH:mm")
        logic.apply_wake_times(self.state, date.today(), t_str, a_str)
        self.save_and_notify("Wake times saved!")
        self.refresh()

    def save_and_notify(self, msg):
        storage.save_state(self.state)
        QMessageBox.information(self, "Success", msg)

class ProfilePage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.lbl_header = QLabel("My Profile")
        self.lbl_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        
        btn_edit = QPushButton("Edit Profile")
        btn_edit.setProperty("class", "ActionButton")
        btn_edit.clicked.connect(self.open_edit_dialog)
        
        header_layout.addWidget(self.lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(btn_edit)
        layout.addLayout(header_layout)
        
        # Profile Details Card
        details_group = QGroupBox("User Details")
        details_layout = QFormLayout()
        
        self.lbl_username = QLabel()
        self.lbl_level = QLabel()
        self.lbl_xp = QLabel()
        self.lbl_streak = QLabel()
        
        details_layout.addRow("Username:", self.lbl_username)
        details_layout.addRow("Level:", self.lbl_level)
        details_layout.addRow("Total XP:", self.lbl_xp)
        details_layout.addRow("Streak:", self.lbl_streak)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Skills Card
        skills_group = QGroupBox("Skills & Stats")
        self.skills_layout = QVBoxLayout()
        skills_group.setLayout(self.skills_layout)
        layout.addWidget(skills_group)
        
        layout.addStretch()
        self.refresh()

    def refresh(self):
        p = self.state.profile
        self.lbl_username.setText(p.username)
        self.lbl_level.setText(f"{p.level} ({p.level_name})")
        self.lbl_xp.setText(f"{p.xp:,}")
        self.lbl_streak.setText(f"{p.streak_days} days (Freezes: {p.streak_freezes})")
        
        # Refresh Skills List
        # Clear layout
        while self.skills_layout.count():
            item = self.skills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add bars
        for name, stat in self.state.stats.items():
            h = QHBoxLayout()
            lbl = QLabel(f"{name.title()} (Lvl {stat.level()})")
            lbl.setFixedWidth(150)
            
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(stat.progress_to_next_level() * 100))
            bar.setTextVisible(True)
            
            h.addWidget(lbl)
            h.addWidget(bar)
            self.skills_layout.addLayout(h)

    def open_edit_dialog(self):
        dlg = ProfileEditDialog(self.state, self)
        if dlg.exec():
            self.refresh()
            storage.save_state(self.state)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Life Gamification App v3.3")
        self.resize(1100, 750)
        self.state = storage.load_state()
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(1000)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(0, 20, 0, 20)
        
        # Date Display Label
        self.lbl_date = QLabel()
        self.lbl_date.setStyleSheet("color: #007acc; font-weight: bold; font-size: 14px; padding-left: 10px;")
        side_layout.addWidget(self.lbl_date)
        
        self.update_date_label()

        self.btn_dash = self.create_nav_button("Dashboard")
        self.btn_profile = self.create_nav_button("Profile") # NEW
        self.btn_tasks = self.create_nav_button("Tasks")
        self.btn_routines = self.create_nav_button("Routines")
        self.btn_book = self.create_nav_button("Book")
        
        side_layout.addWidget(self.btn_dash)
        side_layout.addWidget(self.btn_profile) # NEW
        side_layout.addWidget(self.btn_tasks)
        side_layout.addWidget(self.btn_routines)
        side_layout.addWidget(self.btn_book)
        side_layout.addStretch()
        side_layout.addWidget(QLabel("v3.3 Profile Edit"))
        
        self.stack = QStackedWidget()
        self.page_dash = DashboardPage(self.state)
        self.page_profile = ProfilePage(self.state) # NEW
        self.page_tasks = TasksPage(self.state, self.handle_task_action)
        self.page_routines = RoutinesPage(self.state)
        self.page_book = BookPage(self.state)
        
        self.stack.addWidget(self.page_dash)
        self.stack.addWidget(self.page_profile) # NEW
        self.stack.addWidget(self.page_tasks)
        self.stack.addWidget(self.page_routines)
        self.stack.addWidget(self.page_book)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)
        
        self.btn_dash.clicked.connect(lambda: self.switch_page(0))
        self.btn_profile.clicked.connect(lambda: self.switch_page(1)) # NEW
        self.btn_tasks.clicked.connect(lambda: self.switch_page(2))
        self.btn_routines.clicked.connect(lambda: self.switch_page(3))
        self.btn_book.clicked.connect(lambda: self.switch_page(4))
        self.btn_dash.setChecked(True)

    def update_date_label(self):
        now = datetime.now()
        day_map = {
            "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
            "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
        }
        day_en = now.strftime("%A")
        day_tr = day_map.get(day_en, day_en)
        date_str = now.strftime("%Y-%m-%d")
        self.lbl_date.setText(f"{date_str}\n{day_tr}")

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        return btn

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0: self.page_dash.refresh()
        elif index == 1: self.page_profile.refresh() # NEW
        elif index == 2: self.page_tasks.refresh()
        elif index == 3: self.page_routines.refresh()
        elif index == 4: self.page_book.refresh()

    def on_tick(self):
        self.page_dash.update_active_task_label()
        if self.stack.currentIndex() == 2: # Check index carefully
            self.page_tasks.update_timers()
        self.update_date_label()

    def handle_task_action(self, task_id: str):
        active = logic.get_active_session(self.state, task_id)
        if active:
            logic.stop_timer_for_session(self.state, active.id)
            task = self.state.tasks.get(task_id)
            today = date.today()
            if task and logic.is_task_completed_for_date(self.state, task, today):
                QMessageBox.information(self, "Task Completed!", f"Great job! You finished '{task.title}' for today.")
            self.page_tasks.refresh()
            self.page_dash.refresh()
            storage.save_state(self.state)
        else:
            logic.start_timer_for_task(self.state, task_id)
            self.page_tasks.refresh()
            self.page_dash.refresh()
            storage.save_state(self.state)

    def closeEvent(self, event):
        active = logic.get_all_active_sessions(self.state)
        for s in active: logic.stop_timer_for_session(self.state, s.id)
        storage.save_state(self.state)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())