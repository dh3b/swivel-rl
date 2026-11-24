from __future__ import annotations

import time
from typing import Callable, Protocol

from .keys import parse_key


class InputBackend(Protocol):
    def set_axis(self, axis: str, value: float) -> None: ...

    def tick(self, dt: float) -> None: ...

    def release_all(self) -> None: ...

    def close(self) -> None: ...


class KeyboardInjector(Protocol):
    def send_key(self, virtual_key: int, down: bool) -> None: ...


class DryRunBackend:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self.events: list[tuple[str, float]] = []
        self._last: dict[str, float] = {}
        self._log = log or (lambda message: None)

    def set_axis(self, axis: str, value: float) -> None:
        self.events.append((axis, value))
        if self._last.get(axis) != value:
            self._log(f"dry_run axis={axis} value={value:.3f}")
            self._last[axis] = value

    def tick(self, dt: float) -> None:
        return None

    def release_all(self) -> None:
        self.events.append(("release", 0.0))
        self._log("dry_run release_all")

    def close(self) -> None:
        return None


class SendInputKeyboardBackend:
    def __init__(
        self,
        injector: KeyboardInjector,
        left: str,
        right: str,
        up: str,
        down: str,
        mode: str = "held",
        pulse_min_hz: float = 2.0,
        pulse_max_hz: float = 12.0,
        pulse_width_ms: float = 25.0,
        clock: Callable[[], float] = time.perf_counter,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._injector = injector
        self._clock = clock
        self._log = log or (lambda message: None)
        self._mode = mode
        self._pulse_min_hz = max(pulse_min_hz, 0.01)
        self._pulse_max_hz = max(pulse_max_hz, self._pulse_min_hz)
        self._pulse_width = max(pulse_width_ms, 1.0) / 1000.0
        self._keys = {
            ("x", -1): parse_key(left),
            ("x", 1): parse_key(right),
            ("y", -1): parse_key(up),
            ("y", 1): parse_key(down),
        }
        self._held: dict[str, int] = {}
        self._pulses: dict[str, dict[str, object]] = {
            axis: {"direction": 0, "next_at": 0.0, "pressed": None, "release_at": 0.0, "value": 0.0}
            for axis in ("x", "y")
        }

    def set_axis(self, axis: str, value: float) -> None:
        direction = 1 if value > 0.0 else -1 if value < 0.0 else 0
        if self._mode == "held":
            self._set_held_axis(axis, direction)
        else:
            self._set_pulse_axis(axis, direction, abs(value))

    def tick(self, dt: float) -> None:
        if self._mode == "held":
            return
        now = self._clock()
        for state in self._pulses.values():
            pressed = state["pressed"]
            if pressed is not None and now >= float(state["release_at"]):
                self._injector.send_key(int(pressed), False)
                self._log(f"key up vk={pressed}")
                state["pressed"] = None

    def release_all(self) -> None:
        keys = set(self._held.values())
        for state in self._pulses.values():
            pressed = state["pressed"]
            if pressed is not None:
                keys.add(int(pressed))
            state["direction"] = 0
            state["next_at"] = 0.0
            state["pressed"] = None
            state["release_at"] = 0.0
            state["value"] = 0.0
        for virtual_key in sorted(keys):
            self._injector.send_key(virtual_key, False)
            self._log(f"key up vk={virtual_key}")
        self._held.clear()

    def close(self) -> None:
        self.release_all()

    def _set_held_axis(self, axis: str, direction: int) -> None:
        desired = self._keys.get((axis, direction)) if direction else None
        current = self._held.get(axis)
        if desired == current:
            return
        if current is not None:
            self._injector.send_key(current, False)
            self._log(f"key up vk={current}")
            self._held.pop(axis, None)
        if desired is not None:
            self._injector.send_key(desired, True)
            self._log(f"key down vk={desired}")
            self._held[axis] = desired

    def _set_pulse_axis(self, axis: str, direction: int, magnitude: float) -> None:
        state = self._pulses[axis]
        if direction != int(state["direction"]):
            pressed = state["pressed"]
            if pressed is not None:
                self._injector.send_key(int(pressed), False)
                self._log(f"key up vk={pressed}")
                state["pressed"] = None
            state["direction"] = direction
            state["next_at"] = 0.0
        state["value"] = magnitude
        if direction == 0:
            return

        now = self._clock()
        pressed = state["pressed"]
        if pressed is not None and now >= float(state["release_at"]):
            self._injector.send_key(int(pressed), False)
            self._log(f"key up vk={pressed}")
            state["pressed"] = None
        if now < float(state["next_at"]):
            return

        virtual_key = self._keys[(axis, direction)]
        self._injector.send_key(virtual_key, True)
        self._log(f"key down vk={virtual_key} axis={axis} value={magnitude:.3f}")
        state["pressed"] = virtual_key
        state["release_at"] = now + self._pulse_width
        rate = self._pulse_min_hz + (self._pulse_max_hz - self._pulse_min_hz) * min(max(magnitude, 0.0), 1.0)
        state["next_at"] = now + 1.0 / rate
