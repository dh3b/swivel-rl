# Feasibility and architecture report

## Scope and status

Date: 2026-11-24.

Current status: research and implementation are complete. The user confirmed that held Camera Swivel keys work in-game. Rocket League and EAC were not available in this environment, so analogue mapping, EAC-inclusive private-match validation, and latency measurement remain open.

## Research conclusions

### Rocket League input and camera behavior

Official Season 24 patch notes for v2.76 state:

> Modernized Keyboard and Mouse Controls: A brand new free look camera mode has been added with updated Mouse and Keyboard control defaults. Players can now also enable a center dot reticule to support the new camera movement. The free look camera mode is available to controller players as well.

Source: https://www.rocketleague.com/news/rocket-league-s24-patch-notes-v276

The Season 24 announcement says:

> Updated KBM Controls: A new Free Look Camera has been added that will allow players to focus their camera whenever and wherever they want. This can also be enabled for controllers for any player interested in experimenting with new camera controls.

Source: https://www.rocketleague.com/news/rocket-league-heads-to-the-streets-in-season-24

This means the safest first option is the native free look camera. Any external helper should be treated as an accessibility/customization experiment, not as a prerequisite.

Official camera-help text defines Camera Swivel Speed as:

> This setting is about how fast the camera turns along with your car.

Source: https://www.epicgames.com/help/en-US/category_RocketLeague/c-RocketLeague_Gameplay/what-are-camera-settings-in-rocket-league-a000084077

It does not document how partial analogue stick deflection maps to angular velocity. No authoritative source was found that proves Rocket League scales swivel speed proportionally with analogue magnitude.

Rocket League Known Issues confirms both mouse-movement swivel bindings and free-look/swivel bugs existed in shipped builds:

- Fixed in v2.67: Default Controls could apply unintended PC bindings, such as setting Camera Swivel to Mouse Movement.
- Fixed in v2.76: free-look camera offset stayed active when overtime began; Look at Ball on a wall added roll; Invert Swivel behaved differently on keyboard/mouse and controller.
- Current known issue: Some third-party controllers aren't detected on PC when EAC is on.

Source: https://www.rocketleague.com/known-issues

PCGamingWiki describes direct mouse-axis camera bindings as transient:

> Mouse axes are not bound to anything by default. Binding them to the camera will cause mouse movement to act like an analog stick, making the camera move at a constant speed and resetting to the default position instantly if movement stops.

Source: https://www.pcgamingwiki.com/wiki/Rocket_League

Steam Input documentation supports the general feasibility of simultaneous gamepad and mouse input:

> Gamepad and mouse input should be possible simultaneously

Source: https://partner.steamgames.com/doc/features/steam_controller/getting_started_for_devs

The same documentation distinguishes mouse-style and joystick-style actions and states that joystick-to-mouse conversion is supported but mouse-to-joystick conversion is not reliable because of in-game acceleration curves and deadzones.

RLBot issue #21 contains this report:

> It's possible to use right stick. The virtual controller is translated to direct input. I just didn't want people moving the camera wildly.

Source: https://github.com/RLBot/RLBot/issues/21

This is evidence that a virtual right stick can move the camera, but it is not proof of proportional analogue magnitude or of safe mixed input with current Rocket League builds.

Mixed input is generally possible, but multiple sources report UI prompt switching and stutter when controller and KBM input are used together. Rocket Science documents rapid prompt switching as the cause of frame-rate problems and mentions reWASD as a way to combine inputs into one virtual device. Source: https://rocketscience.fyi/know/rl/issues

### Windows input APIs

Microsoft Raw Input is the correct capture mechanism because it provides device-level relative deltas and source-device identity:

- An application must call RegisterRawInputDevices to receive raw input.
- RIDEV_INPUTSINK allows receiving input even when the application is not foreground.
- RAWINPUTHEADER.hDevice identifies the device generating the event.
- RAWMOUSE.lLastX and lLastY contain relative motion for MOUSE_MOVE_RELATIVE.
- GetRawInputBuffer exists for high-frequency mice where multiple events accumulate.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/inputdev/about-raw-input
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerrawinputdevices
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-rawinput
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getrawinputbuffer

Microsoft SendInput is the supported user-mode injection API:

> Synthesizes keystrokes, mouse motions, and button clicks.

It inserts events serially into the keyboard or mouse input stream and can fail under UIPI. Source: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput

Raw Input is capture-only. GameInput documentation describes reading devices and readings but did not reveal a documented user-mode injection path. Virtual gamepad options such as ViGEmBus or LuminalVGBus require a kernel driver, admin installation, signing, and anti-cheat compatibility testing. LuminalVGBus explicitly describes itself as alpha, unsigned, and not loaded. Source: https://github.com/NortheBridge/LuminalVGBus

