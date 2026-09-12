"""
TrackMe Application Usage & Productivity Analytics View for DigitalBrainEX AI.
Displays aggregated application time logs, active window timeline, and productivity stats.
"""
from datetime import date, datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QComboBox,
    QFrame,
)
from PyQt6.QtCore import Qt
from src.core.repository import DataRepository
from src.core.event_bus import event_bus, EVT_WINDOW_TRACKED
from src.core.logger import logger


class TrackMeView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ViewContentWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()
        # Data is loaded on first activation in _on_module_changed

        event_bus.subscribe(EVT_WINDOW_TRACKED, self._on_new_activity_logged)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        title_label = QLabel("TrackMe Usage")
        title_label.setObjectName("ViewTitleLabel")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        header_layout.addWidget(QLabel("Period:"))
        self.combo_period = QComboBox()
        self.combo_period.addItems(["Today", "Yesterday", "Last 7 Days", "All Time"])
        self.combo_period.currentIndexChanged.connect(self.load_data)
        header_layout.addWidget(self.combo_period)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_data)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(header_layout)

        # Metric summary cards
        metric_layout = QHBoxLayout()

        self.card_total_time = self._create_card("Total Time Logged", "0h 0m")
        self.card_top_app = self._create_card("Most Used Application", "None")
        self.card_entries = self._create_card("Activity Samples", "0")

        metric_layout.addWidget(self.card_total_time)
        metric_layout.addWidget(self.card_top_app)
        metric_layout.addWidget(self.card_entries)
        main_layout.addLayout(metric_layout)

        # Splitter: Summary by App (45%), Raw Timeline (55%)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # App Summary Table
        summary_container = QWidget()
        summary_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        summary_layout = QVBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_title = QLabel("Time Spent by Application")
        summary_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #000000;")
        summary_layout.addWidget(summary_title)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(3)
        self.summary_table.setHorizontalHeaderLabels(["Application", "Total Time", "Samples"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.summary_table.setColumnWidth(1, 100)
        self.summary_table.setColumnWidth(2, 80)
        self.summary_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setShowGrid(True)
        self.summary_table.verticalHeader().setVisible(True)
        self.summary_table.verticalHeader().setDefaultSectionSize(26)
        summary_layout.addWidget(self.summary_table)
        splitter.addWidget(summary_container)

        # Recent Activity Timeline Table
        recent_container = QWidget()
        recent_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        recent_layout = QVBoxLayout(recent_container)
        recent_layout.setContentsMargins(12, 0, 0, 0)
        recent_title = QLabel("Recent Active Window Timeline")
        recent_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #000000;")
        recent_layout.addWidget(recent_title)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(3)
        self.recent_table.setHorizontalHeaderLabels(["Time", "Application", "Window Title"])
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.recent_table.setColumnWidth(0, 90)
        self.recent_table.setColumnWidth(1, 140)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setShowGrid(True)
        self.recent_table.verticalHeader().setVisible(True)
        self.recent_table.verticalHeader().setDefaultSectionSize(26)
        recent_layout.addWidget(self.recent_table)
        splitter.addWidget(recent_container)

        splitter.setSizes([450, 550])
        main_layout.addWidget(splitter)

    def _create_card(self, title: str, default_val: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardWidget")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(default_val)
        lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #2563eb;")
        lbl_val.setObjectName("card_value")
        layout.addWidget(lbl_val)

        frame.value_label = lbl_val
        return frame

    def load_data(self):
        period_idx = self.combo_period.currentIndex()
        target_date = None
        if period_idx == 0:  # Today
            target_date = date.today().strftime("%Y-%m-%d")
        elif period_idx == 1:  # Yesterday
            target_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            summary = DataRepository.get_application_usage_summary(date_str=target_date)
            self._display_summary(summary)

            recent = DataRepository.get_recent_activity(limit=100)
            self._display_recent(recent)
        except Exception as e:
            logger.error(f"Error loading TrackMe data: {e}")

    def _display_summary(self, summary):
        self.summary_table.blockSignals(True)
        self.summary_table.setUpdatesEnabled(False)
        try:
            self.summary_table.setRowCount(len(summary))
            total_secs = 0
            top_app = "None"

            if summary:
                top_app = summary[0]["application"]

            for row, s in enumerate(summary):
                secs = s["total_seconds"]
                total_secs += secs

                hrs = secs // 3600
                mins = (secs % 3600) // 60
                time_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m {secs % 60}s"

                app_item = QTableWidgetItem(s["application"])
                time_item = QTableWidgetItem(time_str)
                samples_item = QTableWidgetItem(str(s["sample_count"]))

                for item in (app_item, time_item, samples_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.summary_table.setItem(row, 0, app_item)
                self.summary_table.setItem(row, 1, time_item)
                self.summary_table.setItem(row, 2, samples_item)

            hrs_tot = total_secs // 3600
            mins_tot = (total_secs % 3600) // 60
            self.card_total_time.value_label.setText(f"{hrs_tot}h {mins_tot}m")
            self.card_top_app.value_label.setText(top_app)
            self.card_entries.value_label.setText(str(len(summary)))
        finally:
            self.summary_table.setUpdatesEnabled(True)
            self.summary_table.blockSignals(False)

    def _display_recent(self, recent):
        self.recent_table.blockSignals(True)
        self.recent_table.setUpdatesEnabled(False)
        try:
            self.recent_table.setRowCount(len(recent))
            for row, r in enumerate(recent):
                time_str = (r.DateTime or "")[-8:]  # HH:MM:SS
                time_item = QTableWidgetItem(time_str)
                app_item = QTableWidgetItem(r.Application or "")
                title_item = QTableWidgetItem(r.WindowTitle or "")

                for item in (time_item, app_item, title_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.recent_table.setItem(row, 0, time_item)
                self.recent_table.setItem(row, 1, app_item)
                self.recent_table.setItem(row, 2, title_item)
        finally:
            self.recent_table.setUpdatesEnabled(True)
            self.recent_table.blockSignals(False)

    def _on_new_activity_logged(self, *args, **kwargs):
        # Triggered by background window tracker
        self.load_data()
