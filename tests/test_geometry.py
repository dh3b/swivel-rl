import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swivel_rl.backends import DryRunBackend
from swivel_rl.config import CursorConfig, DeadZoneConfig, ResponseConfig
from swivel_rl.geometry import CameraController, DeadZone, ResponseCurve, VirtualCursor


class VirtualCursorTests(unittest.TestCase):
    def test_update_and_clamp(self):
        cursor = VirtualCursor(CursorConfig(outer_width=100.0, outer_height=40.0))
        cursor.update(80.0, -30.0)
        self.assertEqual(cursor.x, 50.0)
        self.assertEqual(cursor.y, -20.0)

    def test_recenter(self):
        cursor = VirtualCursor(CursorConfig(recenter_rate=10.0))
        cursor.x = 100.0
        cursor.y = -50.0
        cursor.recenter(1.0)
        self.assertAlmostEqual(cursor.x, 100.0 * pow(2.718281828459045, -10.0), places=3)
        self.assertAlmostEqual(cursor.y, -50.0 * pow(2.718281828459045, -10.0), places=3)


class DeadZoneTests(unittest.TestCase):
    def test_axis_shape(self):
        dead_zone = DeadZone(DeadZoneConfig(inner_width=100.0, outer_width=300.0, inner_height=100.0, outer_height=300.0))
        self.assertEqual(dead_zone.evaluate(0.0, 0.0), (0.0, 0.0))
        self.assertEqual(dead_zone.evaluate(50.0, 0.0)[0], 0.0)
        self.assertEqual(dead_zone.evaluate(100.0, 0.0)[0], 0.5)
        self.assertEqual(dead_zone.evaluate(150.0, 0.0)[0], 1.0)
        self.assertEqual(dead_zone.evaluate(-150.0, 0.0)[0], -1.0)

    def test_hysteresis_holds_until_return(self):
        dead_zone = DeadZone(
            DeadZoneConfig(
                inner_width=100.0,
                outer_width=300.0,
                inner_height=100.0,
                outer_height=300.0,
                hysteresis=0.1,
            )
        )
        self.assertEqual(dead_zone.evaluate(54.0, 0.0)[0], 0.0)
        self.assertGreater(dead_zone.evaluate(56.0, 0.0)[0], 0.0)
        self.assertGreater(dead_zone.evaluate(49.0, 0.0)[0], 0.0)
        self.assertEqual(dead_zone.evaluate(44.0, 0.0)[0], 0.0)


class ResponseCurveTests(unittest.TestCase):
    def test_exponent_and_gain(self):
        response = ResponseCurve(ResponseConfig(exponent=2.0, gain_x=0.5, gain_y=1.0))
        self.assertEqual(response.apply(0.5, -0.5), (0.125, -0.25))


class CameraControllerTests(unittest.TestCase):
    def build_controller(self):
        backend = DryRunBackend()
        controller = CameraController(
            VirtualCursor(CursorConfig(outer_width=1000.0, outer_height=500.0)),
            DeadZone(DeadZoneConfig(inner_width=100.0, outer_width=300.0, inner_height=100.0, outer_height=300.0)),
            ResponseCurve(ResponseConfig(exponent=1.0, gain_x=1.0, gain_y=1.0, activation_threshold=0.1)),
            backend,
        )
        return controller, backend

    def test_mouse_delta_sets_axis(self):
        controller, backend = self.build_controller()
        controller.on_mouse_delta(100.0, 0.0)
        self.assertEqual(controller.axis_x, 0.5)
        self.assertEqual(controller.axis_y, 0.0)
        self.assertIn(("x", 0.5), backend.events)

    def test_below_threshold_releases_axis(self):
        controller, backend = self.build_controller()
        controller.on_mouse_delta(59.0, 0.0)
        self.assertEqual(controller.axis_x, 0.0)
        self.assertIn(("x", 0.0), backend.events)

    def test_held_axis_survives_recenter_until_cursor_returns(self):
        controller, backend = self.build_controller()
        controller.on_mouse_delta(150.0, 0.0)
        self.assertGreater(controller.axis_x, 0.0)
        controller.tick(1.0, enabled=True)
        self.assertGreater(controller.axis_x, 0.0)
        controller.on_mouse_delta(-150.0, 0.0)
        self.assertEqual(controller.axis_x, 0.0)
        self.assertIn(("x", 0.0), backend.events)

    def test_disabled_tick_releases_all(self):
        controller, backend = self.build_controller()
        controller.on_mouse_delta(150.0, 0.0)
        controller.tick(0.016, enabled=False)
        self.assertEqual(controller.axis_x, 0.0)
        self.assertIn(("release", 0.0), backend.events)


if __name__ == "__main__":
    unittest.main()
