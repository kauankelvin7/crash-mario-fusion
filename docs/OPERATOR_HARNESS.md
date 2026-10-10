# Local Windows operator harness

`tools/windows/operator_harness.py` is a bounded keyboard helper for exactly
the visible `CrashBandicoot.exe` and `sm64.us.f3dex2e.exe` process windows. It
does not launch, modify, instrument, or inspect game memory. It uses only
Windows user-mode APIs and Python's standard library.

```powershell
python tools/windows/operator_harness.py mario
python tools/windows/operator_harness.py mario --action jump --vk 0x20
python tools/windows/operator_harness.py mario --action jump --vk 0x20 --seconds 0.2 --execute
python tools/windows/operator_harness.py crash --capture-client
```

Dry-run is the default. `--execute` is required to send a key. The operator
must supply `--vk` from the game's local control settings: the pinned sm64ex
keyboard implementation maps configurable scancodes from `configKeyStick*`,
`configKeyA`, and `configKeyStart`; Crash controls are configurable too, so
the harness deliberately does not guess key bindings. Actions are limited to
up/down/left/right/jump/menu and a hold from greater than zero through five
seconds. Press Escape in the console to abort. Before each action, throughout
the hold, and before a client capture, the helper rechecks that there is exactly
one visible matching executable window and that it remains foreground. Window,
PID and full process-image path must remain consistent. Focus changes halt
further key-down activity; key-up is always attempted to avoid a stuck key.

`--capture-client` uses `PrintWindow(PW_CLIENTONLY)` and writes only the target
client surface as BMP beneath `%LOCALAPPDATA%\CrashMarioFusion\operator-captures`.
The file is created exclusively and never written to the repository. Review
local Windows privacy/ACL policy before capture. Screenshots and any existing
telemetry remain local; never upload game files, screenshots, configs, logs,
tokens, or raw telemetry. This helper does not call or replace existing
telemetry collectors and reports no gameplay outcome. A sent input is not
proof that a game accepted it or that any movement, jump, landing, or
postphysics event occurred.

Source-only deterministic tests (no Windows APIs or games launched):

```powershell
python -m unittest tests.test_windows_operator_harness
```

These source-only tests cannot prove original gameplay. The helper uses
`PostMessageW` targeted to the currently verified game HWND, **not** global
`SendInput`. It verifies the process owner/path, tries to foreground only that
window, confirms focus, limits held keys to five seconds, and releases keys
even on focus-loss or operator abort. If Windows refuses focus, it stops.

## Native Windows operator experiment (2026-10-09)

On the authorized local Windows PC, the user-approved tests reached real
playable game scenes without manual input:
- Mario: targeted Start (Space), file A (L), tutorial confirmation (L), then
  held W for 1.5 s. Private window screenshots show Mario advancing from
  the sandy castle entrance onto grass, with the native camera moving.
- Crash: targeted Enter from the title menu, then Z from the island screen,
  entering **Sanity Beach**. The tested Python harness sent VK_UP for 0.8 s;
  private client-only screenshots show Crash advancing forward between crates.
- Win32 client capture, exact executable-window identity, fail-closed keyboard
  and focus checks were exercised locally. The 8 isolated operator tests pass.

Example stock bindings for reproduction (verify local settings first):

```powershell
python tools/windows/operator_harness.py mario --action up --vk 0x57 --seconds 1 --execute
python tools/windows/operator_harness.py crash --action up --vk 0x26 --seconds 0.8 --execute --capture-client
```

**Evidence scope:** VERIFIED_REAL graphical movement and controller input only.
These standalone GUI actions were not simultaneously timestamped against fresh
CMW1 packets; postphysics Crash frame ownership, shared coordinate calibration,
collision and a playable fused world remain BLOCKED. All visual files remain
private in LOCALAPPDATA; never commit or upload them.
