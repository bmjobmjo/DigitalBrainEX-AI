"""
Helper for creating Windows shell shortcuts (.lnk files).
Uses Windows Script Host via PowerShell.
"""
import subprocess
import os
from typing import Optional


def create_shortcut(
    target_lnk: str,
    target_exe: str,
    arguments: str = "",
    working_dir: Optional[str] = None,
    icon_path: Optional[str] = None,
    description: str = "DigitalBrainEX AI",
) -> bool:
    """Creates a Windows .lnk shortcut."""
    try:
        os.makedirs(os.path.dirname(target_lnk), exist_ok=True)
        work_dir = working_dir or os.path.dirname(target_exe)
        icon = icon_path or target_exe

        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{target_lnk}'); "
            f"$s.TargetPath = '{target_exe}'; "
            f"$s.Arguments = '{arguments}'; "
            f"$s.WorkingDirectory = '{work_dir}'; "
            f"$s.IconLocation = '{icon},0'; "
            f"$s.Description = '{description}'; "
            f"$s.Save()"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return res.returncode == 0 and os.path.exists(target_lnk)
    except Exception as e:
        print(f"Error creating shortcut {target_lnk}: {e}")
        return False
