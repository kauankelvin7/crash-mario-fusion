#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_cache=/workspace/.cache/crash-mario-m0
export DOTNET_CLI_HOME="$task_cache/dotnet-home" NUGET_PACKAGES="$task_cache/nuget"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export LD_LIBRARY_PATH="$task_cache/mame/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p "$task_cache/logs"
cd "$task_root"
python -m unittest discover -s tests -v > "$task_cache/logs/bootstrap-tests.log" 2>&1
gcc -std=c11 -Wall -Wextra -Werror -UNDEBUG -I"$task_cache/libsm64/src" \
    tools/probe_libsm64.c -L"$task_cache/libsm64/dist" \
    -Wl,-rpath,"$task_cache/libsm64/dist" -lsm64 -lm -o "$task_cache/probe-libsm64"
"$task_cache/probe-libsm64" > "$task_cache/logs/libsm64-probe.log" 2>&1
cd "$task_cache/CrashBandicoot-Launcher"
"$task_cache/dotnet/dotnet" CrashBandicoot.Launcher/bin/Release/net10.0/CrashBandicoot.dll \
    --help > "$task_cache/logs/launcher-cli.log" 2>&1
"$task_cache/dotnet/dotnet" run --project tools/CrashBandicoot.DiscCheck -c Release \
    -- "$task_cache/mame/usr/bin/chdman" "$task_cache/disc-check" \
    > "$task_cache/logs/disc-check.log" 2>&1
cat "$task_cache/logs/bootstrap-tests.log" "$task_cache/logs/libsm64-probe.log" \
    "$task_cache/logs/disc-check.log"
echo "VERIFIED_SYNTHETIC: M0 checks passed. No real game or shared event executed."
