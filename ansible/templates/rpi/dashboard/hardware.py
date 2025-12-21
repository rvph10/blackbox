import sys
import logging

logger = logging.getLogger("Dashboard.Hardware")

HAS_HARDWARE_DEPS = False
GPIO = None

try:
    import RPi.GPIO as _GPIO
    import psutil
    import evdev
    from select import select
    HAS_HARDWARE_DEPS = True
    GPIO = _GPIO
except ImportError as e:
    logger.warning(f"Hardware dependencies missing: {e}. Running in simulation/limited mode.")
    HAS_HARDWARE_DEPS = False
    
    # Mock GPIO for development/testing off-device
    if 'RPi.GPIO' not in sys.modules:
        from unittest.mock import MagicMock
        GPIO = MagicMock()
        # Mock constants
        GPIO.BCM = 11
        GPIO.OUT = 0
        GPIO.IN = 1
        GPIO.HIGH = 1
        GPIO.LOW = 0
        GPIO.PUD_UP = 22

# Re-export these for consumers
__all__ = ['GPIO', 'HAS_HARDWARE_DEPS', 'psutil', 'evdev', 'select']

