import threading
import time
import socket
import subprocess
import json
import os
import sys
import requests
import logging
from typing import Any

# Optional deps
try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("Dashboard.Monitor")

class SystemMonitor:
    """Background data collection service."""
    
    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        self.state = {
            'weather': None,
            'network': {'dl': 0.0, 'ul': 0.0, 'latency': None},
            'services': {},
            'backups': {},
            'system': {'cpu': 0, 'ram': 0, 'temp': 0}
        }
        
        self._network_state = {'last_rx': 0, 'last_tx': 0, 'last_check': 0}
        
    def start(self):
        threads = [
            (self._loop_weather, 900),
            (self._loop_network, 5),
            (self._loop_services, 30),
            (self._loop_system, 2)
        ]
        
        for target, interval in threads:
            t = threading.Thread(target=self._run_loop, args=(target, interval), daemon=True)
            t.start()

    def stop(self):
        self._stop_event.set()

    def get_state(self, key: str) -> Any:
        with self._lock:
            return self.state.get(key)

    def _run_loop(self, task_func, interval):
        while not self._stop_event.is_set():
            try:
                task_func()
            except Exception as e:
                logger.error(f"Error in {task_func.__name__}: {e}")
            time.sleep(interval)

    def _loop_weather(self):
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.config.LATITUDE,
            "longitude": self.config.LONGITUDE,
            "current_weather": "true"
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            with self._lock:
                self.state['weather'] = resp.json().get('current_weather')

    def _loop_network(self):
        # 1. WAN Throughput via OPNsense API
        try:
            url = f"https://{self.config.OPNSENSE_IP}/api/diagnostics/interface/getInterfaceStatistics"
            resp = requests.get(url, auth=self.config.OPNSENSE_AUTH, verify=False, timeout=5)
            
            if resp.status_code == 200:
                stats = resp.json().get('statistics', {})
                for iface in stats.values():
                    if iface.get('name') == self.config.WAN_INTERFACE:
                        rx = int(iface.get('received-bytes', 0))
                        tx = int(iface.get('sent-bytes', 0))
                        now = time.time()
                        
                        if self._network_state['last_check'] > 0:
                            dt = now - self._network_state['last_check']
                            if dt > 0.5:
                                # Bytes to Mbits
                                dl = (rx - self._network_state['last_rx']) / dt * 8 / 1_048_576
                                ul = (tx - self._network_state['last_tx']) / dt * 8 / 1_048_576
                                
                                # Clamp plausible values (0 - 10Gbps)
                                dl = max(0, min(dl, 10000))
                                ul = max(0, min(ul, 10000))

                                with self._lock:
                                    self.state['network']['dl'] = dl
                                    self.state['network']['ul'] = ul

                        self._network_state.update({'last_rx': rx, 'last_tx': tx, 'last_check': now})
                        break
        except Exception:
            pass # Network errors are transient, ignore

        # 2. Latency
        try:
            # Using subprocess for ping is simple and effective for this
            cmd = ['ping', '-c', '1', '-W', '1', '1.1.1.1']
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
            if 'time=' in output:
                lat = float(output.split('time=')[1].split(' ')[0])
                with self._lock:
                    self.state['network']['latency'] = lat
        except subprocess.CalledProcessError:
            with self._lock:
                self.state['network']['latency'] = None

    def _loop_services(self):
        results = {}
        for name, ip, port in self.config.SERVICES:
            is_up = False
            try:
                if port:
                    with socket.create_connection((ip, int(port)), timeout=1.0):
                        is_up = True
                else:
                    subprocess.check_call(['ping', '-c', '1', '-W', '1', ip],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    is_up = True
            except (socket.timeout, socket.error, subprocess.CalledProcessError):
                is_up = False
            results[name] = is_up

        # Backup Status
        backups = {}
        if os.path.exists(self.config.BACKUP_STATUS_PATH):
            try:
                with open(self.config.BACKUP_STATUS_PATH, 'r') as f:
                    backups = json.load(f)
            except json.JSONDecodeError:
                pass

        with self._lock:
            self.state['services'] = results
            self.state['backups'] = backups

    def _loop_system(self):
        cpu = psutil.cpu_percent() if psutil else 0
        ram = psutil.virtual_memory().percent if psutil else 0
        temp = 0.0
        
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read().strip()) / 1000.0
        except FileNotFoundError:
            pass

        with self._lock:
            self.state['system'] = {'cpu': cpu, 'ram': ram, 'temp': temp}

