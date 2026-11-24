# swivel-rl

Experimental Windows helper that converts physical mouse movement into Rocket League camera swivel through a virtual cursor and a dead zone.

## How it works

The app captures relative mouse movement through Windows Raw Input and translates each delta into the position of a virtual cursor. The cursor integrates movement, applies sensitivity and clamping. Movement outside that dead zone is converted into horizontal and vertical axis values through hysteresis and a configurable response curve. In held digital mode, the SendInput backend presses the corresponding Rocket League Camera Swivel key while the axis is active and releases it as the cursor returns to the center. The input loop runs only when Rocket League is foreground, and it releases every injected key on focus loss, manual disarming, or shutdown.

## Install

```bash
python -m pip install -e .
```

## Setup

To get started you'll need a config file, to write a default config run:
```bash
python -m swivel_rl.cli --write-default config.json
```
Most important options include:
- Deadzone dimensions
- Digital mode
- Keys that are bound to camera swivel in RL (deafult: Q,E,UP,DOWN)

To run the script with graphical interface (most reccomended):
```bash
python -m swivel_rl.cli --config config.json --backend sendinput_keyboard --ui
```

## Configuration

For the keyboard backend, bind these same keys in Rocket League to Camera Swivel Left, Right, Up, and Down. Keep Free Look off: this helper emulates **swivel keys**, not unrestricted free-look mouse input

Key fields:

- `backend`: `dry_run` or `sendinput_keyboard`.
> [!NOTE]
> You'll always want to run with `sendinput_keyboard` if you actually want the script to work, `dry_run` is mostly for testing 
- `mouse_device_path_contains`: optional device path fragment used to limit capture; blank captures all raw mice.
- `target_processes`: process names allowed to receive input.
- `disarm_hotkey`: default `["CONTROL", "SHIFT", "HOME"]`.
- `cursor.sensitivity_x`, `cursor.sensitivity_y`: mouse delta multipliers.
- `cursor.outer_width`, `cursor.outer_height`: virtual cursor clamp rectangle.
- `cursor.recenter_rate`: exponential recentering rate while the cursor is inside the dead zone; directions in held digital mode are not recentered.
- `dead_zone.inner_width`, `dead_zone.inner_height`: no-output rectangle.
- `dead_zone.outer_width`, `dead_zone.outer_height`: full-output rectangle.
- `dead_zone.hysteresis`: fraction of the inner half-size used to prevent boundary chatter; default `0.1`.
- `response.exponent`: response curve shape.
- `response.gain_x`, `response.gain_y`: output scaling.
- `response.activation_threshold`: minimum output before a digital key is pressed; default `0.0`.
- `digital_mode`: `held` holds the swivel key until the cursor re-enters the dead zone; `pulse` is legacy/experimental.
- `pulse_min_hz`, `pulse_max_hz`, `pulse_width_ms`: legacy tap timing, unused by `held`.
- `focus_debounce_ms`: focus flapping tolerance before arming/disarming.
- `keys.left`, `keys.right`, `keys.up`, `keys.down`: keys sent by `sendinput_keyboard`.

## Other commands

List raw input mice:

```bash
python -m swivel_rl.cli --list-devices
```

Open the configuration UI:

```bash
python -m swivel_rl.cli --config config.json --ui
```

Run in dry-run mode:

```bash
python -m swivel_rl.cli --config config.json
```

Run with diagnostics written to a file:

```bash
python -m swivel_rl.cli --config config.json --backend sendinput_keyboard --log-file swivel-debug.log
```

Run with real keyboard injection:

```bash
python -m swivel_rl.cli --config config.json --backend sendinput_keyboard
```

Generate a full example config:

```bash
python -m swivel_rl.cli --write-default config.example.generated.json
```

## Safety

- No game memory reads or writes.
- No DLL injection, internal hooks, game-file modification, or anti-cheat bypass.
- Input is active only while a configured Rocket League process is foreground.
- All synthetic keys are released on focus loss, panic hotkey, error, Ctrl+C, and shutdown.
- Dry-run mode is the default and does not inject input.
- EAC is required for online play on PC, and third-party mods cannot offer a competitive advantage in online play.
- Test first in training or a private match, then with EAC enabled, before any online use.

There is no official guarantee that external input translation is approved. See `docs/FEASIBILITY.md`.

## License

MIT. See `LICENSE`.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```
