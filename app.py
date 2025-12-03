import sys
from datetime import datetime, date
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QFrame, QProgressBar, 
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout, 
    QLineEdit, QComboBox, QSpinBox, QMessageBox, QGroupBox, QGridLayout,
    QCheckBox, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QAction

import storage
import logic
from models import AppState, TaskTemplate

# --- Stylesheet (Kept same as before) ---
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
QLineEdit, QComboBox, QSpinBox { background-color: #3c3c3c; border: 1px solid #555555; border-radius: 3px; padding: 4px; color: white; }
"""

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
        
        # Custom Recurrence Fields
        self.custom_group = QGroupBox("Custom Recurrence")
        self.custom_layout = QVBoxLayout()
        
        # Every N days
        self.every_n_box = QCheckBox("Every N Days")
        self.every_n_spin = QSpinBox()
        self.every_n_spin.setRange(1, 365)
        self.every_n_spin.setValue(task.custom_every_n_days if task and task.custom_every_n_days else 3)
        h_n = QHBoxLayout()
        h_n.addWidget(self.every_n_box)
        h_n.addWidget(self.every_n_spin)
        self.custom_layout.addLayout(h_n)
        
        # Specific Weekdays
        self.weekdays_box = QCheckBox("Specific Weekdays")
        self.days_checks = []
        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        h_days = QHBoxLayout()
        for i, name in enumerate(days_names):
            cb = QCheckBox(name)
            if task and task.custom_weekdays and i in task.custom_weekdays:
                cb.setChecked(True)
            self.days_checks.append(cb)
            h_days.addWidget(cb)
        self.custom_layout.addLayout(h_days)
        self.custom_layout.addWidget(self.weekdays_box) # Logic trigger placeholder
        
        # Connect checkboxes logic
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

    def toggle_custom_fields(self, text):
        self.custom_group.setVisible(text == "custom")

    def get_data(self):
        custom_n = None
        custom_days = None
        
        if self.recurrence_input.currentText() == "custom":
            if self.every_n_box.isChecked():
                custom_n = self.every_n_spin.value()
            elif self.weekdays_box.isChecked():
                custom_days = [i for i, cb in enumerate(self.days_checks) if cb.isChecked()]

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
    # Kept identical to previous version, just ensuring imports work
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
        self.lbl_xp = QLabel("XP: 0")
        self.lbl_streak = QLabel("Streak: 0 🔥")
        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 500)
        self.xp_bar.setTextVisible(True)
        self.xp_bar.setFormat("%v / 500 XP to next level")
        
        profile_layout.addWidget(self.lbl_level, 0, 0)
        profile_layout.addWidget(self.lbl_xp, 0, 1)
        profile_layout.addWidget(self.lbl_streak, 0, 2)
        profile_layout.addWidget(self.xp_bar, 1, 0, 1, 3)
        profile_group.setLayout(profile_layout)
        main_layout.addWidget(profile_group)

        self.lbl_active_task = QLabel("")
        self.lbl_active_task.setStyleSheet("color: #2da44e; font-weight: bold; font-size: 15px;")
        main_layout.addWidget(self.lbl_active_task)

        stats_group = QGroupBox("Key Skills")
        stats_layout = QGridLayout()
        target_stats = ["yazılım", "yazarlık", "liderlik", "içerik üretme"]
        row, col = 0, 0
        self.stat_widgets = {} 
        for name in target_stats:
            _ = self.state.stats.get(name)
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
        self.lbl_xp.setText(f"Total XP: {p.xp}")
        self.lbl_streak.setText(f"Streak: {p.streak_days} 🔥 (Frz: {p.streak_freezes})")
        current_progress = p.xp % 500
        self.xp_bar.setValue(current_progress)
        
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
        
        # Header
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
        
        # Active Table
        layout.addWidget(QLabel("🚀 Active Tasks"))
        self.active_table = QTableWidget()
        self.setup_table(self.active_table, ["Title", "Recur", "Target", "Progress", "XP", "Stat", "Active Time", "Action"])
        self.active_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.active_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, self.active_table))
        layout.addWidget(self.active_table)
        
        # Completed Table
        layout.addWidget(QLabel("✅ Completed Today"))
        self.comp_table = QTableWidget()
        self.setup_table(self.comp_table, ["Title", "Cat", "Recur", "Target", "Total Time"])
        # Optional: Context menu on completed tasks too
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
        
        # Filter Tasks
        all_tasks = logic.get_tasks_for_date(self.state, today)
        active_list = []
        completed_list = []
        
        for t in all_tasks:
            if logic.is_task_completed_for_date(self.state, t, today):
                completed_list.append(t)
            else:
                active_list.append(t)
                
        # Populate Active
        self.active_table.setRowCount(len(active_list))
        for r, t in enumerate(active_list):
            self.set_active_row(r, t, today)
            
        # Populate Completed
        self.comp_table.setRowCount(len(completed_list))
        for r, t in enumerate(completed_list):
            self.set_completed_row(r, t, today)

    def set_active_row(self, row, t: TaskTemplate, today: date):
        # Title
        item_title = QTableWidgetItem(t.title)
        item_title.setData(Qt.ItemDataRole.UserRole, t.id) # Store ID
        self.active_table.setItem(row, 0, item_title)
        self.active_table.setItem(row, 1, QTableWidgetItem(t.recurrence))
        
        # Target
        target_str = f"{t.target_minutes}m" if t.target_minutes else "-"
        self.active_table.setItem(row, 2, QTableWidgetItem(target_str))
        
        # Progress Bar
        mins_done = logic.get_task_minutes_for_date(self.state, t.id, today)
        if t.target_minutes:
            pbar = QProgressBar()
            pbar.setRange(0, t.target_minutes)
            pbar.setValue(min(mins_done, t.target_minutes))
            pbar.setFormat(f"{mins_done}/{t.target_minutes} min")
            pbar.setStyleSheet("QProgressBar { text-align: center; }")
            self.active_table.setCellWidget(row, 3, pbar)
        else:
            self.active_table.setItem(row, 3, QTableWidgetItem("-"))
            
        self.active_table.setItem(row, 4, QTableWidgetItem(str(t.xp_reward)))
        self.active_table.setItem(row, 5, QTableWidgetItem(t.stat_name or "-"))
        
        # Timer Display
        active_sess = logic.get_active_session(self.state, t.id)
        dur_item = QTableWidgetItem("..." if active_sess else "-")
        dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_table.setItem(row, 6, dur_item)
        
        # Button
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
        
        # Get Task ID from column 0
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
                data["stat"], custom_every_n_days=data["custom_n"], 
                custom_weekdays=data["custom_days"]
            )
            self.refresh()
            storage.save_state(self.state)

    def open_edit_dialog(self, task_id):
        task = self.state.tasks.get(task_id)
        if not task: return
        dlg = TaskDialog(self, task)
        if dlg.exec():
            data = dlg.get_data()
            # Update fields
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
        res = QMessageBox.question(self, "Confirm Delete", "Delete this task? History will remain but task will be gone.")
        if res == QMessageBox.StandardButton.Yes:
            if task_id in self.state.tasks:
                del self.state.tasks[task_id]
                storage.save_state(self.state)
                self.refresh()

    def update_timers(self):
        # Update running duration only in Active Table column 6
        for row in range(self.active_table.rowCount()):
            item_title = self.active_table.item(row, 0)
            if not item_title: continue
            task_id = item_title.data(Qt.ItemDataRole.UserRole)
            
            # Update Progress Bar (live progress)
            task = self.state.tasks.get(task_id)
            if task and task.target_minutes:
                mins = logic.get_task_minutes_for_date(self.state, task_id, date.today())
                # Find widget
                pbar = self.active_table.cellWidget(row, 3)
                if isinstance(pbar, QProgressBar):
                    pbar.setValue(min(mins, task.target_minutes))
                    pbar.setFormat(f"{mins}/{task.target_minutes} min")

            # Update Duration Text
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Life Gamification App v3")
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
        
        self.btn_dash = self.create_nav_button("Dashboard")
        self.btn_tasks = self.create_nav_button("Tasks")
        side_layout.addWidget(self.btn_dash)
        side_layout.addWidget(self.btn_tasks)
        side_layout.addStretch()
        side_layout.addWidget(QLabel("v3.0 Recurrence"))
        
        self.stack = QStackedWidget()
        self.page_dash = DashboardPage(self.state)
        self.page_tasks = TasksPage(self.state, self.handle_task_action)
        self.stack.addWidget(self.page_dash)
        self.stack.addWidget(self.page_tasks)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)
        
        self.btn_dash.clicked.connect(lambda: self.switch_page(0))
        self.btn_tasks.clicked.connect(lambda: self.switch_page(1))
        self.btn_dash.setChecked(True)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        return btn

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0: self.page_dash.refresh()
        elif index == 1: self.page_tasks.refresh()

    def on_tick(self):
        self.page_dash.update_active_task_label()
        if self.stack.currentIndex() == 1:
            self.page_tasks.update_timers()

    def handle_task_action(self, task_id: str):
        active = logic.get_active_session(self.state, task_id)
        if active:
            # STOP
            logic.stop_timer_for_session(self.state, active.id)
            
            # Check for completion (Did this session finish the daily target?)
            task = self.state.tasks.get(task_id)
            today = date.today()
            if task and logic.is_task_completed_for_date(self.state, task, today):
                QMessageBox.information(self, "Task Completed!", f"Great job! You finished '{task.title}' for today.")
            
            self.page_tasks.refresh()
            self.page_dash.refresh()
            storage.save_state(self.state)
        else:
            # START
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