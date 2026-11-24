import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swivel_rl.config import Config, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = Config()
        self.assertEqual(config.backend, "dry_run")
        self.assertEqual(config.keys.left, "Q")
        self.assertEqual(config.tick_rate_hz, 120.0)
        self.assertEqual(config.digital_mode, "held")
        self.assertEqual(config.focus_debounce_ms, 150.0)
        self.assertEqual(config.dead_zone.inner_width, 240.0)
        self.assertEqual(config.dead_zone.inner_height, 240.0)
        self.assertEqual(config.dead_zone.outer_width, 1500.0)
        self.assertEqual(config.dead_zone.outer_height, 1500.0)
        self.assertEqual(config.cursor.outer_width, 1800.0)
        self.assertEqual(config.cursor.outer_height, 1800.0)

    def test_invalid_backend(self):
        with self.assertRaises(ValueError):
            Config.from_dict({"backend": "memory_write"})

    def test_invalid_hysteresis(self):
        with self.assertRaises(ValueError):
            Config.from_dict({"dead_zone": {"hysteresis": 1.0}})

    def test_round_trip(self):
        config = Config.from_dict(
            {
                "backend": "sendinput_keyboard",
                "target_processes": ["game.exe"],
                "disarm_hotkey": ["CONTROL", "ALT", "X"],
                "cursor": {"sensitivity_x": 2.5},
                "response": {"exponent": 1.7},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "config.json"
            save_config(config, path)
            loaded = load_config(path)
            raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded.backend, "sendinput_keyboard")
        self.assertEqual(loaded.target_processes, ("game.exe",))
        self.assertEqual(loaded.disarm_hotkey, ("CONTROL", "ALT", "X"))
        self.assertEqual(loaded.cursor.sensitivity_x, 2.5)
        self.assertEqual(loaded.response.exponent, 1.7)
        self.assertEqual(raw["keys"]["left"], "Q")
        self.assertEqual(raw["digital_mode"], "held")
        self.assertEqual(raw["focus_debounce_ms"], 150.0)
        self.assertEqual(raw["dead_zone"]["hysteresis"], 0.1)

    def test_missing_file_uses_defaults(self):
        config = load_config("does-not-exist.json")
        self.assertEqual(config.backend, "dry_run")


if __name__ == "__main__":
    unittest.main()
