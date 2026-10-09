# Native coin → native Crash input, v1

Runtime bases remain the M0 pins: full sm64ex `d7ca2c0`, Crash Launcher `224da77`. This is a narrow event adapter, not shared-world collision/rendering. Each original runtime owns physics, objects, camera, saves and event consequences.

The authored hook runs at the end of native `interact_coin`, after coin/healing/interact-status/star logic. It observes value-1 pickups outside demos, exporting `gGlobalTimer`, native coin count and Mario position. The counter is an SM64 observation counter; no equivalence with Crash simulation/presentation ticks is assumed. No axis/scale transformation or position write occurs.

Transport: one nonblocking UDP datagram to IPv4 loopback. Fixed 52-byte **CMJ1** packet: magic[4], fresh run nonce[16], sequence u32, native counter u32, coin count i32, three f32 positions, Unix milliseconds i64. Numbers use big endian; floats use IEEE binary32. Start order: Crash receiver readiness, then Mario. New nonce on every paired start. Lost packets are logged/dropped; no retry/backlog/replay guarantee. Session/length/finite values/sequence are checked; age >250 ms or >100 ms in the future is rejected. Up to 32 packets drained per port-0 controller callback, with no worker thread or game-thread waiting.

Default is observation only. With `-Apply`, HOLD physical Crash R1 during **unpaused** known gameplay to permit input. Native Cross must be released. One event generates a 100-ms active-low Cross pulse followed by a 100-ms cooldown; physical input resumes afterward. Ineligible, expired, duplicate, other-session or busy events are consumed, not queued. Title/cinema/unknown levels and a Start press cannot inject; level change/unarming cancels the pulse. Port 1 is unchanged. Native pause/grounded/player-pose observation is still missing: the gate is not a full pause detector, and `input_applied` never proves a jump/landing. Do not arm during pause, loading, death or menus. R1 itself is left unchanged, so its native effects remain possible.

Crash state accessed: level id via its public catalog and controller word via its public pad bus. Mario state accessed: native interaction arguments. No native Crash position or object behavior is guessed. Unload unregisters the handler and closes the socket. The runner stops only the two processes it starts; local game files/config/logs never enter project Git.

Real oracle: baseline and observe-only pickup retain identical coin/healing/sparkle/deletion behavior. Then one pickup, one matching sequence in both logs, one input application, plus actual native Crash ground→jump→landing evidence on Windows. Logs/packet tests alone are insufficient. Shared camera/geometry/collision and combined input ownership are outside this event; two separate windows remain.
# M3 read-only world-coordinate preflight (2026-10-09)

`tools/world_coordinates.py` consumes the real adapter's `motion_sample` XYZ log
and an explicit private calibration. It does not emit UDP, write memory, load
geometry or replace collision/physics. CMJ1 remains unchanged. Old Y-only logs
are rejected instead of fabricating XZ.

Crash NTSC-U signed int32 translation XYZ is at object `+0x80/+0x84/+0x88`.
Decode to fractional native view units with `raw / 256`; the pinned Launcher's
`FramePacing.CameraTrace.cs:92–94` displays `raw >> 8`, which truncates that
precision. `FramePacing.cs:347` defines `ObjTransOff`. The c1 reference
`src/pc/gfx/soft.c:291–294` independently shifts camera-relative translation
by 8 before rotation. These units imply no meters or cross-game scale.
Mario `Vec3f pos` (`include/types.h`, `MarioState`) and CMJ1 XYZ are native f32.

Chosen reversible mapping: `mario = mario_origin + scale * Ry(yaw) *
(crash_raw/256 - crash_origin)`, with positive uniform scale and Y unchanged
by yaw; `Ry` maps XZ to `(cos(yaw)*X + sin(yaw)*Z,
-sin(yaw)*X + cos(yaw)*Z)`. Inverse removes translation/scale
and applies negative yaw. This preserves up and triangle winding within the
selected frame. Native basis alignment is a calibration input, not verified
cross-engine alignment. Result is quantized to f32 and rejected if inverse
error exceeds `1/512` Crash native view unit on any axis. This prevents silent
underflow or precision collapse; it does not promise globally exact f32 mapping.

Private calibration JSON fields: `schema_version: 1`, `crash_level` (integer),
`mario_frame` (operator-confirmed level/area label), `crash_origin` and
`mario_origin` (three native view/world numbers each), `scale` (positive),
`yaw_degrees` (finite). No default scale/origin exists. Use explicitly chosen
world-placement landmarks; distance ratios determine scale, XZ directions
determine yaw. Record how the correspondence was chosen locally. Neither
existing M2 data nor unit decoding establishes those correspondences.
Crash level mismatches abort. Mario area identity is operator supplied and
not runtime verified; changing either area requires a new calibration.

`floor_query_safe` checks only conservative native query bounds: open X/Z
`(-8192,8192)` and Y `[-32768,32767]`, before signed-16 casts. Grounding:
pinned sm64ex `src/engine/surface_collision.h:8` and `surface_collision.c`
`find_floor` (XYZ s16 casts and XZ bounds); `Surface.vertex1/2/3` are Vec3s.
A safe coordinate does not imply any floor or shared collision exists.

