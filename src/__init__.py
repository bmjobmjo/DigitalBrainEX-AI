"""DigitalBrainEX AI Package."""
__version__ = "2.1.0"

# Ensure PyTorch C++ runtime DLLs are loaded before PyQt6 on Windows
try:
    import torch
except Exception:
    pass

