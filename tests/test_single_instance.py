"""
Unit tests for SingleInstanceManager.
Verifies singleton lifecycle, mutex detection, IPC messaging, and cleanup.
"""
import unittest
import sys
import os
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.single_instance import SingleInstanceManager

app = QApplication.instance() or QApplication(["test_single_instance"])


class TestSingleInstance(unittest.TestCase):

    def test_mutex_detection_and_cleanup(self):
        primary = SingleInstanceManager()
        is_running = primary.is_already_running()
        self.assertFalse(is_running, "First instance should be primary")

        secondary = SingleInstanceManager()
        is_second_running = secondary.is_already_running()
        self.assertTrue(is_second_running, "Second instance should detect primary running")

        secondary.cleanup()
        primary.cleanup()

        # After cleanup, fresh instance should be primary
        fresh = SingleInstanceManager()
        self.assertFalse(fresh.is_already_running(), "Fresh instance after cleanup should be primary")
        fresh.cleanup()
        print("Mutex detection and cleanup verified!")

    def test_ipc_multiprocess_activation(self):
        import subprocess
        import time

        # Start primary in background process
        proc = subprocess.Popen([sys.executable, '-c', '''
from PyQt6.QtWidgets import QApplication
from src.utils.single_instance import SingleInstanceManager
import sys

app = QApplication([])
mgr = SingleInstanceManager()
mgr.is_already_running()
mgr.start_server(on_activate_callback=lambda args: print("ACTIVATION_RESULT:" + str(args), flush=True))
print("PRIMARY_READY", flush=True)
sys.exit(app.exec())
'''], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            # Wait for primary to signal readiness
            ready = False
            for _ in range(50):
                line = proc.stdout.readline()
                if "PRIMARY_READY" in line:
                    ready = True
                    break
                time.sleep(0.1)
            self.assertTrue(ready, "Primary process should report readiness")

            # Run secondary in another process
            res = subprocess.run([sys.executable, '-c', '''
from PyQt6.QtWidgets import QApplication
from src.utils.single_instance import SingleInstanceManager
import sys

app = QApplication([])
mgr = SingleInstanceManager()
if mgr.is_already_running():
    mgr.notify_running_instance(args=["test_file.pdf", "--minimized"])
'''], capture_output=True, text=True)

            time.sleep(0.5)
            proc.terminate()
            out, err = proc.communicate(timeout=5)
            self.assertIn("ACTIVATION_RESULT:['test_file.pdf', '--minimized']", out)
            print("Multi-process IPC activation verified!")
        finally:
            if proc.poll() is None:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
