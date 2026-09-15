"""
Single Instance Manager for DigitalBrainEX AI.
Ensures only one instance of the application runs at any time.
If another instance is launched, it brings the existing instance to the foreground
and exits cleanly without duplicate background services or tray icons.
"""

import os
import sys
import json
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from src.core.logger import logger

# Unique GUID matching original C# application mutex
MUTEX_GUID = "{8F6F0AC4-B9A1-45fd-A8CF-72F04E6BDE8F}"
WIN32_MUTEX_NAME = f"Global\\DigitalBrainEX_AI_Mutex_{MUTEX_GUID}"
LOCAL_MUTEX_NAME = f"DigitalBrainEX_AI_Mutex_{MUTEX_GUID}"
IPC_SERVER_NAME = f"DigitalBrainEX_AI_IPC_{MUTEX_GUID}"


class SingleInstanceManager(QObject):
    """
    Manages application singleton lifecycle and inter-process activation messaging.
    """
    activation_requested = pyqtSignal(list)  # Emits list of command-line arguments

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = None
        self._mutex_handle = None
        self._is_primary = False

    def is_already_running(self) -> bool:
        """
        Checks if another instance is already running using OS-level mutex or IPC probe.
        Returns True if another instance is active, False if this is the primary instance.
        """
        if sys.platform == "win32":
            try:
                import ctypes
                # Try Global mutex first, fall back to local session mutex
                handle = ctypes.windll.kernel32.CreateMutexW(None, True, WIN32_MUTEX_NAME)
                last_err = ctypes.windll.kernel32.GetLastError()
                if last_err == 183:  # ERROR_ALREADY_EXISTS
                    # An instance is already running
                    if handle:
                        ctypes.windll.kernel32.CloseHandle(handle)
                    return True
                elif not handle:
                    # Retry with local session namespace if Global was denied
                    handle = ctypes.windll.kernel32.CreateMutexW(None, True, LOCAL_MUTEX_NAME)
                    last_err = ctypes.windll.kernel32.GetLastError()
                    if last_err == 183:
                        if handle:
                            ctypes.windll.kernel32.CloseHandle(handle)
                        return True

                self._mutex_handle = handle
                self._is_primary = True
                return False
            except Exception as e:
                logger.warning(f"Windows mutex check encountered error: {e}")

        # Fallback / cross-platform IPC socket probe
        probe_socket = QLocalSocket()
        probe_socket.connectToServer(IPC_SERVER_NAME)
        connected = probe_socket.waitForConnected(300)
        if connected:
            probe_socket.disconnectFromServer()
            return True

        self._is_primary = True
        return False

    def notify_running_instance(self, args: list = None) -> bool:
        """
        Sends an activation message to the primary instance over local IPC socket.
        """
        if args is None:
            args = sys.argv[1:]

        try:
            socket = QLocalSocket()
            socket.connectToServer(IPC_SERVER_NAME)
            if socket.waitForConnected(1000):
                payload = json.dumps({"action": "ACTIVATE", "args": args}).encode("utf-8")
                socket.write(payload)
                socket.flush()
                socket.waitForBytesWritten(1000)
                socket.disconnectFromServer()
                socket.waitForDisconnected(500)
                logger.info("Sent activation request to running instance.")
                return True
            else:
                logger.warning("Could not connect to running instance IPC socket.")
        except Exception as e:
            logger.error(f"Failed to notify running instance: {e}")

        # On Windows, try to find and bring existing window to front directly via Win32 API
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32

                def enum_windows_proc(hwnd, lParam):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            title = buff.value
                            if "DigitalBrain" in title or "Digital Brain" in title:
                                # Found running window
                                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                                user32.SetForegroundWindow(hwnd)
                                return False  # Stop enumerating
                    return True

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
                return True
            except Exception as e:
                logger.debug(f"Direct window focus fallback error: {e}")

        return False

    def start_server(self, on_activate_callback=None) -> bool:
        """
        Starts the QLocalServer to listen for activation messages from future instances.
        """
        if on_activate_callback:
            self.activation_requested.connect(on_activate_callback)

        # Clean up any abandoned socket from a prior unclean termination
        QLocalServer.removeServer(IPC_SERVER_NAME)

        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle_client_connection)

        started = self._server.listen(IPC_SERVER_NAME)
        if started:
            logger.info(f"Singleton IPC server listening on: {IPC_SERVER_NAME}")
        else:
            logger.warning(f"Could not start Singleton IPC server: {self._server.errorString()}")
        return started

    def _handle_client_connection(self):
        """Reads incoming message from secondary instance and triggers activation."""
        if not self._server:
            return

        client_socket = self._server.nextPendingConnection()
        if not client_socket:
            return

        buffer = [b""]
        has_handled = [False]

        def handle_message():
            if has_handled[0]:
                return
            data = client_socket.readAll().data()
            if data:
                buffer[0] += data

            if buffer[0]:
                try:
                    payload = json.loads(buffer[0].decode("utf-8"))
                    args = payload.get("args", [])
                    has_handled[0] = True
                    logger.info(f"Received activation message from another instance (args: {args})")
                    self.activation_requested.emit(args)
                    return
                except Exception:
                    pass

            if client_socket.state() == QLocalSocket.LocalSocketState.UnconnectedState:
                has_handled[0] = True
                self.activation_requested.emit([])

        client_socket.readyRead.connect(handle_message)
        client_socket.disconnected.connect(handle_message)
        if client_socket.bytesAvailable() > 0:
            handle_message()

    def cleanup(self):
        """Releases the mutex and closes the IPC server."""
        if self._server:
            try:
                self._server.close()
                QLocalServer.removeServer(IPC_SERVER_NAME)
            except Exception:
                pass
            self._server = None

        if sys.platform == "win32" and self._mutex_handle:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass
            self._mutex_handle = None
