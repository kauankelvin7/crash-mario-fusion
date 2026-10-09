#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cache=/workspace/.cache/crash-mario-m0
prepared=/workspace/.cache/crash-mario-integration/sm64ex
mkdir -p "$repo/.cache/integration" "$cache/logs"
cd "$repo"
python tools/prepare_integration.py --source "$cache/sm64ex" --output "$prepared"
# Compile the actual patched native interaction translation unit without extracted assets.
(cd "$prepared" && gcc -c -DVERSION_US -D_LANGUAGE_C -DNON_MATCHING -DAVOID_UB \
    -fno-strict-aliasing -fwrapv -Iinclude -Isrc -I. src/game/interaction.c \
    -o "$repo/.cache/integration/native-interaction.o")
nm -u "$repo/.cache/integration/native-interaction.o" | rg 'cm64_coin'
gcc -std=c11 -Wall -Wextra -Werror -Iintegration/sm64 \
    integration/sm64/cm64_coin.c tests/integration/native_sender.c \
    -o "$repo/.cache/integration/native-coin-sender"
export DOTNET_CLI_HOME="$cache/dotnet-home" NUGET_PACKAGES="$cache/nuget"
export DOTNET_CLI_TELEMETRY_OPTOUT=1
"$cache/dotnet/dotnet" run --project tests/integration -- \
    "$repo" "$repo/.cache/integration/native-coin-sender" \
    > "$cache/logs/integration-checks.log" 2>&1
cat "$cache/logs/integration-checks.log"
