# demo/sensor_simulator.py
"""
Sensor Simulator – generates realistic PLC data with configurable noise,
drift, and a high-speed Demo Mode for screen recording.
"""

import math
import random
import time
from typing import Dict, Union

class TemperatureSensorSimulator:
    """
    Simulates a temperature sensor with setpoint, drift, noise, and cyclic component.
    Demo mode multiplies speed and noise, and introduces random setpoint jumps.
    """

    def __init__(self, setpoint: float = 65.5,
                 noise_amplitude: float = 1.5,
                 drift_speed: float = 0.05):
        self.setpoint = setpoint
        self.noise_amplitude = noise_amplitude
        self.drift_speed = drift_speed
        self.start_time = time.time()
        self._last_value = setpoint
        self.demo_mode = False
        self._demo_jump_counter = 0

    def read(self) -> float:
        """Return the next simulated temperature value."""
        elapsed = time.time() - self.start_time
        speed_mult = 5.0 if self.demo_mode else 1.0
        noise_mult = 3.0 if self.demo_mode else 1.0

        # Sinusoidal drift
        drift = math.sin(elapsed * self.drift_speed * speed_mult) * 2.0
        # Gaussian noise
        noise = random.gauss(0, self.noise_amplitude * 0.3 * noise_mult)
        # Small cyclic component
        cycle = math.sin(elapsed * 0.1 * speed_mult) * 0.5

        # Demo mode: random setpoint jumps every ~2 seconds (approx)
        if self.demo_mode and random.random() < 0.02:
            jump = random.uniform(-5, 5)
            self.setpoint = max(40, min(90, self.setpoint + jump))
            self._demo_jump_counter += 1

        value = self.setpoint + drift + noise + cycle
        value = max(-50.0, min(150.0, value))
        self._last_value = round(value, 2)
        return self._last_value

    def set_setpoint(self, new_sp: Union[float, int]) -> None:
        """Update the setpoint."""
        self.setpoint = float(new_sp)

    def set_demo_mode(self, active: bool) -> None:
        """Enable or disable Demo Mode."""
        self.demo_mode = active
        if not active:
            # Reset jump counter for clarity
            self._demo_jump_counter = 0

    @property
    def last_value(self) -> float:
        return self._last_value


class SystemMetricsSimulator:
    """
    Simulates system metrics (CPU and memory usage) with realistic variation.
    Demo mode increases speed and noise.
    """

    def __init__(self, cpu_base: float = 12.0, mem_base: float = 45.0):
        self.cpu_base = cpu_base
        self.mem_base = mem_base
        self.start_time = time.time()
        self.demo_mode = False

    def get_metrics(self) -> Dict[str, float]:
        """Return a dict with 'cpu' and 'memory' (both in %), and uptime seconds."""
        elapsed = time.time() - self.start_time
        speed_mult = 5.0 if self.demo_mode else 1.0
        noise_mult = 3.0 if self.demo_mode else 1.0

        cpu_variation = math.sin(elapsed * 0.02 * speed_mult) * 5
        mem_variation = math.cos(elapsed * 0.015 * speed_mult) * 3

        cpu_noise = random.uniform(-2, 2) * noise_mult
        mem_noise = random.uniform(-1.5, 1.5) * noise_mult

        cpu = max(0, min(100, self.cpu_base + cpu_variation + cpu_noise))
        mem = max(0, min(100, self.mem_base + mem_variation + mem_noise))
        return {
            "cpu": round(cpu, 2),
            "memory": round(mem, 2),
            "uptime_seconds": int(time.time() - self.start_time),
        }

    def set_demo_mode(self, active: bool) -> None:
        """Enable or disable Demo Mode."""
        self.demo_mode = active