"""
DigitalBrainEX AI - Windows Setup & Installation Application.
Provides a modern, intuitive setup wizard to install DigitalBrainEX AI, configure
desktop & Start Menu shortcuts, and register automatic startup on Windows login.
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Ensure package root is in python search path
pkg_root = Path(__file__).resolve().parent.parent.parent
if str(pkg_root) not in sys.path:
    sys.path.insert(0, str(pkg_root))

from PyQt6.QtWidgets import (
    QApplication,
    QWizard,
    QWizardPage,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont

from src.installer.shortcut_helper import create_shortcut
from src.utils.startup_manager import set_auto_startup, APP_REG_NAME


def get_default_install_dir() -> str:
    """Returns the default user installation path (%LOCALAPPDATA%\\DigitalBrainEX)."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(local_app_data, "DigitalBrainEX")


def find_system_pythonw() -> tuple[str, str]:
    """
    Locates python.exe and pythonw.exe on the system.
    Returns (python_exe, pythonw_exe).
    """
    python_exe = None
    pythonw_exe = None

    # 1. If not running frozen, current sys.executable is python
    if not getattr(sys, "frozen", False):
        python_exe = sys.executable
        py_dir = os.path.dirname(python_exe)
        pw = os.path.join(py_dir, "pythonw.exe")
        if os.path.exists(pw):
            pythonw_exe = pw

    # 2. Check PATH
    if not pythonw_exe:
        which_pw = shutil.which("pythonw")
        if which_pw and os.path.exists(which_pw):
            pythonw_exe = which_pw
    if not python_exe:
        which_py = shutil.which("python")
        if which_py and os.path.exists(which_py):
            python_exe = which_py

    # 3. Check Windows Registry
    if sys.platform == "win32" and (not pythonw_exe or not python_exe):
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r"Software\Python\PythonCore") as core_key:
                    subkeys_count, _, _ = winreg.QueryInfoKey(core_key)
                    for i in range(subkeys_count):
                        ver_name = winreg.EnumKey(core_key, i)
                        try:
                            with winreg.OpenKey(core_key, rf"{ver_name}\InstallPath") as ip_key:
                                inst_path, _ = winreg.QueryValueEx(ip_key, "ExecutablePath")
                                if inst_path and os.path.exists(inst_path):
                                    if not python_exe:
                                        python_exe = inst_path
                                    pw_cand = os.path.join(os.path.dirname(inst_path), "pythonw.exe")
                                    if os.path.exists(pw_cand) and not pythonw_exe:
                                        pythonw_exe = pw_cand
                                    break
                        except Exception:
                            continue
            except Exception:
                pass

    # 4. Check known Windows default locations
    if not pythonw_exe or not python_exe:
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app, "Programs", "Python", "Python313"),
            os.path.join(local_app, "Programs", "Python", "Python312"),
            os.path.join(local_app, "Programs", "Python", "Python311"),
            r"C:\Python313",
            r"C:\Python312",
            r"C:\Python311",
        ]
        for cand in candidates:
            cand_py = os.path.join(cand, "python.exe")
            cand_pw = os.path.join(cand, "pythonw.exe")
            if os.path.exists(cand_py) and not python_exe:
                python_exe = cand_py
            if os.path.exists(cand_pw) and not pythonw_exe:
                pythonw_exe = cand_pw

    # Fallbacks
    if not python_exe:
        python_exe = sys.executable
    if not pythonw_exe:
        pythonw_exe = python_exe

    return python_exe, pythonw_exe


class InstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    finished_success = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(
        self,
        source_dir: str,
        dest_dir: str,
        doc_folder: str,
        auto_startup: bool,
        desktop_shortcut: bool,
        start_menu_shortcut: bool,
    ):
        super().__init__()
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.doc_folder = doc_folder
        self.auto_startup = auto_startup
        self.desktop_shortcut = desktop_shortcut
        self.start_menu_shortcut = start_menu_shortcut

    def run(self):
        try:
            self.progress_changed.emit(5, "Preparing target installation directory...")
            os.makedirs(self.dest_dir, exist_ok=True)

            # Configure Document & Media storage folder (DocFolder)
            self.progress_changed.emit(10, "Configuring Document & Media storage folder...")
            if self.doc_folder:
                from src.utils.config_manager import set_doc_folder
                set_doc_folder(self.doc_folder)
                os.makedirs(os.path.join(self.doc_folder, "Minutes"), exist_ok=True)

            # 1. Check if standalone DigitalBrainEX.exe binary exists
            app_exe_src = None
            candidates = [
                os.path.join(self.source_dir, "DigitalBrainEX.exe"),
                os.path.join(self.source_dir, "dist", "DigitalBrainEX.exe"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dist", "DigitalBrainEX.exe")),
            ]
            for c in candidates:
                if os.path.exists(c):
                    app_exe_src = os.path.abspath(c)
                    break

            if app_exe_src:
                self.progress_changed.emit(20, "Installing standalone DigitalBrainEX.exe binary...")
                app_exe_dst = os.path.join(self.dest_dir, "DigitalBrainEX.exe")
                shutil.copy2(app_exe_src, app_exe_dst)

                # Clean up any previously copied source code directory to ensure a clean binary-only installation
                old_src = os.path.join(self.dest_dir, "src")
                if os.path.exists(old_src):
                    try:
                        shutil.rmtree(old_src)
                    except Exception:
                        pass

                # Clean up any loose .py files in destination
                for f in os.listdir(self.dest_dir):
                    if f.endswith(".py") or f.endswith(".pyc"):
                        try:
                            os.remove(os.path.join(self.dest_dir, f))
                        except Exception:
                            pass

                # Copy database if not already exists (preserve user data)
                dst_db_dir = os.path.join(self.dest_dir, "database")
                src_db_dir = os.path.join(self.source_dir, "database")
                os.makedirs(dst_db_dir, exist_ok=True)
                if os.path.exists(src_db_dir):
                    self.progress_changed.emit(50, "Configuring database storage...")
                    for f in os.listdir(src_db_dir):
                        src_file = os.path.join(src_db_dir, f)
                        dst_file = os.path.join(dst_db_dir, f)
                        if not os.path.exists(dst_file) and os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)

                # Create default runtime directories
                for sub in ["logs", "screenshots", "recordings", "temp_pad"]:
                    os.makedirs(os.path.join(self.dest_dir, sub), exist_ok=True)

                self.progress_changed.emit(70, "Generating launchers and scripts...")
                # Write run_app.bat
                bat_path = os.path.join(self.dest_dir, "run_app.bat")
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(f'@echo off\ncd /d "{self.dest_dir}"\nstart "" "DigitalBrainEX.exe" %*\n')

                # Write uninstaller script
                uninstall_bat = os.path.join(self.dest_dir, "uninstall.bat")
                with open(uninstall_bat, "w", encoding="utf-8") as uf:
                    uf.write(
                        f'@echo off\n'
                        f'echo Uninstalling DigitalBrainEX AI...\n'
                        f'taskkill /F /IM DigitalBrainEX.exe >nul 2>&1\n'
                        f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "{APP_REG_NAME}" /f >nul 2>&1\n'
                        f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DigitalBrainEX" /f >nul 2>&1\n'
                        f'del "%USERPROFILE%\\Desktop\\DigitalBrainEX AI.lnk" >nul 2>&1\n'
                        f'del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DigitalBrainEX AI.lnk" >nul 2>&1\n'
                        f'echo DigitalBrainEX binary and database remain in {self.dest_dir}.\n'
                        f'echo Uninstallation completed successfully!\n'
                        f'pause\n'
                    )

                self._register_in_add_remove(app_exe_dst, app_exe_dst, uninstall_bat)

                self.progress_changed.emit(85, "Creating Windows shortcuts...")
                # Desktop Shortcut
                if self.desktop_shortcut:
                    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                    desktop_lnk = os.path.join(desktop_dir, "DigitalBrainEX AI.lnk")
                    create_shortcut(
                        target_lnk=desktop_lnk,
                        target_exe=app_exe_dst,
                        arguments="",
                        working_dir=self.dest_dir,
                        icon_path=app_exe_dst,
                        description="DigitalBrainEX AI - Intelligent Task Companion & Diary",
                    )

                # Start Menu Shortcut
                if self.start_menu_shortcut:
                    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
                    start_menu_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                    start_menu_lnk = os.path.join(start_menu_dir, "DigitalBrainEX AI.lnk")
                    create_shortcut(
                        target_lnk=start_menu_lnk,
                        target_exe=app_exe_dst,
                        arguments="",
                        working_dir=self.dest_dir,
                        icon_path=app_exe_dst,
                        description="DigitalBrainEX AI - Intelligent Task Companion & Diary",
                    )

                # Auto-Startup
                self.progress_changed.emit(95, "Configuring Windows Auto-Startup...")
                startup_cmd = f'"{app_exe_dst}" --minimized'
                set_auto_startup(self.auto_startup, command=startup_cmd)

                self.progress_changed.emit(100, "Installation complete!")
                self.finished_success.emit()
                return

            # Fallback if binary is not compiled yet (e.g. running directly from repo in dev mode)
            folders_to_copy = ["src"]
            if os.path.exists(os.path.join(self.source_dir, "assets")):
                folders_to_copy.append("assets")

            current = 15
            for folder in folders_to_copy:
                src_path = os.path.join(self.source_dir, folder)
                dst_path = os.path.join(self.dest_dir, folder)
                if os.path.exists(src_path):
                    self.progress_changed.emit(current, f"Copying {folder} files...")
                    if os.path.exists(dst_path):
                        shutil.rmtree(dst_path)
                    shutil.copytree(src_path, dst_path)
                current += 25

            # Copy database if not already exists (preserve user data)
            dst_db_dir = os.path.join(self.dest_dir, "database")
            src_db_dir = os.path.join(self.source_dir, "database")
            os.makedirs(dst_db_dir, exist_ok=True)
            if os.path.exists(src_db_dir):
                self.progress_changed.emit(65, "Configuring database storage...")
                for f in os.listdir(src_db_dir):
                    src_file = os.path.join(src_db_dir, f)
                    dst_file = os.path.join(dst_db_dir, f)
                    if not os.path.exists(dst_file) and os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)

            # Create default runtime directories
            for sub in ["logs", "screenshots", "recordings", "temp_pad"]:
                os.makedirs(os.path.join(self.dest_dir, sub), exist_ok=True)

            self.progress_changed.emit(75, "Generating launchers and scripts...")

            # Copy requirements.txt
            req_src = os.path.join(self.source_dir, "requirements.txt")
            if os.path.exists(req_src):
                shutil.copy2(req_src, os.path.join(self.dest_dir, "requirements.txt"))

            # Determine python & pythonw paths using robust system locator
            python_exe, pythonw_exe = find_system_pythonw()

            app_py = os.path.join(self.dest_dir, "src", "app.py")
            app_icon = os.path.join(self.dest_dir, "src", "assets", "app_icon.ico")

            # Write run_app.bat in dest_dir
            bat_path = os.path.join(self.dest_dir, "run_app.bat")
            with open(bat_path, "w", encoding="utf-8") as bf:
                bf.write(f'@echo off\ncd /d "{self.dest_dir}"\nstart "" "{pythonw_exe}" "{app_py}" %*\n')

            # Write run_app_debug.bat in dest_dir
            bat_debug_path = os.path.join(self.dest_dir, "run_app_debug.bat")
            with open(bat_debug_path, "w", encoding="utf-8") as bdf:
                bdf.write(f'@echo off\ncd /d "{self.dest_dir}"\n"{python_exe}" "{app_py}" %*\npause\n')

            # Write uninstaller script
            uninstall_bat = os.path.join(self.dest_dir, "uninstall.bat")
            with open(uninstall_bat, "w", encoding="utf-8") as uf:
                uf.write(
                    f'@echo off\n'
                    f'echo Uninstalling DigitalBrainEX AI...\n'
                    f'powershell -Command "Stop-Process -Name python, pythonw -ErrorAction SilentlyContinue"\n'
                    f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "{APP_REG_NAME}" /f >nul 2>&1\n'
                    f'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DigitalBrainEX" /f >nul 2>&1\n'
                    f'del "%USERPROFILE%\\Desktop\\DigitalBrainEX AI.lnk" >nul 2>&1\n'
                    f'del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DigitalBrainEX AI.lnk" >nul 2>&1\n'
                    f'echo DigitalBrainEX AI files remain in {self.dest_dir} if you wish to delete them.\n'
                    f'echo Uninstallation completed successfully!\n'
                    f'pause\n'
                )

            # Register in Windows Add/Remove Programs
            self._register_in_add_remove(pythonw_exe, app_icon, uninstall_bat)

            self.progress_changed.emit(85, "Creating Windows shortcuts...")

            # 1. Desktop Shortcut
            if self.desktop_shortcut:
                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                desktop_lnk = os.path.join(desktop_dir, "DigitalBrainEX AI.lnk")
                create_shortcut(
                    target_lnk=desktop_lnk,
                    target_exe=pythonw_exe,
                    arguments=f'"{app_py}"',
                    working_dir=self.dest_dir,
                    icon_path=app_icon,
                    description="DigitalBrainEX AI - Intelligent Task Companion & Diary",
                )

            # 2. Start Menu Shortcut
            if self.start_menu_shortcut:
                appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
                start_menu_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                start_menu_lnk = os.path.join(start_menu_dir, "DigitalBrainEX AI.lnk")
                create_shortcut(
                    target_lnk=start_menu_lnk,
                    target_exe=pythonw_exe,
                    arguments=f'"{app_py}"',
                    working_dir=self.dest_dir,
                    icon_path=app_icon,
                    description="DigitalBrainEX AI - Intelligent Task Companion & Diary",
                )

            # 3. Configure Windows Auto-Startup
            self.progress_changed.emit(95, "Configuring Windows Auto-Startup...")
            startup_cmd = f'"{pythonw_exe}" "{app_py}" --minimized'
            set_auto_startup(self.auto_startup, command=startup_cmd)

            self.progress_changed.emit(100, "Installation complete!")
            self.finished_success.emit()

        except Exception as e:
            self.finished_error.emit(str(e))

    def _register_in_add_remove(self, pythonw_exe: str, icon_path: str, uninstall_bat: str):
        """Registers DigitalBrainEX in Windows Add/Remove Programs registry."""
        if sys.platform != "win32":
            return
        import winreg
        uninstall_key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\DigitalBrainEX"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, uninstall_key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "DigitalBrainEX AI")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "2.0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "DigitalBrain")
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_path)
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, self.dest_dir)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'cmd.exe /c "{uninstall_bat}"')
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        except Exception as e:
            print(f"Could not register in Add/Remove programs: {e}")


class WelcomePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Welcome to DigitalBrainEX AI Setup")
        self.setSubTitle("This wizard will guide you through the installation of DigitalBrainEX AI.")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        lbl_desc = QLabel(
            "DigitalBrainEX AI is an intelligent companion for task management, "
            "developer diary tracking, screen capture, and productivity analytics.\n\n"
            "This setup program will:\n"
            "  • Install DigitalBrainEX application files\n"
            "  • Configure the authentic desktop & tray icons\n"
            "  • Set up Windows shortcuts and auto-startup on login\n\n"
            "Click Next to continue."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 13px; line-height: 1.5; color: #1e293b;")
        layout.addWidget(lbl_desc)
        layout.addStretch()


class DirectoryPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Select Destination Location")
        self.setSubTitle("Where should DigitalBrainEX AI be installed?")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("Setup will install DigitalBrainEX AI into the following folder:")
        layout.addWidget(lbl)

        path_layout = QHBoxLayout()
        self.edit_path = QLineEdit(get_default_install_dir())
        path_layout.addWidget(self.edit_path)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)

        lbl_info = QLabel("At least 60 MB of free disk space is required.")
        lbl_info.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(lbl_info)
        layout.addStretch()

        self.registerField("install_dir*", self.edit_path)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.edit_path.text())
        if folder:
            self.edit_path.setText(folder)


class StorageDirectoryPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Document & Media Storage Location (DocFolder)")
        self.setSubTitle("Where should project documents, attachments, and meeting audio be stored?")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel(
            "Select the root storage folder for all project documents and files.\n"
            "Relative document paths in your database (e.g. \\3\\filename.pdf) "
            "will be resolved directly inside this folder:"
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 12px; color: #1e293b;")
        layout.addWidget(lbl)

        path_layout = QHBoxLayout()
        from src.utils.config_manager import get_doc_folder
        self.edit_doc_folder = QLineEdit(get_doc_folder())
        path_layout.addWidget(self.edit_doc_folder)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)

        lbl_info = QLabel("Tip: You can change this path later anytime in Settings -> Paths & Storage.")
        lbl_info.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(lbl_info)
        layout.addStretch()

        self.registerField("doc_folder*", self.edit_doc_folder)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Document Storage Folder", self.edit_doc_folder.text())
        if folder:
            self.edit_doc_folder.setText(folder)


class OptionsPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Select Additional Tasks")
        self.setSubTitle("Which additional integration options should be performed?")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        self.chk_startup = QCheckBox("Start DigitalBrainEX AI automatically when Windows starts (Recommended)")
        self.chk_startup.setChecked(True)
        layout.addWidget(self.chk_startup)

        self.chk_desktop = QCheckBox("Create a Desktop shortcut")
        self.chk_desktop.setChecked(True)
        layout.addWidget(self.chk_desktop)

        self.chk_start_menu = QCheckBox("Create a Start Menu shortcut")
        self.chk_start_menu.setChecked(True)
        layout.addWidget(self.chk_start_menu)

        layout.addStretch()

        self.registerField("auto_startup", self.chk_startup)
        self.registerField("desktop_shortcut", self.chk_desktop)
        self.registerField("start_menu_shortcut", self.chk_start_menu)


class ProgressPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Installing DigitalBrainEX AI")
        self.setSubTitle("Please wait while setup installs files on your computer.")

        self._installed = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.lbl_status = QLabel("Ready to install...")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

    def initializePage(self):
        super().initializePage()
        if self._installed:
            return

        if getattr(sys, "frozen", False):
            source_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        else:
            source_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        dest_dir = self.field("install_dir")
        doc_folder = self.field("doc_folder")
        auto_startup = self.field("auto_startup")
        desktop_sc = self.field("desktop_shortcut")
        start_menu_sc = self.field("start_menu_shortcut")

        self.wizard().button(QWizard.WizardButton.BackButton).setEnabled(False)
        self.wizard().button(QWizard.WizardButton.NextButton).setEnabled(False)

        self.worker = InstallWorker(
            source_dir=source_dir,
            dest_dir=dest_dir,
            doc_folder=doc_folder,
            auto_startup=auto_startup,
            desktop_shortcut=desktop_sc,
            start_menu_shortcut=start_menu_sc,
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.finished_success.connect(self._on_success)
        self.worker.finished_error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, percent: int, text: str):
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(text)

    def _on_success(self):
        self._installed = True
        self.wizard().button(QWizard.WizardButton.NextButton).setEnabled(True)
        self.wizard().next()

    def _on_error(self, err_msg: str):
        self.lbl_status.setText(f"Installation failed: {err_msg}")
        QMessageBox.critical(self, "Installation Error", f"An error occurred during installation:\n{err_msg}")
        self.wizard().button(QWizard.WizardButton.BackButton).setEnabled(True)

    def isComplete(self) -> bool:
        return self._installed


class FinishedPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Installation Complete")
        self.setSubTitle("DigitalBrainEX AI has been successfully installed.")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        lbl = QLabel(
            "DigitalBrainEX AI is now installed on your system.\n\n"
            "You can access it anytime from your Desktop, Start Menu, or the System Tray."
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px; color: #1e293b;")
        layout.addWidget(lbl)

        self.chk_launch = QCheckBox("Launch DigitalBrainEX AI now")
        self.chk_launch.setChecked(True)
        layout.addWidget(self.chk_launch)

        layout.addStretch()

    def validatePage(self) -> bool:
        if self.chk_launch.isChecked():
            dest_dir = self.field("install_dir")
            app_exe = os.path.join(dest_dir, "DigitalBrainEX.exe")
            if os.path.exists(app_exe):
                subprocess.Popen([app_exe], cwd=dest_dir)
            else:
                bat_path = os.path.join(dest_dir, "run_app.bat")
                if os.path.exists(bat_path):
                    subprocess.Popen(["cmd.exe", "/c", bat_path], shell=True)
        return True


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DigitalBrainEX AI Setup")
        self.resize(580, 420)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        # Apply icon
        self._icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "app_icon.ico"))
        if os.path.exists(self._icon_path):
            self.setWindowIcon(QIcon(self._icon_path))

        self.addPage(WelcomePage(self))
        self.addPage(DirectoryPage(self))
        self.addPage(StorageDirectoryPage(self))
        self.addPage(OptionsPage(self))
        self.addPage(ProgressPage(self))
        self.addPage(FinishedPage(self))

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_icon_path") and os.path.exists(self._icon_path):
            from src.utils.win32_helper import apply_native_window_icon
            apply_native_window_icon(int(self.winId()), self._icon_path)


def run_direct_install(install_dir: Optional[str] = None, doc_folder: Optional[str] = None, auto_startup: bool = True) -> bool:
    """Executes installation directly and synchronously."""
    from src.utils.config_manager import get_doc_folder
    if getattr(sys, "frozen", False):
        source_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        source_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    target_dest = install_dir or get_default_install_dir()
    target_doc = doc_folder or get_doc_folder()

    print(f"Installing DigitalBrainEX AI:")
    print(f"  Source:       {source_dir}")
    print(f"  Destination:  {target_dest}")
    print(f"  DocFolder:    {target_doc}")
    print(f"  Auto-Startup: {auto_startup}")

    worker = InstallWorker(
        source_dir=source_dir,
        dest_dir=target_dest,
        doc_folder=target_doc,
        auto_startup=auto_startup,
        desktop_shortcut=True,
        start_menu_shortcut=True,
    )
    success = [False]
    worker.progress_changed.connect(lambda p, m: print(f"  [{p}%] {m}"))
    worker.finished_success.connect(lambda: success.__setitem__(0, True))
    worker.finished_error.connect(lambda err: print(f"  [ERROR] {err}"))
    worker.run()
    return success[0]


def main():
    if "--silent" in sys.argv or "--install" in sys.argv:
        app = QApplication.instance() or QApplication(sys.argv)
        ok = run_direct_install()
        sys.exit(0 if ok else 1)

    from src.utils.win32_helper import setup_windows_app_id
    setup_windows_app_id()
    app = QApplication(sys.argv)
    wizard = SetupWizard()
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