Low-level hooks can identify injected events via LLMHF_INJECTED, but Microsoft recommends Raw Input in most cases and warns that global hooks hurt performance and conflict with other software. Hooks are therefore excluded from the implementation.

Local smoke verification on this Windows build confirmed Raw Input registration/shutdown and that a SendInput-relative mouse move sent to the desktop was not surfaced by Raw Input. This supports device-level capture without a desktop feedback loop, but it is not a substitute for in-game validation. It also showed that the first enumerated HID mouse is a webcam HID, so capture now accepts all raw mice by default instead of silently selecting the first one. User testing showed no `WM_INPUT`; the root cause was that the window was created on one thread and pumped on another. `RawInputMouseSource` now creates the hidden top-level window, registers devices, and pumps messages on the same thread, with `--log-file` diagnostics.

### Existing solutions

- Native free look camera: safest and no external process.
- Direct in-game mouse-axis binding to Camera Swivel: transient constant-speed behavior; unsuitable for a centred virtual cursor.
- AHK key remappers: ordinary OS input, but no reliable Windows mouse-to-camera implementation was found.
- Steam Input mouse joystick / gamepad emulation: plausible no-code alternative; depends on game settings and simultaneous-input support.
- reWASD + virtual gamepad: one user reports mapping mouse movement to the right joystick for Rocket League camera control. Source: https://forum.rewasd.com/forum/rewasd/technical-questions-aa/246997-rocket-league-on-kbm-with-wooting
- rlm2c: maps mouse velocity to an analogue stick using Interception and ViGEm drivers; its own README warns that Interception is blocked by some anti-cheats. Source: https://github.com/bozbez/rlm2c
- DoubleTap.RL: Linux uinput/evdev mouse macro; not applicable to Windows camera swivel. Source: https://github.com/enXov/doubletap-rl

### Policy and anti-cheat risk

Rocket League's Code of Conduct says users agree to Epic's Terms and Community Rules and warns:

> Just because something isn't specifically called out above doesn't mean it's OK.

Source: https://www.rocketleague.com/code-of-conduct

Epic Terms prohibit cheats, circumvention of gameplay integrity tools, and bot software. Source: https://legal.epicgames.com/epicgames/tos

The Code of Conduct's Third-Party Mods section says EAC is required for online play on PC, community mods will not run when EAC is enabled, and mods cannot offer a competitive advantage in online play. Sources: https://www.rocketleague.com/code-of-conduct and https://www.rocketleague.com/news/easy-anti-cheat-comes-to-rocket-league-on-pc-today

No official source explicitly whitelists input remappers, and no official source explicitly bans ordinary OS-level input translation. The design therefore stays strictly in user input space: no game process access, no injection, no hooks, no mods, no automation, no aim assistance, and no anti-cheat bypass.

## Decision

Genuine analogue swivel is still the preferred long-term technical approach, but it is not validated and is not appropriate for the first shipped backend.

The first implementation uses a shared capture/dead-zone pipeline with two backend paths:

1. `dry_run`: default; records intended axis commands without injecting anything.
2. `sendinput_keyboard`: opt-in; sends ordinary key down/up events for user-bound Camera Swivel keys while Rocket League is foreground.

Virtual analogue via right stick remains an experimental future backend. It requires a virtual gamepad driver, admin/signing decisions, and in-game proof that partial stick magnitude maps to camera speed. It must not be added silently.

Naive turbo-style key timing is rejected. With Free Look off, Camera Swivel keys move smoothly to deterministic fixed positions, so the digital backend holds the corresponding key while the cursor remains outside the dead zone. Pulse timing remains legacy/experimental and is not the primary mode. It stays purely user-driven; it does not automate game actions or aim.

## Approach comparison

| Approach | Fidelity | Complexity | Safety/policy | Decision |
|---|---:|---:|---|---|
| Native free look camera | Native | None | Lowest risk | Recommended first |
| Virtual right stick analogue axis | Potentially high | High: driver, signing, admin | Uncertain EAC compatibility | Deferred pending validation/user consent |
| Held Camera Swivel keys via SendInput | Low-medium | Low | User-mode OS input; unconfirmed but low-risk if focused and user-driven | Implemented as default digital mode |
| Discrete Camera Swivel taps | Medium | Low | User-driven key taps, no automation | Legacy/experimental mode |
| Steam Input/reWASD/other remappers | Medium | User-side config | Vendor-supported input layer | Documented alternative |
| Mouse-axis direct binding | Low | Built-in | Low risk but technically transient | Rejected as primary mechanism |

## Architecture