## CMW1 native snapshot prototype (separate from CMJ1)

`integration/world_snapshot.py` serializes observations only; no runtime pose
emitter, socket listener, collision command or memory writer is installed.
Wire header is network-endian `4s BB H 16s 16s II`: magic `CMW1`, engine
(1 Crash / 2 Mario), phase, flags (bit 0 paused; other bits rejected), session,
frame generation, sequence and native tick. Both identities are explicit
nonzero 16-byte values. Sequence must increase; renew session before u32 wrap.
Native tick is u32 and may wrap independently; never compare engines' ticks.

| Payload | Position | Rotation | State / flags | Total bytes |
| --- | --- | --- | --- | --- |
| Crash | 3 signed i32 raw translation | 3 signed i32 raw rotation | 2 u32, opaque | 80 |
| Mario | 3 finite f32 native XYZ | 3 signed i16 `faceAngle` | 2 u32, opaque | 74 |

Source types: Launcher `FramePacing.cs:347–348` translation/rotation offsets;
sm64ex `include/types.h` `MarioState.pos`, `faceAngle`, `action`, `flags`.
No common degrees/radians, action IDs, state masks or velocities are invented.
Candidate phase tags: 1 post Mario update, 2 post Crash physics, 3 pre Crash
GPU. Source emission timing and native tick acquisition still need actual
instrumentation; tags do not prove a coherent gameplay snapshot.

`SnapshotStore` binds both reviewed frame generations at construction and keeps
at most two latest observations, rejecting duplicates/out-of-order sequences,
foreign sessions/frames, malformed lengths, unknown flags and nonfinite values.
Paused/expired observations are unavailable; there is no interpolation,
extrapolation, replay queue or remote physics authority. A new zone/area/object
generation requires explicit invalidation/rebinding, not pointer identity.
Freshness bounds receiver-local elapsed time since arrival. **It cannot detect
delay before receipt, synchronize clocks, or prove source capture freshness.**
Session matching is not cryptographic authentication. Live use remains gated
on source-frame identities, coherent sampling, loss/load/pause observations
and local-only transport; CMJ1 gameplay behavior remains unchanged.

## M3.1 opt-in Mario-only CMW1 native emitter (2026-10-09)
The separate CMW1 observer uses the documented fixed header and payload (74 bytes total) without changing CMJ1. Mario emitter source integration/sm64/cm64_pose.c runs from private pinned sm64ex post-update level and area lifecycle hooks when normal native gameplay is valid; opt-in requires CM64_POSE_ENABLE=1, CM64_POSE_SESSION fresh nonzero 16-byte hex, CM64_POSE_PORT a numeric localhost UDP port 1024..65535. Disabled by default. Receiver controls private session generation; max 10 Hz, 300 s or 3000 accepted source emissions. No queue or retries. Original player inputs, movement, rendering and collisions are not modified.

CMW1 frame bytes [24..39] are M31A (4 bytes), native Mario signed s16 level and signed s16 area (2+2), reserved zero u32 (4), and an observer-local u32 epoch (4). Epoch increments on invalidation and area changes. This descriptor is an instrumentation contract, NOT a verified native engine frame-generation counter; input area transitions invalidate old observations. The existing sequence, engine-local tick, XYZ, 3 signed angles, state/action/flags follow the existing CMW1 layout. No inter-engine clock alignment or spatial transform is inferred. Collector accepts only an exact-session, monotonic sequence/epoch and validated finite bytes on IPv4 loopback and marks calibration_ready=false. Original continuous Crash pose sender is still NOT IMPLEMENTED. New Mario game execution remains NOT_TESTED (synthetic C tests plus successful native Windows link only).

## M3.2 Crash-only opt-in diagnostic CMW1 — source contract and restrictions
CMW1 Crash observations from RecompOne PadReadEvent use engine=1, **phase=0 UNKNOWN_DIAGNOSTIC** (neither verified POST_CRASH_PHYSICS nor PRE_CRASH_GPU). The phase zero addition to integration/world_snapshot.py is exclusive to Crash, while Mario remains phase=1 POST_MARIO_UPDATE; existing synthetic phases 2/3 retain prior meaning. Do not interpret the Crash native_tick header as real Crash game frame: it is an observer-only callback ordinal. The frame 16-byte descriptor is struct big-endian M32D (4 ASCII bytes), original Crash native level uint32, observer-local epoch uint32, reserved zero uint32; no native zone ID or genuine engine lifecycle generation proved. Each live run uses a fresh nonzero 16-byte session, never shared across runs. Payload includes native signed int32 XYZ (object offsets +0x80/+0x84/+0x88), signed int32 native raw rotation (+0x8c/+0x90/+0x94), uint32 opaque state (+0x2c) and flags (+0x120). This is signed raw data, NOT translated world units.
Independent local UDP emitter is disabled unless CM64_CRASH_POSE_ENABLE=1 and fresh CM64_CRASH_POSE_SESSION+CM64_CRASH_POSE_PORT are provided. Loopback-only, nonblocking, <=10Hz, <=300s, <=3000 attempts, no replay/catchup, no gameplay memory/input mutation. Pointer bounds, native gameplay level, native pause flags, Start request and valid object lifecycle signature are checked before observation; invalid contexts suppress packets and invalidate observer epoch. Private collector validates signed CMW1 packet, phase/session/replay/frame/freshness, enforces finite local child/process and writes only outside repo; it is NOT a world calibration or live gameplay validation tool. CMJ1 Mario coin->Crash event transport remains unchanged and separate. No shared collider or renderer exists.

