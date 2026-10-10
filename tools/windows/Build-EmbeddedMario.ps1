#Requires -Version 7.0
<#
.SYNOPSIS
Prepare a private, opt-in Windows libsm64-in-Crash host experiment.
.DESCRIPTION
Copies only public-source runtime binaries from the sealed M3 launcher, and
builds libsm64 from the pinned local source. Owned ROM/disc are NOT copied.
#>
[CmdletBinding()]
param(
    [string]$MsysRoot = 'C:/msys64',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M4-embed'
$m0 = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0'
$m3 = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose'
$public = Join-Path $m0 'libsm64'
$private = Join-Path $root 'libsm64'
$app = Join-Path $root 'crash-app'
$sourceMod = Join-Path $repo 'integration/embedded_mario'
$expectedLib = 'fd11813208272b4271d92bd92feb8f3fdbe61be5'
$expectedCrash = '224da7757920a817de2d9242416f657ab95782ea'
$gcc = Join-Path $MsysRoot 'mingw64/bin/gcc.exe'
$bash = Join-Path $MsysRoot 'usr/bin/bash.exe'
$cygpath = Join-Path $MsysRoot 'usr/bin/cygpath.exe'
$dotnet = Join-Path $m0 'dotnet/dotnet.exe'
foreach ($file in @($gcc,$bash,$cygpath,$dotnet,
    (Join-Path $sourceMod 'embedded_probe.c'),
    (Join-Path $sourceMod 'CrashEmbeddedMarioMod.cs'),
    (Join-Path $sourceMod 'Interop.cs'),
    (Join-Path $sourceMod 'mod.json'))) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Missing required source/tool (no fallback download): $file"
    }
}
$pin = (& git -C $public rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $pin -ne $expectedLib -or
    (& git -C $public status --porcelain)) { throw 'Dirty or wrong public libsm64 upstream pin' }
$manifestPath = Join-Path $m3 'observer-build.json'
$sealedApp = Join-Path $m3 'app'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.pin -ne $expectedCrash) { throw 'Wrong public Crash source pin' }
foreach ($name in @('CrashBandicoot.exe','CrashBandicoot.dll','RecompOne.Runtime.dll')) {
    $file = Join-Path $sealedApp $name
    $sha = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sha -ne $manifest.hashes.PSObject.Properties[$name].Value) {
        throw "Sealed Crash original host changed: $name"
    }
}
if ($CheckOnly) {
    Write-Output 'EMBED_PREFLIGHT_OK public_libsm64_pin=true crash_host_sealed=true source_only=true original_game_NOT_TESTED'
    return
}
New-Item -ItemType Directory -Force $root | Out-Null
if (-not (Test-Path -LiteralPath $private)) {
    & git clone --no-hardlinks $public $private | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Local private libsm64 clone failed' }
}
if ((& git -C $private rev-parse HEAD).Trim() -ne $expectedLib) {
    throw 'Unknown existing private libsm64 cache; preserve it'
}
$privatePosix = (& $cygpath -u $private).Trim()
$repoPosix = (& $cygpath -u $repo).Trim()
$probePosix = (& $cygpath -u (Join-Path $root 'probe')).Trim()
foreach ($name in @($privatePosix,$repoPosix,$probePosix)) {
    if ($name.Contains("'")) { throw 'Unsupported apostrophe in private source path' }
}
New-Item -ItemType Directory -Force (Join-Path $root 'probe') | Out-Null
$script = "export PATH=/mingw64/bin:/usr/bin; cd '$privatePosix'; make -j4 OS=Windows_NT lib"
& $bash -lc $script
if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $private 'dist/sm64.dll'))) {
    throw 'Native Windows x64 libsm64 build failed'
}
$build = "export PATH=/mingw64/bin:/usr/bin; gcc -std=c11 -O2 -Wall -Wextra -I '$privatePosix/src' '$repoPosix/integration/embedded_mario/embedded_probe.c' '$privatePosix/dist/sm64.dll' -lm -o '$probePosix/embedded_probe.exe'"
& $bash -lc $build
if ($LASTEXITCODE -ne 0) { throw 'Native original Mario C ABI probe build failed' }
Copy-Item -LiteralPath (Join-Path $private 'dist/sm64.dll') -Destination (Join-Path $root 'probe/sm64.dll') -Force
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
& $dotnet build (Join-Path $sourceMod 'EmbeddedMarioProbe.csproj') -c Release -o (Join-Path $root 'dotnet-probe') -v quiet
if ($LASTEXITCODE -ne 0) { throw 'C# x64 embedded ABI probe build failed' }
Copy-Item -LiteralPath (Join-Path $private 'dist/sm64.dll') -Destination (Join-Path $root 'dotnet-probe/sm64.dll') -Force
$env:PATH = (Join-Path $MsysRoot 'mingw64/bin')+';'+$env:PATH
& $dotnet (Join-Path $root 'dotnet-probe/EmbeddedMarioProbe.dll') --abi-only
if ($LASTEXITCODE -ne 0) { throw 'Native C# ABI size/layout gate failed' }
if (-not (Test-Path -LiteralPath $app)) {
    Copy-Item -LiteralPath $sealedApp -Destination $app -Recurse
}
# Never modify sealed M3 source; the new host copy must remain fingerprint identical.
foreach ($name in @('CrashBandicoot.exe','CrashBandicoot.dll','RecompOne.Runtime.dll')) {
    $sha = (Get-FileHash -LiteralPath (Join-Path $app $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sha -ne $manifest.hashes.PSObject.Properties[$name].Value) {
        throw "Existing private Crash embed app is unknown: $name"
    }
}
$settingsPath = Join-Path $app 'settings.json'
$settings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
$active = @($settings.ActiveMods)
if ($active.Count -gt 0 -and
    -not ($active.Count -eq 1 -and $active[0] -in @('cm64-crash-pose','cm64-embedded-mario'))) {
    throw 'Existing private embedded host has unexpected active mods; preserve it'
}
$destMod = Join-Path $app 'mods/cm64-embedded-mario'
New-Item -ItemType Directory -Force $destMod | Out-Null
foreach ($name in @('Interop.cs','CrashEmbeddedMarioMod.cs','mod.json')) {
    Copy-Item -LiteralPath (Join-Path $sourceMod $name) -Destination (Join-Path $destMod $name) -Force
}
$settings.ModsConfigured=$true
$settings.ActiveMods=@('cm64-embedded-mario')
$settings | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $settingsPath -Encoding utf8
Copy-Item -LiteralPath (Join-Path $private 'dist/sm64.dll') -Destination (Join-Path $app 'sm64.dll') -Force
$hash = (Get-FileHash -LiteralPath (Join-Path $app 'sm64.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
$buildManifest = @{
    libsm64_pin=$expectedLib
    crash_pin=$expectedCrash
    dll_sha256=$hash
    source_hashes=@{}
}
foreach ($name in @('Interop.cs','CrashEmbeddedMarioMod.cs','mod.json')) {
    $buildManifest.source_hashes[$name] = (Get-FileHash -LiteralPath (Join-Path $sourceMod $name) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$buildManifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $root 'embedded-build.json') -Encoding utf8
Write-Output 'EMBED_PRIVATE_BUILD_OK DLL=Windows_x64 crash_app=isolated_one_mod rom_copied=false original_game_NOT_TESTED'
