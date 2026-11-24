import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swivel_rl.backends import DryRunBackend, SendInputKeyboardBackend
from swivel_rl.keys import parse_key
from swivel_rl.win32_input import RawInputMouseSource


class FakeInjector:
    def __init__(self):
        self.calls = []

    def send_key(self, virtual_key, down):
        self.calls.append((virtual_key, down))


class DryRunBackendTests(unittest.TestCase):
    def test_records_events(self):
        backend = DryRunBackend()
        backend.set_axis("x", 0.25)
        backend.release_all()
        self.assertEqual(backend.events, [("x", 0.25), ("release", 0.0)])


class SendInputKeyboardBackendTests(unittest.TestCase):
    def build_backend(self):
        injector = FakeInjector()
        backend = SendInputKeyboardBackend(injector, "Q", "E", "UP", "DOWN", mode="held")
        return injector, backend

    def test_positive_x_presses_right(self):
        injector, backend = self.build_backend()
        backend.set_axis("x", 0.5)
        self.assertEqual(injector.calls, [(parse_key("E"), True)])

    def test_direction_change_releases_old_key_before_pressing_new(self):
        injector, backend = self.build_backend()
        backend.set_axis("x", 0.5)
        backend.set_axis("x", -0.5)
        self.assertEqual(
            injector.calls,
            [
                (parse_key("E"), True),
                (parse_key("E"), False),
                (parse_key("Q"), True),
            ],
        )

    def test_release_all_sends_key_up(self):
        injector, backend = self.build_backend()
        backend.set_axis("y", -1.0)
        backend.release_all()
        self.assertEqual(
            injector.calls,
            [
                (parse_key("UP"), True),
                (parse_key("UP"), False),
            ],
        )

    def test_zero_axis_releases_held_key(self):
        injector, backend = self.build_backend()
        backend.set_axis("x", 1.0)
        backend.set_axis("x", 0.0)
        self.assertEqual(
            injector.calls,
            [
                (parse_key("E"), True),
                (parse_key("E"), False),
            ],
        )


class SendInputPulseBackendTests(unittest.TestCase):
    def build_backend(self, clock):
        injector = FakeInjector()
        backend = SendInputKeyboardBackend(
            injector,
            "Q",
            "E",
            "UP",
            "DOWN",
            mode="pulse",
            pulse_min_hz=10.0,
            pulse_max_hz=10.0,
            pulse_width_ms=20.0,
            clock=clock,
        )
        return injector, backend

    def test_axis_emits_discrete_key_tap(self):
        clock = [0.0]
        injector, backend = self.build_backend(lambda: clock[0])
        backend.set_axis("x", 1.0)
        self.assertEqual(injector.calls, [(parse_key("E"), True)])
        backend.tick(0.001)
        self.assertEqual(injector.calls, [(parse_key("E"), True)])
        clock[0] = 0.03
        backend.tick(0.001)
        self.assertEqual(
            injector.calls,
            [(parse_key("E"), True), (parse_key("E"), False)],
        )

    def test_axis_repeats_only_after_interval(self):
        clock = [0.0]
        injector, backend = self.build_backend(lambda: clock[0])
        backend.set_axis("x", 1.0)
        clock[0] = 0.05
        backend.tick(0.001)
        backend.set_axis("x", 1.0)
        clock[0] = 0.11
        backend.tick(0.001)
        backend.set_axis("x", 1.0)
        self.assertEqual(
            injector.calls,
            [
                (parse_key("E"), True),
                (parse_key("E"), False),
                (parse_key("E"), True),
            ],
        )


class KeyParsingTests(unittest.TestCase):
    def test_letters_and_named_keys(self):
        self.assertEqual(parse_key("q"), ord("Q"))
        self.assertEqual(parse_key("HOME"), 0x24)
        self.assertEqual(parse_key("f13"), 0x7C)

    def test_invalid_key(self):
        with self.assertRaises(ValueError):
            parse_key("NOT_A_KEY")


class RawInputMouseSourceTests(unittest.TestCase):
    def test_window_and_message_loop_share_thread(self):
        events = []
        source = RawInputMouseSource(lambda dx, dy: None, on_event=events.append)
        source.start()
        try:
            self.assertTrue(source.running)
            self.assertTrue(any("rawinput thread started" in event for event in events))
        finally:
            source.stop()
        self.assertFalse(source.running)


if __name__ == "__main__":
    unittest.main()
