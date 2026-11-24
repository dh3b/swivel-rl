from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VALID_BACKENDS = {"dry_run", "sendinput_keyboard"}
VALID_DIGITAL_MODES = {"held", "pulse"}


@dataclass
class CursorConfig:
    sensitivity_x: float = 1.0
    sensitivity_y: float = 1.0
    outer_width: float = 1800.0
    outer_height: float = 1800.0
    recenter_rate: float = 5.0


@dataclass
class DeadZoneConfig:
    inner_width: float = 240.0
    inner_height: float = 240.0
    outer_width: float = 1500.0
    outer_height: float = 1500.0
    hysteresis: float = 0.1


@dataclass
class ResponseConfig:
    exponent: float = 1.0
    gain_x: float = 1.0
    gain_y: float = 1.0
    activation_threshold: float = 0.0


@dataclass
class KeysConfig:
    left: str = "Q"
    right: str = "E"
    up: str = "UP"
    down: str = "DOWN"


@dataclass
class Config:
    backend: str = "dry_run"
    target_processes: tuple[str, ...] = (
        "rocketleague.exe",
        "rocketleague-win64-shipping.exe",
    )
    mouse_device_path_contains: str = ""
    tick_rate_hz: float = 120.0
    digital_mode: str = "held"
    pulse_min_hz: float = 2.0
    pulse_max_hz: float = 12.0
    pulse_width_ms: float = 25.0
    focus_debounce_ms: float = 150.0
    require_target_focus: bool = True
    disarm_hotkey: tuple[str, ...] = ("CONTROL", "SHIFT", "HOME")
    log_events: bool = False
    cursor: CursorConfig = None
    dead_zone: DeadZoneConfig = None
    response: ResponseConfig = None
    keys: KeysConfig = None

    def __post_init__(self) -> None:
        self.cursor = self.cursor or CursorConfig()
        self.dead_zone = self.dead_zone or DeadZoneConfig()
        self.response = self.response or ResponseConfig()
        self.keys = self.keys or KeysConfig()
        if self.backend not in VALID_BACKENDS:
            raise ValueError(f"Unsupported backend: {self.backend}")
        if self.digital_mode not in VALID_DIGITAL_MODES:
            raise ValueError(f"Unsupported digital mode: {self.digital_mode}")
        if self.pulse_min_hz <= 0 or self.pulse_max_hz <= 0:
            raise ValueError("Pulse rates must be positive")
        if self.pulse_max_hz < self.pulse_min_hz:
            raise ValueError("pulse_max_hz must be at least pulse_min_hz")
        if self.pulse_width_ms <= 0:
            raise ValueError("pulse_width_ms must be positive")
        if self.focus_debounce_ms < 0:
            raise ValueError("focus_debounce_ms cannot be negative")
        if not 0.0 <= self.dead_zone.hysteresis < 1.0:
            raise ValueError("dead_zone.hysteresis must be in [0, 1)")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["target_processes"] = list(self.target_processes)
        data["disarm_hotkey"] = list(self.disarm_hotkey)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Config":
        data = data or {}

        def section(name: str, factory: Any) -> Any:
            values = data.get(name) or {}
            return factory(**values)

        target_processes = tuple(data.get("target_processes", cls.target_processes))
        disarm_hotkey = tuple(data.get("disarm_hotkey", cls.disarm_hotkey))
        return cls(
            backend=data.get("backend", "dry_run"),
            target_processes=target_processes,
            mouse_device_path_contains=str(data.get("mouse_device_path_contains", "")),
            tick_rate_hz=float(data.get("tick_rate_hz", 120.0)),
            digital_mode=str(data.get("digital_mode", "held")),
            pulse_min_hz=float(data.get("pulse_min_hz", 2.0)),
            pulse_max_hz=float(data.get("pulse_max_hz", 12.0)),
            pulse_width_ms=float(data.get("pulse_width_ms", 25.0)),
            focus_debounce_ms=float(data.get("focus_debounce_ms", 150.0)),
            require_target_focus=bool(data.get("require_target_focus", True)),
            disarm_hotkey=disarm_hotkey,
            log_events=bool(data.get("log_events", False)),
            cursor=section("cursor", CursorConfig),
            dead_zone=section("dead_zone", DeadZoneConfig),
            response=section("response", ResponseConfig),
            keys=section("keys", KeysConfig),
        )


def load_config(path: str | Path | None) -> Config:
    if not path:
        return Config()
    config_path = Path(path)
    if not config_path.exists():
        return Config()
    with config_path.open("r", encoding="utf-8") as handle:
        return Config.from_dict(json.load(handle))


def save_config(config: Config, path: str | Path) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2)
        handle.write("\n")
