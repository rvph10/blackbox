#!/usr/bin/env python3
"""
Raspberry Pi Homelab Dashboard
System status display for 3.5" TFT Framebuffer.
"""

import logging
import signal
import sys
import time
import urllib3
from datetime import datetime

from config import Config
from display import DisplayDriver
from monitor import SystemMonitor
from renderer import Renderer
from input import InputController

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Dashboard")

class DashboardApp:
    def __init__(self):
        self.config = Config()
        self.display = DisplayDriver(self.config)
        self.monitor = SystemMonitor(self.config)
        self.renderer = Renderer(self.config, self.monitor)
        
        # Initial State Calculation
        now = datetime.now()
        self.last_hour = now.hour
        
        # Check if we start inside the OFF schedule window
        if self.config.SCHEDULE_OFF_HOUR <= now.hour < self.config.SCHEDULE_ON_HOUR:
            self.screen_on = False
        else:
            self.screen_on = True

        self.input = InputController(
            self.config,
            callback_power_toggle=self.toggle_screen,
            callback_next_page=self.handle_input
        )
        
        # Connect driver reload callback
        self.display.set_on_driver_reload_callback(self.input.reset_touch_device)
        
        # Shutdown handling
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        self.running = True

    def toggle_screen(self):
        self.screen_on = not self.screen_on
        logger.info(f"Screen manually toggled: {'ON' if self.screen_on else 'OFF'}")

    def handle_input(self):
        # If screen is off, user touching screen wants to see it
        if not self.screen_on:
            self.screen_on = True
            logger.info("Screen woke up by touch")
        else:
            # Trigger animated transition
            for frame in self.renderer.next_page():
                if self.screen_on:  # Only draw if screen is still on
                    self.display.draw(frame)
                    time.sleep(1.0 / self.config.ANIMATION_FPS)

    def run(self):
        logger.info("Starting Dashboard...")
        self.monitor.start()
        self.input.start()
        
        # Give drivers time to initialize before first power cycle
        logger.info("Waiting for drivers to initialize...")
        time.sleep(2.0)
        
        # Now enforce initial state (this may trigger driver reload)
        self.display.set_power(self.screen_on)

        try:
            while self.running:
                now = datetime.now()
                current_hour = now.hour
                
                # Check for critical alerts
                services = self.monitor.get_state('services')
                failed = [k for k,v in services.items() if not v]
                
                # --- State Machine Logic ---
                
                # 1. Schedule Transitions
                # Only change state if we cross the hour boundary
                if current_hour != self.last_hour:
                    if current_hour == self.config.SCHEDULE_OFF_HOUR:
                        self.screen_on = False
                        logger.info("Schedule: Entering night mode (OFF)")
                    elif current_hour == self.config.SCHEDULE_ON_HOUR:
                        self.screen_on = True
                        logger.info("Schedule: Entering day mode (ON)")
                    self.last_hour = current_hour
                
                # 2. Alert Override
                # If an alert occurs and screen is OFF, wake it up
                if failed and not self.screen_on:
                    self.screen_on = True
                    logger.info("Alert detected! Waking screen.")
                    
                # 3. Apply State
                if self.screen_on:
                    # If we just woke up, ensure power is ON
                    self.display.set_power(True)
                    
                    if failed:
                         img = self.renderer.render_alert(failed)
                    else:
                         img = self.renderer.render()
                    
                    self.display.draw(img)
                    time.sleep(0.5) 
                else:
                    self.display.set_power(False)
                    time.sleep(1.0)

        except KeyboardInterrupt:
            self._shutdown()

    def _shutdown(self, signum=None, frame=None):
        logger.info("Shutting down...")
        self.running = False
        self.monitor.stop()
        self.input.stop()
        self.display.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    app = DashboardApp()
    app.run()