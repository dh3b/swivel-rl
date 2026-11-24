from __future__ import annotations

import threading
import time

from .backends import DryRunBackend, InputBackend, SendInputKeyboardBackend
from .config import Config
from .detector import RocketLeagueDetector
from .geometry import CameraController, DeadZone, ResponseCurve, VirtualCursor
from .win32_input import HotkeyMonitor, RawInputMouseSource, Win32KeyboardInjector


def create_backend(config: Config, log) -> InputBackend:
    if config.backend == "dry_run":
        return DryRunBackend(log=log)
    if config.backend == "sendinput_keyboard":
        return SendInputKeyboardBackend(
            Win32KeyboardInjector(),
            config.keys.left,
            config.keys.right,
            config.keys.up,
            config.keys.down,
            mode=config.digital_mode,
            pulse_min_hz=config.pulse_min_hz,
            pulse_max_hz=config.pulse_max_hz,
            pulse_width_ms=config.pulse_width_ms,
            log=log,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")


class SwivelApp:
    def __init__(self, config: Config, log_file: str | None = None) -> None:
        self.config = config
        self._log_handle = None
        self._log = self._make_logger(log_file)
        self.backend = create_backend(config, self._log)
        self.cursor = VirtualCursor(config.cursor)
        self.dead_zone = DeadZone(config.dead_zone)
        self.response = ResponseCurve(config.response)
        self.controller = CameraController(self.cursor, self.dead_zone, self.response, self.backend)
        self.detector = RocketLeagueDetector(config.target_processes)
        self.hotkey = HotkeyMonitor(config.disarm_hotkey)
        self.source: RawInputMouseSource | None = None
        self.armed = False
        self.manual_disarmed = False
        self._focus_candidate: bool | None = None
        self._focus_candidate_since = 0.0
        self._stop_event = threading.Event()

    def _make_logger(self, log_file: str | None = None):
        if not self.config.log_events and not log_file:
            return lambda message: None
        if log_file:
            self._log_handle = open(log_file, "a", encoding="utf-8")

        def log(message: str) -> None:
            print(message, flush=True)
            if self._log_handle is not None:
                self._log_handle.write(message + "\n")
                self._log_handle.flush()

        return log

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> int:
        self._stop_event.clear()
        interval = 1.0 / max(self.config.tick_rate_hz, 1.0)
        self.source = RawInputMouseSource(
            self._on_mouse_delta,
            self.config.mouse_device_path_contains,
            self._log if self.config.log_events else None,
        )
        previous = time.perf_counter()
        try:
            self.source.start()
            self._log(f"capturing mouse device: {self.source.device_path}")
            while not self._stop_event.is_set():
                loop_started = time.perf_counter()
                dt = max(loop_started - previous, 0.0)
                previous = loop_started

                if self.hotkey.poll():
                    self.manual_disarmed = not self.manual_disarmed
                    self._log(f"manual disarm: {self.manual_disarmed}")

                if self.source.error:
                    raise RuntimeError(self.source.error)

                focused = not self.config.require_target_focus or self.detector.is_target_foreground()
                desired = focused and not self.manual_disarmed
                now = time.perf_counter()
                if desired != self._focus_candidate:
                    self._focus_candidate = desired
                    self._focus_candidate_since = now
                    self._log(f"focus candidate: {desired}")
                debounce = self.config.focus_debounce_ms / 1000.0
                if now - self._focus_candidate_since >= debounce:
                    self._set_armed(desired)
                self.controller.tick(dt, self.armed)

                elapsed = time.perf_counter() - loop_started
                time.sleep(max(0.0, interval - elapsed))
            self._log("stopped")
        except KeyboardInterrupt:
            self._log("stopped")
            return 0
        finally:
            self._set_armed(False)
            self.controller.disarm()
            self.backend.close()
            if self.source is not None:
                self.source.stop()
            if self._log_handle is not None:
                self._log_handle.close()
                self._log_handle = None
        return 0

    def _on_mouse_delta(self, dx: int, dy: int) -> None:
        self._log(f"raw dx={dx} dy={dy} armed={self.armed}")
        if not self.armed:
            return
        self.controller.on_mouse_delta(dx, dy)

    def _set_armed(self, armed: bool) -> None:
        if armed == self.armed:
            return
        self.armed = armed
        self._log(f"armed: {armed}")
        if not armed:
            self.controller.disarm()
