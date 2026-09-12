"""
Dedicated Task Editor Popup Dialog for DigitalBrainEX AI.
Matches original AddTask.cs popup dialog.
"""
from typing import Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDate, QTime

from src.core.repository import DataRepository
from src.core.logger import logger


class TaskEditorDialog(QDialog):
    def __init__(self, parent=None, task_id: Optional[int] = None, default_project_id: int = 0):
        super().__init__(parent)
        self.task_id = task_id
        self.default_project_id = default_project_id
        self.saved_task_id: Optional[int] = None

        self.setWindowTitle("Edit Task" if self.task_id else "New Task")
        self.setMinimumSize(660, 580)
        self.resize(700, 620)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Task & Reminder" if self.task_id else "📋 Create New Task"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Task Name
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Task Name / Objective:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Enter task description or goal...")
        name_layout.addWidget(self.edit_name)
        layout.addLayout(name_layout)

        # Metadata Row: Project, Due Date, Priority, Status
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(12)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_project = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_project)
        meta_layout.addLayout(proj_col, stretch=2)

        due_col = QVBoxLayout()
        due_col.addWidget(QLabel("Due Date:"))
        self.edit_due_date = QDateEdit()
        self.edit_due_date.setCalendarPopup(True)
        self.edit_due_date.setDate(QDate.currentDate())
        due_col.addWidget(self.edit_due_date)
        meta_layout.addLayout(due_col, stretch=1)

        priority_col = QVBoxLayout()
        priority_col.addWidget(QLabel("Priority:"))
        self.combo_priority = QComboBox()
        self.combo_priority.addItems(["Normal", "High", "Critical", "Low"])
        priority_col.addWidget(self.combo_priority)
        meta_layout.addLayout(priority_col, stretch=1)

        status_col = QVBoxLayout()
        status_col.addWidget(QLabel("Status:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Active", "In Progress", "Closed"])
        status_col.addWidget(self.combo_status)
        meta_layout.addLayout(status_col, stretch=1)

        layout.addLayout(meta_layout)

        # Reminder Group Box
        reminder_group = QGroupBox("Reminder & Alarm Settings")
        rem_layout = QVBoxLayout(reminder_group)
        rem_layout.setSpacing(8)

        self.chk_reminder = QCheckBox("Enable Reminder for this Task")
        self.chk_reminder.toggled.connect(self._toggle_reminder_controls)
        rem_layout.addWidget(self.chk_reminder)

        rem_controls_layout = QHBoxLayout()
        self.radio_once = QRadioButton("Once")
        self.radio_daily = QRadioButton("Daily")
        self.radio_weekly = QRadioButton("Weekly")
        self.radio_once.setChecked(True)

        self.rem_button_group = QButtonGroup(self)
        self.rem_button_group.addButton(self.radio_once)
        self.rem_button_group.addButton(self.radio_daily)
        self.rem_button_group.addButton(self.radio_weekly)

        rem_controls_layout.addWidget(self.radio_once)
        rem_controls_layout.addWidget(self.radio_daily)
        rem_controls_layout.addWidget(self.radio_weekly)

        rem_controls_layout.addSpacing(16)
        rem_controls_layout.addWidget(QLabel("Alarm Time:"))
        self.edit_rem_time = QTimeEdit()
        self.edit_rem_time.setTime(QTime(10, 0))
        rem_controls_layout.addWidget(self.edit_rem_time)
        rem_controls_layout.addStretch()

        rem_layout.addLayout(rem_controls_layout)
        layout.addWidget(reminder_group)
        self._toggle_reminder_controls(False)

        # Task Notes
        layout.addWidget(QLabel("Task Details / Notes:"))
        self.edit_notes = QTextEdit()
        self.edit_notes.setPlaceholderText("Add checklist items, meeting follow-ups, or notes...")
        layout.addWidget(self.edit_notes, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Task")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_task)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _toggle_reminder_controls(self, enabled: bool):
        self.radio_once.setEnabled(enabled)
        self.radio_daily.setEnabled(enabled)
        self.radio_weekly.setEnabled(enabled)
        self.edit_rem_time.setEnabled(enabled)

    def _populate_projects(self):
        self.combo_project.clear()
        self.combo_project.addItem("General", userData="0")
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_project.addItem(name, userData=str(p.PojectID))
        except Exception as e:
            logger.error(f"Error populating task dialog projects: {e}")

    def _load_data(self):
        if self.task_id:
            t = DataRepository.get_task_by_id(self.task_id)
            if t:
                self.edit_name.setText(t.TaskName or "")
                self.edit_notes.setPlainText(t.Desc or "")

                if t.DueOn:
                    try:
                        qdate = QDate.fromString(t.DueOn[:10], "yyyy-MM-dd")
                        if qdate.isValid():
                            self.edit_due_date.setDate(qdate)
                    except Exception:
                        pass

                idx_status = self.combo_status.findText(t.Status or "Active")
                if idx_status >= 0:
                    self.combo_status.setCurrentIndex(idx_status)

                for i in range(self.combo_project.count()):
                    if self.combo_project.itemData(i) == str(t.PojectID):
                        self.combo_project.setCurrentIndex(i)
                        break

                if t.EnableReminder and t.EnableReminder.lower() in ("1", "true", "yes"):
                    self.chk_reminder.setChecked(True)
                    if t.ReminderTime:
                        try:
                            qtime = QTime.fromString(t.ReminderTime[:5], "hh:mm")
                            if qtime.isValid():
                                self.edit_rem_time.setTime(qtime)
                        except Exception:
                            pass
        else:
            if self.default_project_id != 0:
                for i in range(self.combo_project.count()):
                    if self.combo_project.itemData(i) == str(self.default_project_id):
                        self.combo_project.setCurrentIndex(i)
                        break

    def _save_task(self):
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a Task Name.")
            self.edit_name.setFocus()
            return

        due_date_str = self.edit_due_date.date().toString("yyyy-MM-dd")
        proj_id = int(self.combo_project.currentData() or 0)
        proj_name = self.combo_project.currentText()
        status = self.combo_status.currentText()
        notes = self.edit_notes.toPlainText()

        enable_rem = "1" if self.chk_reminder.isChecked() else "0"
        rem_type = "Once"
        if self.radio_daily.isChecked():
            rem_type = "Daily"
        elif self.radio_weekly.isChecked():
            rem_type = "Weekly"
        rem_time = self.edit_rem_time.time().toString("hh:mm")

        try:
            if self.task_id:
                DataRepository.update_task(
                    self.task_id,
                    TaskName=name,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                    DueOn=due_date_str,
                    Status=status,
                    Desc=notes,
                    EnableReminder=enable_rem,
                    ReminderType=rem_type,
                    ReminderTime=rem_time,
                )
                self.saved_task_id = self.task_id
            else:
                new_task = DataRepository.create_task(
                    name=name,
                    project_id=proj_id,
                    project_name=proj_name,
                    due_on=due_date_str,
                    desc=notes,
                    status=status,
                    enable_reminder=enable_rem,
                    reminder_type=rem_type,
                    reminder_time=rem_time,
                )
                self.saved_task_id = new_task.TaskID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving task: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save task:\n{e}")
