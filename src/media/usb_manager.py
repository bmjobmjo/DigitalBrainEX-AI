"""
USB & Serial Hardware Communication Manager for DigitalBrainEX AI.
Provides discovery and communication for USB peripherals and COM ports.
"""
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from src.core.logger import logger

try:
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class USBManager(QObject):
    device_discovered = pyqtSignal(str, str)  # (port, description)

    @staticmethod
    def list_serial_ports() -> List[Dict[str, str]]:
        """Enumerates connected serial and USB-to-UART bridge devices."""
        if not SERIAL_AVAILABLE:
            return []

        devices = []
        try:
            ports = serial.tools.list_ports.comports()
            for p in ports:
                devices.append({
                    "port": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                })
        except Exception as e:
            logger.error(f"Error enumerating serial ports: {e}")

        return devices
