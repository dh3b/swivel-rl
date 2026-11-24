from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .app import SwivelApp
from .config import (
    VALID_BACKENDS,
    Config,
    CursorConfig,
    DeadZoneConfig,
    KeysConfig,
    ResponseConfig,
    save_config,
)
from .win32_input import list_mouse_devices


def run_ui(config: Config, config_path: str | None) -> int:
    ConfigWindow(config, config_path).mainloop()
    return 0


class ConfigWindow(tk.Tk):
    def __init__(self, config: Config, config_path: str | None) -> None:
        super().__init__()
        self.config_path = config_path
        self.app: SwivelApp | None = None
        self.worker: threading.Thread | None = None
        self.vars: dict[str, tk.Variable] = {}
        self.title("swivel-rl")
        self.geometry("760x760")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build(config)

    def _build(self, config: Config) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        self.vars["backend"] = tk.StringVar(value=config.backend)
        self.vars["target_processes"] = tk.StringVar(value=",".join(config.target_processes))
        self.vars["mouse_device_path_contains"] = tk.StringVar(value=config.mouse_device_path_contains)
        self.vars["tick_rate_hz"] = tk.StringVar(value=str(config.tick_rate_hz))
        self.vars["digital_mode"] = tk.StringVar(value=config.digital_mode)
        self.vars["pulse_min_hz"] = tk.StringVar(value=str(config.pulse_min_hz))
        self.vars["pulse_max_hz"] = tk.StringVar(value=str(config.pulse_max_hz))
        self.vars["pulse_width_ms"] = tk.StringVar(value=str(config.pulse_width_ms))
        self.vars["focus_debounce_ms"] = tk.StringVar(value=str(config.focus_debounce_ms))
        self.vars["require_target_focus"] = tk.BooleanVar(value=config.require_target_focus)
        self.vars["log_events"] = tk.BooleanVar(value=config.log_events)
        self.vars["disarm_hotkey"] = tk.StringVar(value="+".join(config.disarm_hotkey))

        for key, value in vars(config.cursor).items():
            self.vars[f"cursor.{key}"] = tk.StringVar(value=str(value))
        for key, value in vars(config.dead_zone).items():
            self.vars[f"dead_zone.{key}"] = tk.StringVar(value=str(value))
        for key, value in vars(config.response).items():
            self.vars[f"response.{key}"] = tk.StringVar(value=str(value))
        for key, value in vars(config.keys).items():
            self.vars[f"keys.{key}"] = tk.StringVar(value=value.upper())

        row = 0
        ttk.Label(root, text="Backend").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Combobox(
            root,
            textvariable=self.vars["backend"],
            values=sorted(VALID_BACKENDS),
            state="readonly",
            width=30,
        ).grid(row=row, column=1, sticky="ew", pady=2)
        row += 1

        self._entry(root, "Target processes (comma separated)", "target_processes", row, wide=True)
        row += 1

        ttk.Label(root, text="Mouse device path contains (blank = all mice)").grid(row=row, column=0, sticky="w", pady=2)
        self.device_combo = ttk.Combobox(
            root,
            textvariable=self.vars["mouse_device_path_contains"],
            values=[config.mouse_device_path_contains],
            width=60,
        )
        self.device_combo.grid(row=row, column=1, sticky="ew", pady=2)
        ttk.Button(root, text="Refresh devices", command=self._refresh_devices).grid(
            row=row, column=2, sticky="w", padx=4, pady=2
        )
        row += 1

        self._entry(root, "Tick rate Hz", "tick_rate_hz", row)
        row += 1

        ttk.Label(root, text="Digital mode (held recommended)").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Combobox(
            root,
            textvariable=self.vars["digital_mode"],
            values=("held", "pulse"),
            state="readonly",
            width=30,
        ).grid(row=row, column=1, sticky="ew", pady=2)
        row += 1

        self._entry(root, "Pulse min Hz", "pulse_min_hz", row)
        row += 1
        self._entry(root, "Pulse max Hz", "pulse_max_hz", row)
        row += 1
        self._entry(root, "Pulse width ms", "pulse_width_ms", row)
        row += 1
        self._entry(root, "Focus debounce ms", "focus_debounce_ms", row)
        row += 1

        ttk.Checkbutton(
            root,
            text="Only arm when Rocket League is foreground",
            variable=self.vars["require_target_focus"],
        ).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Checkbutton(
            root,
            text="Log input events to stdout",
            variable=self.vars["log_events"],
        ).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        self._entry(root, "Disarm hotkey (+ separated)", "disarm_hotkey", row)
        row += 1

        sections = [
            (
                "Cursor",
                [
                    ("cursor.sensitivity_x", "Sensitivity X"),
                    ("cursor.sensitivity_y", "Sensitivity Y"),
                    ("cursor.outer_width", "Outer width"),
                    ("cursor.outer_height", "Outer height"),
                    ("cursor.recenter_rate", "Recenter rate"),
                ],
            ),
            (
                "Dead zone",
                [
                    ("dead_zone.inner_width", "Inner width"),
                    ("dead_zone.inner_height", "Inner height"),
                    ("dead_zone.outer_width", "Outer width"),
                    ("dead_zone.outer_height", "Outer height"),
                ],
            ),
            (
                "Response",
                [
                    ("response.exponent", "Exponent"),
                    ("response.gain_x", "Gain X"),
                    ("response.gain_y", "Gain Y"),
                    ("response.activation_threshold", "Activation threshold"),
                ],
            ),
            (
                "Digital keys",
                [
                    ("keys.left", "Left"),
                    ("keys.right", "Right"),
                    ("keys.up", "Up"),
                    ("keys.down", "Down"),
                ],
            ),
        ]
        for title, fields in sections:
            ttk.Label(root, text=title, font=("TkDefaultFont", 10, "bold")).grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(8, 2)
            )
            row += 1
            for key, label in fields:
                self._entry(root, label, key, row)
                row += 1

        buttons = ttk.Frame(root)
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(12, 4))
        self.start_button = ttk.Button(buttons, text="Start", command=self._start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Stop", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=4)
        ttk.Button(buttons, text="Save config", command=self._save).pack(side="left", padx=4)
        row += 1

        self.status = tk.StringVar(value="Stopped")
        ttk.Label(root, textvariable=self.status, foreground="#444444").grid(
            row=row, column=0, columnspan=3, sticky="w"
        )
        row += 1

        note = (
            "Dry run records events without injecting input. "
            "SendInput keyboard uses held arrow/letter keys and requires Rocket League free look."
        )
        ttk.Label(root, text=note, wraplength=720, foreground="#666666").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        root.columnconfigure(1, weight=1)

    def _entry(self, parent: ttk.Frame, label: str, key: str, row: int, wide: bool = False) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(parent, textvariable=self.vars[key], width=70 if wide else 24)
        entry.grid(
            row=row,
            column=1,
            columnspan=2 if wide else 1,
            sticky="ew",
            pady=2,
        )

    def _refresh_devices(self) -> None:
        try:
            paths = [""] + [device["path"] for device in list_mouse_devices()]
        except Exception as exc:
            messagebox.showerror("Device enumeration failed", str(exc))
            return
        self.device_combo["values"] = paths
        self.status.set(f"Found {len(paths) - 1} raw mouse device(s)")

    def _config_from_fields(self) -> Config:
        backend = self.vars["backend"].get()
        if backend not in VALID_BACKENDS:
            raise ValueError(f"Unsupported backend: {backend}")

        def number(key: str) -> float:
            try:
                return float(self.vars[key].get())
            except ValueError as exc:
                raise ValueError(f"{key} must be a number") from exc

        return Config(
            backend=backend,
            target_processes=tuple(
                part.strip()
                for part in self.vars["target_processes"].get().split(",")
                if part.strip()
            ),
            mouse_device_path_contains=self.vars["mouse_device_path_contains"].get(),
            tick_rate_hz=number("tick_rate_hz"),
            digital_mode=self.vars["digital_mode"].get(),
            pulse_min_hz=number("pulse_min_hz"),
            pulse_max_hz=number("pulse_max_hz"),
            pulse_width_ms=number("pulse_width_ms"),
            focus_debounce_ms=number("focus_debounce_ms"),
            require_target_focus=bool(self.vars["require_target_focus"].get()),
            disarm_hotkey=tuple(
                part.strip().upper()
                for part in self.vars["disarm_hotkey"].get().split("+")
                if part.strip()
            ),
            log_events=bool(self.vars["log_events"].get()),
            cursor=CursorConfig(
                sensitivity_x=number("cursor.sensitivity_x"),
                sensitivity_y=number("cursor.sensitivity_y"),
                outer_width=number("cursor.outer_width"),
                outer_height=number("cursor.outer_height"),
                recenter_rate=number("cursor.recenter_rate"),
            ),
            dead_zone=DeadZoneConfig(
                inner_width=number("dead_zone.inner_width"),
                inner_height=number("dead_zone.inner_height"),
                outer_width=number("dead_zone.outer_width"),
                outer_height=number("dead_zone.outer_height"),
                hysteresis=number("dead_zone.hysteresis"),
            ),
            response=ResponseConfig(
                exponent=number("response.exponent"),
                gain_x=number("response.gain_x"),
                gain_y=number("response.gain_y"),
                activation_threshold=number("response.activation_threshold"),
            ),
            keys=KeysConfig(
                left=self.vars["keys.left"].get().strip().upper(),
                right=self.vars["keys.right"].get().strip().upper(),
                up=self.vars["keys.up"].get().strip().upper(),
                down=self.vars["keys.down"].get().strip().upper(),
            ),
        )

    def _save(self) -> None:
        try:
            config = self._config_from_fields()
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return
        if not self.config_path:
            messagebox.showinfo("No config path", "Start with --config <path> to enable saving.")
            return
        save_config(config, self.config_path)
        self.status.set(f"Saved {self.config_path}")

    def _start(self) -> None:
        try:
            config = self._config_from_fields()
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return
        if self.config_path:
            save_config(config, self.config_path)
        self.app = SwivelApp(config)
        self.worker = threading.Thread(target=self._worker, args=(self.app,), daemon=True)
        self.worker.start()
        self.start_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.status.set("Running")

    def _worker(self, app: SwivelApp) -> None:
        try:
            app.run()
        except Exception as exc:
            self.after(0, lambda: self._on_stopped(f"Error: {exc}"))
        else:
            self.after(0, lambda: self._on_stopped("Stopped"))

    def _stop(self) -> None:
        if self.app is None:
            return
        self.app.stop()
        if self.worker is not None and self.worker.is_alive():
            self.worker.join(timeout=3.0)
        self._on_stopped("Stopped")

    def _on_stopped(self, status: str) -> None:
        self.status.set(status)
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.app = None
        self.worker = None

    def _on_close(self) -> None:
        self._stop()
        self.destroy()
