#!/usr/bin/env bash
# Source/dependency caches only; never fetch game data or modify project sources.
set -euo pipefail
task_cache=/workspace/.cache/crash-mario-m0
mkdir -p "$task_cache/logs"
fetch_source() {
    local repository=$1 revision=$2 directory="$task_cache/${1##*/}"
    if [[ ! -e "$directory" ]]; then
        git clone --depth 1 "https://github.com/$repository.git" "$directory"
        if [[ $(git -C "$directory" rev-parse HEAD) != "$revision" ]]; then
            git -C "$directory" fetch --depth 1 origin "$revision"
            git -C "$directory" checkout --detach "$revision"
        fi
    fi
    [[ $(git -C "$directory" rev-parse HEAD) == "$revision" ]] || {
        echo "Wrong cached revision: $directory; preserve local work before replacing it." >&2
        return 1
    }
    [[ -z $(git -C "$directory" status --porcelain) ]] || {
        echo "Dirty source cache: $directory; preserve and inspect changes." >&2
        return 1
    }
}
fetch_source rehan-remade/universal-modder 8370faa8e114baf33acdb23079aff552a7728c4b
fetch_source Matteo842/CrashBandicoot-Launcher 224da7757920a817de2d9242416f657ab95782ea
fetch_source wurlyfox/c1 256fdcef59f15a190290cc19db3fa9a707843b69
fetch_source n64decomp/sm64 9921382a68bb0c865e5e45eb594d9c64db59b1af
fetch_source sm64pc/sm64ex d7ca2c04364a6dd0dac58b47151e04e26887e6f0
fetch_source libsm64/libsm64 fd11813208272b4271d92bd92feb8f3fdbe61be5

if [[ ! -x "$task_cache/dotnet/dotnet" ]] ||
   [[ $("$task_cache/dotnet/dotnet" --version) != 10.0.401 ]]; then
    curl -fsSL https://dot.net/v1/dotnet-install.sh -o "$task_cache/dotnet-install.sh"
    bash "$task_cache/dotnet-install.sh" --version 10.0.401 \
        --install-dir "$task_cache/dotnet" --no-path
fi
export DOTNET_CLI_HOME="$task_cache/dotnet-home"
export NUGET_PACKAGES="$task_cache/nuget"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1

# Download through APT's signed metadata into writable directories; no sudo.
if [[ ! -x "$task_cache/mame/usr/bin/chdman" ]] ||
   [[ ! -e "$task_cache/mame/usr/lib/x86_64-linux-gnu/libutf8proc.so.3" ]]; then
    mkdir -p "$task_cache/apt/config" "$task_cache/apt/lists/partial" \
        "$task_cache/apt/archives/partial" "$task_cache/mame"
    printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main' \
        > "$task_cache/apt/config/sources.list"
    apt_options=(-o Dir::Etc::parts=- -o Dir::Etc::main=-
        -o "Dir::Etc::sourcelist=$task_cache/apt/config/sources.list"
        -o Dir::Etc::sourceparts=- -o "Dir::State::lists=$task_cache/apt/lists"
        -o "Dir::Cache::archives=$task_cache/apt/archives" -o Debug::NoLocking=true)
    apt-get "${apt_options[@]}" update
    (cd "$task_cache/apt" && apt-get "${apt_options[@]}" download mame-tools libutf8proc3)
    for package in "$task_cache"/apt/mame-tools_*.deb "$task_cache"/apt/libutf8proc3_*.deb; do
        dpkg-deb -x "$package" "$task_cache/mame"
    done
fi
export LD_LIBRARY_PATH="$task_cache/mame/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
chdman_status=0
"$task_cache/mame/usr/bin/chdman" help > "$task_cache/logs/chdman-version.log" 2>&1 || chdman_status=$?
# chdman documents help with exit 1; require its expected banner as well.
[[ $chdman_status == 0 || $chdman_status == 1 ]]
rg -q 'chdman - MAME Compressed Hunks of Data' "$task_cache/logs/chdman-version.log"
(cd "$task_cache/libsm64" && make -j2 lib) > "$task_cache/logs/libsm64-build.log" 2>&1
(cd "$task_cache/CrashBandicoot-Launcher" && "$task_cache/dotnet/dotnet" build \
    CrashBandicoot.Launcher -c Release -f net10.0 -p:TargetFrameworks=net10.0) \
    > "$task_cache/logs/launcher-build-linux.log" 2>&1
echo "M0 source caches and asset-free builds prepared. Run bash tools/m0-check.sh."
