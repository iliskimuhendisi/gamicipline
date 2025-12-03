import sys
from typing import Optional, Callable
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QFrame, QProgressBar, 
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout, 
    QLineEdit, QComboBox, QSpinBox, QMessageBox, QGroupBox, QGridLayout,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor

import storage
import logic
from models import AppState, TimerSession

# --- Dark Theme Stylesheet ---
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}
QFrame#Sidebar {
    background-color: #252526;
    border-right: 1px solid #333333;
}
QPushButton.NavButton {
    background-color: transparent;
    color: #aaaaaa;
    text-align: left;
    padding: 10px 20px;
    border: none;
    font-size: 16px;
}
QPushButton.NavButton:hover {
    background-color: #2a2d2e;
    color: #ffffff;
}
QPushButton.NavButton:checked {
    background-color: #37373d;
    color: #ffffff;
    border-left: 3px solid #007acc;
}
QPushButton.ActionButton {
    background-color: #007acc;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton.ActionButton:hover {
    background-color: #0098ff;
}
QPushButton.StartButton {
    background-color: #2da44e; /* Green */
    color: white;
    border-radius: 4px;
    font-weight: bold;
    padding: 6px;
}
QPushButton.StopButton {
    background-color: #d73a49; /* Red */
    color: white;
    border-radius: 4px;
    font-weight: bold;
    padding: 6px;
}
QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #333333;
    border: 1px solid #333333;
}
QHeaderView::section {
    background-color: #252526;
    padding: 4px;
    border: 1px solid #333333;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #454545;
    border-radius: 6px;
    margin-top: 20px; 
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
    color: #007acc;
}
QProgressBar {
    border: 1px solid #454545;
    border-radius: 4px;
    text-align: center;
    background-color: #2d2d2d;
}
QProgressBar::chunk {
    background-color: #007acc;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px;
    color: white;
}
"""

class AddTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Task")
        self.setModal(True)
        self.resize(400, 300)
        self.setStyleSheet("background-color: #252526;")

        layout = QFormLayout(self)
        
        self.title_input = QLineEdit()
        self.desc_input = QLineEdit()
        self.cat_input = QLineEdit()
        
        self.recurrence_input = QComboBox()
        self.recurrence_input.addItems(["daily", "weekly", "monthly", "once", "custom"])
        
        self.xp_input = QSpinBox()
        self.xp_input.setRange(0, 10000)
        self.xp_input.setValue(50)
        
        self.points_input = QSpinBox()
        self.points_input.setRange(0, 10000)
        self.points_input.setValue(10)
        
        self.target_input = QSpinBox()
        self.target_input.setRange(0, 1440) # minutes
        self.target_input.setValue(30)
        
        self.stat_input = QLineEdit()
        self.stat_input.setPlaceholderText("Optional (e.g. yazılım)")

        layout.addRow("Title:", self.title_input)
        layout.addRow("Description:", self.desc_input)
        layout.addRow("Category:", self.cat_input)
        layout.addRow("Recurrence:", self.recurrence_input)
        layout.addRow("Target Min:", self.target_input)
        layout.addRow("XP Reward:", self.xp_input)
        layout.addRow("Points:", self.points_input)
        layout.addRow("Stat Name:", self.stat_input)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Create Task")
        save_btn.clicked.connect(self.accept)
        save_btn.setProperty("class", "ActionButton") # for styling
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            "title": self.title_input.text(),
            "desc": self.desc_input.text(),
            "cat": self.cat_input.text(),
            "recurrence": self.recurrence_input.currentText(),
            "target": self.target_input.value(),
            "xp": self.xp_input.value(),
            "points": self.points_input.value(),
            "stat": self.stat_input.text() if self.stat_input.text() else None
        }

class DashboardPage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Top Section: Profile ---
        profile_group = QGroupBox("Profile Overview")
        profile_layout = QGridLayout()
        
        self.lbl_level = QLabel("Level ??")
        self.lbl_level.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_xp = QLabel("XP: 0")
        self.lbl_streak = QLabel("Streak: 0 🔥")
        
        # XP Bar
        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 500) # Assuming 500xp per level roughly based on logic
        self.xp_bar.setTextVisible(True)
        self.xp_bar.setFormat("%v / 500 XP to next level")
        
        profile_layout.addWidget(self.lbl_level, 0, 0)
        profile_layout.addWidget(self.lbl_xp, 0, 1)
        profile_layout.addWidget(self.lbl_streak, 0, 2)
        profile_layout.addWidget(self.xp_bar, 1, 0, 1, 3)
        
        profile_group.setLayout(profile_layout)
        main_layout.addWidget(profile_group)

        # --- Active Task Section ---
        self.lbl_active_task = QLabel("")
        self.lbl_active_task.setStyleSheet("color: #2da44e; font-weight: bold; font-size: 15px;")
        main_layout.addWidget(self.lbl_active_task)

        # --- Middle Section: Stats Cards ---
        stats_group = QGroupBox("Key Skills")
        stats_layout = QGridLayout()
        
        # We will pick 4 specific stats to show for demo, or first 4
        target_stats = ["yazılım", "yazarlık", "liderlik", "içerik üretme"]
        
        row, col = 0, 0
        self.stat_widgets = {} 
        
        for name in target_stats:
            _ = self.state.stats.get(name) # Check existence
            
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
            
            # Store references to update later
            self.stat_widgets[name] = {
                "lvl_lbl": lbl_lvl,
                "prog_bar": progress
            }
            
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        main_layout.addStretch()

    def refresh(self):
        p = self.state.profile
        self.lbl_level.setText(f"{p.level_name} (Lvl {p.level})")
        self.lbl_xp.setText(f"Total XP: {p.xp}")
        self.lbl_streak.setText(f"Streak: {p.streak_days} 🔥 (Frz: {p.streak_freezes})")
        
        # Update XP Bar (Current level progress logic)
        # Logic says: Level = 1 + (XP // 500). 
        # So progress within current level is XP % 500.
        current_progress = p.xp % 500
        self.xp_bar.setValue(current_progress)
        
        # Update Stat Cards
        for name, widgets in self.stat_widgets.items():
            stat_obj = self.state.stats.get(name)
            if stat_obj:
                widgets["lvl_lbl"].setText(f"Level {stat_obj.level()}")
                # progress_to_next_level returns 0.0 to 1.0
                pct = int(stat_obj.progress_to_next_level() * 100)
                widgets["prog_bar"].setValue(pct)
            else:
                widgets["lvl_lbl"].setText("N/A")
                widgets["prog_bar"].setValue(0)
    
    def update_active_task_label(self):
        """Called by MainWindow timer to show currently running tasks."""
        active_sessions = logic.get_all_active_sessions(self.state)
        if not active_sessions:
            self.lbl_active_task.setText("")
            return

        # Show the first one as primary
        sess = active_sessions[0]
        task = self.state.tasks.get(sess.task_id)
        if not task:
            return

        start_dt = datetime.fromisoformat(sess.start_time)
        duration = datetime.now() - start_dt
        # Format HH:MM:SS
        total_seconds = int(duration.total_seconds())
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        
        self.lbl_active_task.setText(f"⏱️ Active: {task.title} — {time_str}")

class TasksPage(QWidget):
    def __init__(self, state: AppState, on_action_callback: Callable, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_action_callback = on_action_callback # Function to handle start/stop in MainWindow
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        title = QLabel("Tasks Library")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        
        add_btn = QPushButton("+ Add Task")
        add_btn.setProperty("class", "ActionButton")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.open_add_dialog)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Table
        self.table = QTableWidget()
        # Cols: Title, Cat, Recur, XP, Stat, Duration, Action
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Title", "Category", "Recur", "XP", "Stat", "Duration", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        self.refresh()

    def refresh(self):
        tasks = list(self.state.tasks.values())
        self.table.setRowCount(len(tasks))
        
        for row, t in enumerate(tasks):
            # Check for active session
            active_sess = logic.get_active_session(self.state, t.id)
            
            self.table.setItem(row, 0, QTableWidgetItem(t.title))
            self.table.setItem(row, 1, QTableWidgetItem(t.category))
            self.table.setItem(row, 2, QTableWidgetItem(t.recurrence))
            self.table.setItem(row, 3, QTableWidgetItem(str(t.xp_reward)))
            self.table.setItem(row, 4, QTableWidgetItem(t.stat_name if t.stat_name else "-"))
            
            # Duration Cell (Placeholder, updated by timer)
            dur_item = QTableWidgetItem("-" if not active_sess else "...")
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Store task ID in this item to easily find it later during updates
            dur_item.setData(Qt.ItemDataRole.UserRole, t.id)
            self.table.setItem(row, 5, dur_item)
            
            # Action Button
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 2, 5, 2)
            
            action_btn = QPushButton()
            if active_sess:
                action_btn.setText("Stop")
                action_btn.setProperty("class", "StopButton")
            else:
                action_btn.setText("Start")
                action_btn.setProperty("class", "StartButton")
                
            action_btn.clicked.connect(lambda checked, tid=t.id: self.on_action_callback(tid))
            btn_layout.addWidget(action_btn)
            
            self.table.setCellWidget(row, 6, btn_widget)

    def update_timers(self):
        """Called by MainWindow timer to update duration text for active tasks."""
        for row in range(self.table.rowCount()):
            # Get the duration item
            item = self.table.item(row, 5)
            if not item:
                continue
                
            task_id = item.data(Qt.ItemDataRole.UserRole)
            active_sess = logic.get_active_session(self.state, task_id)
            
            if active_sess:
                start_dt = datetime.fromisoformat(active_sess.start_time)
                delta = datetime.now() - start_dt
                total_seconds = int(delta.total_seconds())
                m, s = divmod(total_seconds, 60)
                h, m = divmod(m, 60)
                item.setText(f"{h:02d}:{m:02d}:{s:02d}")
                item.setForeground(QColor("#2da44e")) # Green text
            else:
                if item.text() != "-":
                    item.setText("-")
                    item.setForeground(QColor("#e0e0e0"))

    def open_add_dialog(self):
        dlg = AddTaskDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            logic.add_task_definition(
                self.state,
                title=data["title"],
                description=data["desc"],
                category=data["cat"],
                recurrence=data["recurrence"],
                target_minutes=data["target"] if data["target"] > 0 else None,
                xp_reward=data["xp"],
                point_reward=data["points"],
                stat_name=data["stat"]
            )
            self.refresh()
            QMessageBox.information(self, "Success", "Task created successfully!")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Life Gamification App")
        self.resize(1000, 700)
        
        # Load State
        self.state = storage.load_state()
        
        self.init_ui()
        self.update_ui_data()

        # Timer for UI updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(1000) # 1 second interval

    def init_ui(self):
        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(0, 20, 0, 20)
        side_layout.setSpacing(5)

        # Nav Buttons
        self.btn_dashboard = self.create_nav_button("Dashboard")
        self.btn_tasks = self.create_nav_button("Tasks")
        self.btn_wallet = self.create_nav_button("Wallet (WIP)")
        self.btn_wallet.setEnabled(False)
        self.btn_graphs = self.create_nav_button("Graphs (WIP)")
        self.btn_graphs.setEnabled(False)

        side_layout.addWidget(self.btn_dashboard)
        side_layout.addWidget(self.btn_tasks)
        side_layout.addWidget(self.btn_wallet)
        side_layout.addWidget(self.btn_graphs)
        side_layout.addStretch()
        
        # Version Label
        ver_lbl = QLabel("v2.1.0 Beta")
        ver_lbl.setStyleSheet("color: #666; padding-left: 20px;")
        side_layout.addWidget(ver_lbl)

        # --- Right Content Area ---
        self.stack = QStackedWidget()
        
        # Pages
        self.page_dashboard = DashboardPage(self.state)
        # Pass handle_task_action as callback to TasksPage
        self.page_tasks = TasksPage(self.state, self.handle_task_action)
        
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_tasks)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        # Signals
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.btn_tasks.clicked.connect(lambda: self.switch_page(1))
        
        # Set default
        self.btn_dashboard.setChecked(True)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        # Refresh data when switching
        if index == 0:
            self.page_dashboard.refresh()
        elif index == 1:
            self.page_tasks.refresh()

    def update_ui_data(self):
        self.page_dashboard.refresh()
        self.page_tasks.refresh()

    def on_tick(self):
        """Called every second by QTimer."""
        # Always update Dashboard active label
        self.page_dashboard.update_active_task_label()
        
        # Only update tasks table if visible
        if self.stack.currentIndex() == 1:
            self.page_tasks.update_timers()

    def handle_task_action(self, task_id: str):
        """Handles Start/Stop logic from TasksPage."""
        active_sess = logic.get_active_session(self.state, task_id)
        
        if active_sess:
            # STOP Timer
            finished_sess = logic.stop_timer_for_session(self.state, active_sess.id)
            
            # Check target duration
            task = self.state.tasks.get(task_id)
            mins = finished_sess.duration_seconds // 60
            
            if task and task.target_minutes and mins >= task.target_minutes:
                QMessageBox.information(
                    self, 
                    "Congratulations! 🎉", 
                    f"You completed the target time for '{task.title}'!\n\n"
                    f"Target: {task.target_minutes} min\n"
                    f"Actual: {mins} min"
                )
            
            # Refresh UIs
            self.page_tasks.refresh()
            self.page_dashboard.refresh()
            storage.save_state(self.state)
            
        else:
            # START Timer
            logic.start_timer_for_task(self.state, task_id)
            self.page_tasks.refresh()
            self.page_dashboard.refresh()
            # We don't necessarily save on every start, but safe to do so
            storage.save_state(self.state)

    def closeEvent(self, event):
        # Auto-stop all active sessions to preserve data
        active_sessions = logic.get_all_active_sessions(self.state)
        if active_sessions:
            print(f"Auto-stopping {len(active_sessions)} active sessions on exit...")
            for sess in active_sessions:
                logic.stop_timer_for_session(self.state, sess.id)
        
        storage.save_state(self.state)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())