## Issue #5 — observational CMW1 correlation and offline landmark fit

`integration/observation_alignment.py` wraps `SnapshotStore` with exactly two
pose slots and fixed per-engine rejection/sequence metadata. Bind **each**
capture session and frame explicitly using `Binding(session, frame)`; they may
be entirely different across engines. An explicit `receiver_clock_id` identifies
one monotonic receiver clock for `accept(packet, receive_ns, ...)` and
`evaluate(now_ns, ...)`. It is a caller assertion, not clock discovery: **do not
feed timestamps from the two existing independent collectors as one clock**.
No wall-clock or native-tick arithmetic is performed. Tick wraps are harmless;
CMW1 sequence wrap requires a fresh capture session. `receiver_arrival_separation_ns`
is only the distance between local receipt stamps, never latency/physics skew.

Only current Crash phase 0 / Mario phase 1 observations can be telemetry-comparable.
`Comparison` always has `physical_status="BLOCKED"`, `calibration_ready=False`.
Malformed, session, phase, replay, frame, missing, paused, gap, timeout, clock
regression and clock-domain rejection reasons are structured. Pause, a newer or
contradictory frame, and a gap invalidate that source until explicit `rebind`.
Same-session rebinding requires a newer observer epoch and retains the sequence
high-water mark; a fresh session resets it. Old epochs do not displace a valid
newer binding. Epochs are observer-local, **not** certified native generations.
Age is explicitly bounded to 1..1,000,000,000 ns; gap to age..300,000,000,000 ns.
No queue, extrapolation, socket, game writes or automatic frame matching.
`SnapshotStore` still accepts its old shared-session constructor and unchanged
80/74-byte CMW1 wire format; it additionally accepts per-engine session bindings.

`tools/estimate_calibration.py` consumes <=128 **explicitly declared** landmark
pairs, <=128 KiB JSON. Each pair requires a unique label, signed-int32 Crash
XYZ, Mario XYZ, Crash level/observer epoch, Mario level/area/observer epoch,
provenance and `correspondence_declared=true`. All fit and holdout pairs must
share the same per-engine scope and provenance. Names never establish matching.
Use `SYNTHETIC` or `OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED`; neither is runtime
calibration evidence. FitPolicy requires every tolerance explicitly: maximum/RMS
Euclidean Mario-unit residual, source/target minimum XZ baseline, XZ covariance
minimum eigenvalue ratio, target float32 absolute-error limit, and holdout policy.
No real-world scale, yaw or tolerance is supplied by default.

For centered Crash points c and Mario points m, define
A=sum(cx*mx+cz*mz), B=sum(cz*mx-cx*mz), C=sum(cy*my), D=sum(|c|²).
The least-squares Y-yaw is atan2(B,A), and uniform scale is
(hypot(A,B)+C)/D. FrameMap origins are the two centroids. This uses the existing
convention X'=cos(yaw)X+sin(yaw)Z, Z'=-sin(yaw)X+cos(yaw)Z;
Y contributes to scale, but cannot replace three well-conditioned, noncollinear
XZ fit pairs. Nonpositive scale, undefined yaw, duplicates, weak baseline or
conditioning fail closed. Every supplied pair is checked; outliers are never
silently trimmed. Holdout points never participate in fitting and are checked
separately against the same maximum/RMS limits. Omitting holdout requires an
explicit policy opt-out and adds an unresolved gate.

Checks model actual Mario float32 inputs/outputs, half-Crash-raw-unit inverse
loss, signed Crash fixed-point inverse range, and conservative open Mario
XZ (-8192,8192) / Y s16 bounds. These are coordinate query bounds, **not** a
native geometry converter or a floor/collision result. Residuals compare against
float32 targets; input and output quantization errors are separately bounded.
No geometry is inserted and no solver is called by the estimator.

Reproducible mathematical example:
`python -m tools.estimate_calibration --input tests/fixtures/calibration_landmarks_synthetic.json`.
Authored scale=2, yaw=90°, translation=(10,20,-30), three fit pairs and two distinct
holdouts recover zero float32 residuals. Output is
`SYNTHETIC_MATH_ESTIMATE_ONLY`, `calibration_ready=false`, `physical_status=BLOCKED`.
Operator data instead returns `OPERATOR_SUPPLIED_NOT_RUNTIME_VERIFIED` with the
same gates: Crash postphysics, native frame identity, runtime correspondence,
and shared collisions/gameplay remain unverified. Keep operator inputs private.
