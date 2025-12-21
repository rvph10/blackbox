import threading
import time
import logging
from hardware import GPIO, evdev, select, HAS_HARDWARE_DEPS

logger = logging.getLogger("Dashboard.Input")

class InputController:
    """Manages physical button and touchscreen input events."""
    
    def __init__(self, config, callback_power_toggle, callback_next_page):
        self.config = config
        self.cb_power = callback_power_toggle
        self.cb_next = callback_next_page
        self.running = True
        self._touch_dev = None
        self._touch_lock = threading.Lock()
        self._driver_reload_in_progress = False
        
    def start(self):
        # Physical Button
        if HAS_HARDWARE_DEPS and GPIO:
            try:
                GPIO.setup(self.config.PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception as e:
                logger.error(f"GPIO Setup failed: {e}")
        
        threading.Thread(target=self._loop_inputs, daemon=True).start()

    def stop(self):
        self.running = False
        self._close_touch_device()

    def reset_touch_device(self):
        """Called by display driver after reloading drivers."""
        logger.info("Resetting touch device after driver reload...")
        with self._touch_lock:
            self._close_touch_device()
            # The main loop will re-acquire the device

    def _close_touch_device(self):
        """Properly close the touch device if open."""
        if self._touch_dev is not None:
            try:
                self._touch_dev.close()
                logger.info("Touch device closed")
            except Exception as e:
                logger.warning(f"Error closing touch device: {e}")
            finally:
                self._touch_dev = None

    def _loop_inputs(self):
        btn_prev = False
        
        while self.running:
            # 1. GPIO Button
            if HAS_HARDWARE_DEPS and GPIO:
                try:
                    btn_state = GPIO.input(self.config.PIN_BUTTON) == GPIO.LOW
                    if btn_state and not btn_prev:
                        self.cb_power()
                        time.sleep(0.3) # Debounce
                    btn_prev = btn_state
                except Exception:
                    pass

            # 2. Touchscreen Discovery & Event Handling
            with self._touch_lock:
                if self._touch_dev is None and HAS_HARDWARE_DEPS and evdev:
                    self._touch_dev = self._get_touch_device()
                    if self._touch_dev:
                        logger.info(f"Touch input device acquired: {self._touch_dev.name}")

                if self._touch_dev:
                    try:
                        r, _, _ = select([self._touch_dev.fd], [], [], 0.0)
                        if r:
                            for event in self._touch_dev.read():
                                # Debug: log all events
                                logger.debug(f"Touch event: type={event.type}, code={event.code}, value={event.value}")
                                if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                                    logger.info("Touch detected! Triggering callback.")
                                    self.cb_next()
                    except (OSError, IOError) as e:
                        # Device lost (e.g. driver reload), reset to force re-scan
                        logger.warning(f"Touch device lost connection: {e}. Rescanning...")
                        self._close_touch_device()
            
            time.sleep(0.05)

    def _get_touch_device(self):
        if not HAS_HARDWARE_DEPS or not evdev: 
            return None
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            logger.debug(f"Scanning {len(devices)} input devices...")
            for d in devices:
                logger.debug(f"Found device: {d.name} at {d.path}")
                if 'touch' in d.name.lower() or 'ads7846' in d.name.lower():
                    logger.info(f"Found touch device: {d.name} at {d.path}")
                    return d
            logger.warning("No touch device found in this scan")
        except Exception as e:
            logger.error(f"Error scanning for touch device: {e}")
        return None