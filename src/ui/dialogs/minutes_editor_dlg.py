"""
Dedicated Meeting Minutes Editor Popup Dialog for DigitalBrainEX AI.
Matches original ReferenceScreenshots/12_Module_MeetingMinutes_Editor.png.
"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDateTime

from src.core.repository import DataRepository
from src.media.audio_recorder import AudioRecorder
from src.core.logger import logger


class MinutesEditorDialog(QDialog):
    def __init__(self, parent=None, minute_id: Optional[int] = None, default_project_id: int = 0):
        super().__init__(parent)
        self.minute_id = minute_id
        self.default_project_id = default_project_id
        self.saved_minute_id: Optional[int] = None

        self.recorder = AudioRecorder()
        self.recorder.recording_stopped.connect(self._on_recording_finished)

        self.setWindowTitle("Edit Meeting Minutes" if self.minute_id else "New Meeting Minutes")
        self.setMinimumSize(740, 620)
        self.resize(800, 680)
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Title
        title_text = "✏️ Edit Meeting Minutes" if self.minute_id else "🎙️ New Meeting Minutes"
        header = QLabel(title_text)
        header.setObjectName("ViewTitleLabel")
        layout.addWidget(header)

        # Subject
        layout.addWidget(QLabel("Meeting Subject / Title:"))
        self.edit_subject = QLineEdit()
        self.edit_subject.setPlaceholderText("Enter meeting subject or discussion topic...")
        layout.addWidget(self.edit_subject)

        # Metadata Row: Project + Date/Time
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(14)

        proj_col = QVBoxLayout()
        proj_col.addWidget(QLabel("Project:"))
        self.combo_proj = QComboBox()
        self._populate_projects()
        proj_col.addWidget(self.combo_proj)
        meta_layout.addLayout(proj_col, stretch=1)

        time_col = QVBoxLayout()
        time_col.addWidget(QLabel("Date & Time:"))
        self.edit_datetime = QDateTimeEdit()
        self.edit_datetime.setCalendarPopup(True)
        self.edit_datetime.setDateTime(QDateTime.currentDateTime())
        time_col.addWidget(self.edit_datetime)
        meta_layout.addLayout(time_col, stretch=1)

        layout.addLayout(meta_layout)

        # Audio Section
        audio_group = QGroupBox("Meeting Audio Recording & Transcription")
        audio_layout = QHBoxLayout(audio_group)
        audio_layout.setSpacing(10)

        self.lbl_audio_status = QLabel("No Audio File")
        self.lbl_audio_status.setStyleSheet("color: #64748b; font-weight: 500;")
        audio_layout.addWidget(self.lbl_audio_status, stretch=1)

        self.btn_record = QPushButton("🔴 Record Audio")
        self.btn_record.clicked.connect(self._toggle_recording)
        audio_layout.addWidget(self.btn_record)

        self.btn_attach = QPushButton("📁 Attach File...")
        self.btn_attach.clicked.connect(self._attach_audio_file)
        audio_layout.addWidget(self.btn_attach)

        self.btn_transcribe = QPushButton("✨ Transcribe")
        self.btn_transcribe.setObjectName("PrimaryButton")
        self.btn_transcribe.setToolTip("Transcribe audio into meeting notes using AI")
        self.btn_transcribe.clicked.connect(self._transcribe_audio)
        audio_layout.addWidget(self.btn_transcribe)

        layout.addWidget(audio_group)

        # Agenda & Notes
        layout.addWidget(QLabel("Agenda, Discussion & Decisions:"))
        self.edit_notes = QTextEdit()
        self.edit_notes.setPlaceholderText("Meeting attendees, key takeaways, action items, decisions...")
        layout.addWidget(self.edit_notes, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Save Minutes")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self._save_minutes)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _populate_projects(self):
        self.combo_proj.clear()
        self.combo_proj.addItem("General", userData=0)
        try:
            projects = DataRepository.get_all_projects()
            for p in projects:
                name = p.ProjectName.strip() if p.ProjectName else f"Project #{p.PojectID}"
                self.combo_proj.addItem(name, userData=p.PojectID)
        except Exception as e:
            logger.error(f"Error populating minutes dialog projects: {e}")

    def _toggle_recording(self):
        if not self.recorder.is_recording:
            self.recorder.start_recording()
            self.btn_record.setText("⏹️ Stop Recording")
            self.btn_record.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: bold;")
            self.lbl_audio_status.setText("● Recording in progress...")
        else:
            saved_file = self.recorder.stop_recording()
            self.btn_record.setText("🔴 Record Audio")
            self.btn_record.setStyleSheet("")

    def _on_recording_finished(self, wav_path: str):
        self.lbl_audio_status.setText(os.path.basename(wav_path))
        self.lbl_audio_status.setProperty("audio_path", wav_path)

    def _attach_audio_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Attach Meeting Audio", "", "Audio Files (*.wav *.mp3 *.m4a *.aac)"
        )
        if filepath:
            self.lbl_audio_status.setText(os.path.basename(filepath))
            self.lbl_audio_status.setProperty("audio_path", filepath)

    def _transcribe_audio(self):
        audio_path = self.lbl_audio_status.property("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            QMessageBox.warning(self, "No Audio", "Please record or attach an audio file first.")
            return

        from src.media.audio_transcriber import AudioTranscriber
        self.btn_transcribe.setEnabled(False)
        self.btn_transcribe.setText("⏳ Transcribing...")

        transcriber = AudioTranscriber()
        result = transcriber.transcribe_file(audio_path)

        self.btn_transcribe.setEnabled(True)
        self.btn_transcribe.setText("✨ Transcribe")

        if result:
            current = self.edit_notes.toPlainText()
            separator = "\n\n--- AI Audio Transcript ---\n" if current else ""
            self.edit_notes.setPlainText(current + separator + result)
            QMessageBox.information(self, "Transcription Complete", "Transcript appended to meeting notes!")
        else:
            QMessageBox.warning(self, "Transcription Error", "Unable to transcribe audio file.")

    def _load_data(self):
        if self.minute_id:
            d = DataRepository.get_document_by_id(self.minute_id)
            if d:
                self.edit_subject.setText(d.DocumentName or "")
                content = d.Desc if d.Desc else (d.Notes or "")
                self.edit_notes.setPlainText(content)
                if d.DocumentURI:
                    self.lbl_audio_status.setText(os.path.basename(d.DocumentURI))
                    self.lbl_audio_status.setProperty("audio_path", d.DocumentURI)

                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == d.PojectID:
                        self.combo_proj.setCurrentIndex(i)
                        break
        else:
            if self.default_project_id != 0:
                for i in range(self.combo_proj.count()):
                    if self.combo_proj.itemData(i) == self.default_project_id:
                        self.combo_proj.setCurrentIndex(i)
                        break

    def _save_minutes(self):
        subject = self.edit_subject.text().strip()
        if not subject:
            QMessageBox.warning(self, "Validation Error", "Please provide a Meeting Subject.")
            self.edit_subject.setFocus()
            return

        notes = self.edit_notes.toPlainText()
        proj_id = self.combo_proj.currentData() or 0
        proj_name = self.combo_proj.currentText()
        audio_path = self.lbl_audio_status.property("audio_path") or ""

        try:
            if self.minute_id:
                DataRepository.update_document(
                    self.minute_id,
                    DocumentName=subject,
                    Desc=notes,
                    Notes=notes,
                    DocumentURI=audio_path,
                    PojectID=proj_id,
                    ProjectName=proj_name,
                )
                self.saved_minute_id = self.minute_id
            else:
                new_doc = DataRepository.create_document(
                    name=subject,
                    desc=notes,
                    notes=notes,
                    uri=audio_path,
                    project_id=proj_id,
                    project_name=proj_name,
                    category="Minutes",
                    doc_type=9 if audio_path else 8,
                )
                self.saved_minute_id = new_doc.DocumentID

            self.accept()
        except Exception as e:
            logger.error(f"Error saving minutes: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save minutes:\n{e}")

    def closeEvent(self, event):
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        super().closeEvent(event)
