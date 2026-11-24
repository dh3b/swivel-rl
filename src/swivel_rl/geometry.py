from __future__ import annotations

import math
from dataclasses import dataclass

from .config import CursorConfig, DeadZoneConfig, ResponseConfig


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass
class VirtualCursor:
    config: CursorConfig
    x: float = 0.0
    y: float = 0.0

    def update(self, dx: float, dy: float) -> None:
        half_width = max(self.config.outer_width, 0.0) / 2.0
        half_height = max(self.config.outer_height, 0.0) / 2.0
        self.x = clamp(self.x + dx * self.config.sensitivity_x, -half_width, half_width)
        self.y = clamp(self.y + dy * self.config.sensitivity_y, -half_height, half_height)

    def recenter(self, dt: float) -> None:
        rate = max(self.config.recenter_rate, 0.0)
        if rate <= 0.0 or dt <= 0.0:
            return
        factor = math.exp(-rate * dt)
        self.x *= factor
        self.y *= factor

    def reset(self) -> None:
        self.x = 0.0
        self.y = 0.0


@dataclass
class DeadZone:
    config: DeadZoneConfig
    _active_x: int = 0
    _active_y: int = 0

    def _axis(self, value: float, inner_half: float, outer_half: float, active: int) -> tuple[float, int]:
        if not math.isfinite(value) or outer_half <= inner_half:
            return 0.0, 0
        hysteresis = clamp(self.config.hysteresis, 0.0, 0.999) * inner_half
        if active:
            if abs(value) <= inner_half - hysteresis:
                active = 0
            elif (value > 0) != (active > 0):
                active = 1 if value > 0 else -1 if abs(value) > inner_half + hysteresis else 0
        elif abs(value) > inner_half + hysteresis:
            active = 1 if value > 0 else -1
        if not active:
            return 0.0, 0
        magnitude = (abs(value) - inner_half) / (outer_half - inner_half)
        magnitude = max(clamp(magnitude, 0.0, 1.0), 1e-6)
        return math.copysign(magnitude, active), active

    def evaluate(self, x: float, y: float) -> tuple[float, float]:
        axis_x, self._active_x = self._axis(
            x, self.config.inner_width / 2.0, self.config.outer_width / 2.0, self._active_x
        )
        axis_y, self._active_y = self._axis(
            y, self.config.inner_height / 2.0, self.config.outer_height / 2.0, self._active_y
        )
        return axis_x, axis_y

    def reset(self) -> None:
        self._active_x = 0
        self._active_y = 0


@dataclass
class ResponseCurve:
    config: ResponseConfig

    def _apply(self, value: float, gain: float) -> float:
        if not math.isfinite(value) or value == 0.0:
            return 0.0
        exponent = max(self.config.exponent, 0.01)
        shaped = abs(value) ** exponent
        return clamp(math.copysign(shaped * gain, value), -1.0, 1.0)

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return self._apply(x, self.config.gain_x), self._apply(y, self.config.gain_y)


class CameraController:
    def __init__(
        self,
        cursor: VirtualCursor,
        dead_zone: DeadZone,
        response: ResponseCurve,
        backend: "InputBackend",
    ) -> None:
        self.cursor = cursor
        self.dead_zone = dead_zone
        self.response = response
        self.backend = backend
        self.axis_x = 0.0
        self.axis_y = 0.0
        self._enabled = True

    def on_mouse_delta(self, dx: float, dy: float) -> None:
        self.cursor.update(dx, dy)
        self._update_outputs()

    def tick(self, dt: float, enabled: bool = True) -> None:
        raw_x, raw_y = self.dead_zone.evaluate(self.cursor.x, self.cursor.y)
        if raw_x == 0.0 and raw_y == 0.0:
            self.cursor.recenter(dt)
        self.backend.tick(dt)
        if not enabled:
            if self._enabled:
                self.axis_x = 0.0
                self.axis_y = 0.0
                self.cursor.reset()
                self.dead_zone.reset()
                self.backend.release_all()
            self._enabled = False
            return
        if not self._enabled:
            self.dead_zone.reset()
        self._enabled = True
        self._update_outputs()

    def disarm(self) -> None:
        self.cursor.reset()
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.dead_zone.reset()
        self._enabled = False
        self.backend.release_all()

    def _update_outputs(self) -> None:
        raw_x, raw_y = self.dead_zone.evaluate(self.cursor.x, self.cursor.y)
        axis_x, axis_y = self.response.apply(raw_x, raw_y)
        threshold = max(self.config_threshold, 0.0)
        self.axis_x = axis_x if abs(axis_x) >= threshold else 0.0
        self.axis_y = axis_y if abs(axis_y) >= threshold else 0.0
        self.backend.set_axis("x", self.axis_x)
        self.backend.set_axis("y", self.axis_y)

    @property
    def config_threshold(self) -> float:
        return self.response.config.activation_threshold
