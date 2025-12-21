import os
import time
import subprocess
import struct
import logging
from PIL import Image
from hardware import GPIO

logger = logging.getLogger("Dashboard.Display")

class DisplayDriver:
    """Handles low-level framebuffer and backlight control."""
    
    def __init__(self, config):
        self.config = config
        self.device = config.FB_DEVICE
        self.is_powered = False
        # Callback to notify input controller when drivers are reloaded
        # IMPORTANT: Initialize BEFORE _init_gpio() which may call _reload_driver()
        self.on_driver_reload_callback = None
        self._init_gpio()

    def _init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.config.PIN_SCREEN_POWER, GPIO.OUT)
        GPIO.setup(self.config.PIN_BACKLIGHT, GPIO.OUT)
        # Start with display OFF to ensure proper initialization on first set_power(True)
        GPIO.output(self.config.PIN_SCREEN_POWER, GPIO.LOW)
        GPIO.output(self.config.PIN_BACKLIGHT, GPIO.LOW)
        self.is_powered = False

    def set_on_driver_reload_callback(self, callback):
        """Set callback to notify when drivers are reloaded."""
        self.on_driver_reload_callback = callback

    def set_power(self, on: bool):
        """Toggle screen power and handle driver re-initialization if needed."""
        # Only act if state actually changes
        if on and not self.is_powered:
            logger.info("Powering ON display...")
            GPIO.output(self.config.PIN_SCREEN_POWER, GPIO.HIGH)
            GPIO.output(self.config.PIN_BACKLIGHT, GPIO.HIGH)
            self._reload_driver()
            self.is_powered = True
        elif not on and self.is_powered:
            logger.info("Powering OFF display...")
            GPIO.output(self.config.PIN_SCREEN_POWER, GPIO.LOW)
            GPIO.output(self.config.PIN_BACKLIGHT, GPIO.LOW)
            self.is_powered = False

    def _reload_driver(self):
        """Reloads both display and touch drivers to ensure correct initialization after power cycle."""
        try:
            logger.info("Reloading display and touch drivers...")
            time.sleep(0.5)
            
            # Remove both drivers (order matters - remove display first)
            subprocess.run(["/usr/sbin/modprobe", "-r", "fb_ili9486"], check=False)
            time.sleep(0.2)
            subprocess.run(["/usr/sbin/modprobe", "-r", "ads7846"], check=False)
            time.sleep(0.3)
            
            # Reload both drivers (order matters - load display first, then touch)
            subprocess.run(["/usr/sbin/modprobe", "fb_ili9486"], check=False)
            time.sleep(0.5)
            subprocess.run(["/usr/sbin/modprobe", "ads7846"], check=False)
            time.sleep(1.0)  # Give touch driver time to initialize
            
            logger.info("Drivers reloaded successfully")
            
            # Notify input controller to reset touch device
            if self.on_driver_reload_callback:
                self.on_driver_reload_callback()
                
        except Exception as e:
            logger.error(f"Failed to reload display driver: {e}")

    def draw(self, image: Image.Image):
        """Writes PIL Image to framebuffer device."""
        if not os.path.exists(self.device):
            return

        try:
            pixels = image.getdata()
            # 16-bit RGB565 buffer
            buf = bytearray(self.config.SCREEN_WIDTH * self.config.SCREEN_HEIGHT * 2)
            
            # Pack pixels (RGB888 -> RGB565)
            # Optimization: Move bitwise ops to C or use numpy if perf becomes an issue
            for i, (r, g, b) in enumerate(pixels):
                c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                struct.pack_into("<H", buf, i * 2, c)
            
            with open(self.device, "wb") as f:
                f.write(buf)
        except IOError as e:
            logger.error(f"Framebuffer write error: {e}")

    def cleanup(self):
        GPIO.cleanup()