- `MouseInput`: `RawInputMouseSource` captures relative physical mouse deltas on a hidden top-level window from all raw mice by default, with optional device-path filtering. Window creation, registration, and message pumping share one thread. Startup and event diagnostics can be written to a file via `--log-file`.
- `VirtualCursor`: integrates deltas into a cursor position clamped to an outer rectangle.
- `DeadZone`: converts cursor position into normalized horizontal and vertical magnitudes outside the inner rectangle.
- `ResponseCurve`: applies exponent and per-axis gain.
- `CameraController`: thresholds axes, owns arm/disarm behavior, and commands the backend.
- `InputBackend`: backend boundary with `set_axis`, `tick`, `release_all`, and `close`; `DryRunBackend` and `SendInputKeyboardBackend` implemented. Keyboard injection uses scancode-based SendInput events. Held mode is the default: it presses the corresponding Camera Swivel key while the cursor remains outside the dead zone and releases it when the cursor returns; pulse mode remains legacy/experimental.
- `RocketLeagueDetector`: checks the foreground process name/path.
- `ConfigurationManager`: JSON-backed `Config`, `load_config`, and `save_config`.
- `UI`: stdlib Tkinter `ConfigWindow` provides field editing, save/load, device refresh, and start/stop controls; CLI and config file remain available.

The input loop owns Raw Input capture, focus checks, ticking, and injection. It does not depend on GUI refresh rate.

## Safety model

- Start in `dry_run` mode.
- Require Rocket League to be the foreground process by default.
- Release all synthetic keys on focus loss, Ctrl+Shift+Home, exceptions, Ctrl+C, and shutdown. Focus changes are debounced by `focus_debounce_ms` before arming/disarming.
- Never hold both left and right, or up and down, on the same axis.
- Capture all physical mice by default, with an optional device-path filter.
- Do not use RIDEV_NOLEGACY, global hooks, memory access, DLL injection, game mods, or anti-cheat bypasses.
- Keep the helper 1:1 user-driven: no automatic camera motion, target lock, predictive movement, or action timing automation.

## In-game validation status

Held Camera Swivel key behavior has been confirmed working in-game by the user. Remaining validation:

1. Bind a virtual right stick to Camera Swivel and measure camera rate at 10%, 25%, 50%, and 100% deflection. Confirm whether speed is proportional.
2. Test virtual right stick camera while KBM drives; observe prompt switching and frame rate.
3. Test Season 24 free look with mouse and controller: threshold, unlatching, centre dot, deadzone, inversion parity, overtime, and Look at Ball behavior.
4. Compare mouse-axis direct binding while moving vs stopped to confirm constant-speed/reset behavior.
5. Confirm SendInput held Camera Swivel keys with Free Look off in a private match with EAC enabled before any online use.
6. Measure end-to-end latency with high-frame-rate capture once a test game is available.

## Known unknowns

- No authoritative proof that Rocket League maps analogue magnitude to swivel speed.
- No authoritative proof that virtual controller right stick and KBM driving coexist cleanly in current builds.
- No official approval of input remappers or synthetic OS input.
- No end-to-end latency measurement.
- No virtual gamepad backend yet.

## References

- Rocket League S24 patch notes: https://www.rocketleague.com/news/rocket-league-s24-patch-notes-v276
- Rocket League Season 24 announcement: https://www.rocketleague.com/news/rocket-league-heads-to-the-streets-in-season-24
- Rocket League Known Issues: https://www.rocketleague.com/known-issues
- Rocket League Code of Conduct: https://www.rocketleague.com/code-of-conduct
- Epic Community Rules: https://legal.epicgames.com/epicgames/community-rules
- Epic Terms of Service: https://legal.epicgames.com/epicgames/tos
- EAC announcement: https://www.rocketleague.com/news/easy-anti-cheat-comes-to-rocket-league-on-pc-today
- Steam Input developer guide: https://partner.steamgames.com/doc/features/steam_controller/getting_started_for_devs
- Steam Input gamepad emulation: https://partner.steamgames.com/doc/features/steam_controller/steam_input_gamepad_emulation_bestpractices
- Steam Input source modes: https://partner.steamgames.com/doc/features/steam_controller/input_source_modes
- Microsoft Raw Input: https://learn.microsoft.com/en-us/windows/win32/inputdev/about-raw-input
- Microsoft RegisterRawInputDevices: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerrawinputdevices
- Microsoft SendInput: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
- RLBot issue #21: https://github.com/RLBot/RLBot/issues/21
- PCGamingWiki Rocket League: https://www.pcgamingwiki.com/wiki/Rocket_League
- Rocket Science known issues: https://rocketscience.fyi/know/rl/issues
- LuminalVGBus: https://github.com/NortheBridge/LuminalVGBus
- rlm2c: https://github.com/bozbez/rlm2c
