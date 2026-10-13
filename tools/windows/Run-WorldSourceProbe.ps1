#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$CrashDisc,
    [ValidateRange(15,80)][int]$Seconds = 60,
    [switch]$CheckOnly,
    [switch]$VisibleOperatorWindow
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root = Join-Path $repo '.cache/m42-g1'
$m41BaselineRoot = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M41B2-texture'
$m3BaselineRoot = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose'
if (Test-Path -LiteralPath (Join-Path $m41BaselineRoot 'sealed-host.json')) {
    $baselineRoot = $m41BaselineRoot
    $baselineKind = 'M41B2'
    $sealPath = Join-Path $baselineRoot 'sealed-host.json'
} elseif (Test-Path -LiteralPath (Join-Path $m3BaselineRoot 'observer-build.json')) {
    $baselineRoot = $m3BaselineRoot
    $baselineKind = 'M3'
    $sealPath = Join-Path $baselineRoot 'observer-build.json'
} else {
    throw 'Require a sealed M41B2 or M3 private Crash baseline'
}
$baseline = Join-Path $baselineRoot 'app'
$m0 = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0'
$fusionRoot = (Split-Path $m0 -Parent) + [IO.Path]::DirectorySeparatorChar
$python = 'C:/msys64/mingw64/bin/python.exe'
$disc = (Resolve-Path -LiteralPath $CrashDisc).Path
$allowedDiscRoots = @()
foreach ($candidate in @((Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/owned'), (Join-Path $env:USERPROFILE 'Downloads'))) {
    if (Test-Path -LiteralPath $candidate -PathType Container) {
        $allowedDiscRoots += (Resolve-Path -LiteralPath $candidate).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
    }
}
$discIsPrivate = $false
foreach ($allowedRoot in $allowedDiscRoots) {
    if ($disc.StartsWith($allowedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        $discIsPrivate = $true
    }
}
if (-not $discIsPrivate -or [IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue', '.chd')) {
    throw 'Use an existing local owned or Downloads Crash disc; media is never copied by this runner'
}
if ([IO.Path]::GetExtension($disc).ToLowerInvariant() -eq '.cue') {
    $discDirectory = [IO.Path]::GetFullPath((Split-Path -Parent $disc)).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $trackNames = @(Get-Content -LiteralPath $disc | ForEach-Object {
        if ($_ -match '^\s*FILE\s+(?:"([^"]+)"|(\S+))\s+(?:BINARY|MOTOROLA)\s*$') {
            if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
        }
    })
    if (-not $trackNames.Count) { throw 'Crash CUE has no supported local data track' }
    foreach ($trackName in $trackNames) {
        $track = Join-Path $discDirectory $trackName
        if (-not (Test-Path -LiteralPath $track -PathType Leaf)) { throw 'Crash CUE references a missing local track' }
        $resolvedTrack = (Resolve-Path -LiteralPath $track).Path
        if (-not $resolvedTrack.StartsWith($discDirectory + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
            ((Get-Item -LiteralPath $resolvedTrack).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Crash CUE track must be a regular file beside its CUE'
        }
    }
}
foreach ($path in @((Join-Path $repo '.cache'), $root, $baseline)) {
    if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Private host roots must not be links'
    }
}
if (@(Get-ChildItem -LiteralPath $baseline -Recurse -Force | Where-Object {
    $_.Attributes -band [IO.FileAttributes]::ReparsePoint
}).Count) { throw 'Preserve linked baseline; cannot safely copy it' }
Push-Location $repo
try {
    & $python -m tools.prepare_world_source_probe --source (Join-Path $m0 'CrashBandicoot-Launcher') `
        --private-clone (Join-Path $root 'world-source-reviewed') --c1 (Join-Path $m0 'c1') `
        --libsm64 (Join-Path $m0 'libsm64') --verify-only
    if ($LASTEXITCODE -ne 0) { throw 'G1 private source or complete public pins drifted' }
} finally { Pop-Location }
$storedSeal = Get-Content -LiteralPath $sealPath -Raw | ConvertFrom-Json
if ($baselineKind -eq 'M3') {
    if ($storedSeal.pin -ne '224da7757920a817de2d9242416f657ab95782ea') {
        throw 'M3 baseline source pin mismatch'
    }
    $seal = [pscustomobject]@{
        public_pin = $storedSeal.pin
        original_exe = $storedSeal.hashes.'CrashBandicoot.exe'
        original_crash_dll = $storedSeal.hashes.'CrashBandicoot.dll'
        patched_runtime = $storedSeal.hashes.'RecompOne.Runtime.dll'
    }
} else {
    $seal = $storedSeal
}
$build = Get-Content -LiteralPath (Join-Path $root 'build-evidence.json') -Raw | ConvertFrom-Json
if ($seal.public_pin -ne $build.source_pin -or $build.positive_fixtures -ne 3 -or
    $build.negative_optout_fixtures -ne 20 -or $build.original_game_run -ne $false) {
    throw 'Unknown or untested G1 build'
}
function Assert-Hash([string]$Path, [string]$Expected) {
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) {
        throw "Private source/binary hash drift: $([IO.Path]::GetFileName($Path))"
    }
}
 $sealedFiles = @(@('CrashBandicoot.exe', $seal.original_exe), @('CrashBandicoot.dll', $seal.original_crash_dll),
    @('RecompOne.Runtime.dll', $seal.patched_runtime))
if ($baselineKind -eq 'M41B2') { $sealedFiles += ,@('sm64.dll', $seal.original_libsm64) }
foreach ($pair in $sealedFiles) {
    Assert-Hash (Join-Path $baseline $pair[0]) $pair[1]
}
Assert-Hash (Join-Path $repo 'integration/embedded_mario/CrashWorldSourceProbe.cs') $build.probe_sha256
$runtime = Join-Path $root 'runtime/RecompOne.Runtime.dll'
Assert-Hash $runtime $build.runtime_sha256
$slots = @(Get-ChildItem -LiteralPath (Join-Path $baseline 'game') -Directory | Where-Object {
    (Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json')) -and
    (Test-Path -LiteralPath (Join-Path $_.FullName 'game.recomp.dll'))
})
if ($slots.Count -ne 1) { throw 'Require exactly one previously prepared original private game slot' }
$manifest = Get-Content -LiteralPath (Join-Path $slots[0].FullName 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.PipelineVersion -ne '8' -or $manifest.Fingerprint -ne $slots[0].Name -or
    [IO.Path]::GetFullPath($manifest.CuePath) -ne $disc -or
    -not [IO.Path]::GetFullPath($manifest.DllPath).StartsWith($fusionRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Prepared original game/disc provenance mismatch; never regenerate the game'
}
$guestHash = (Get-FileHash -LiteralPath $manifest.DllPath -Algorithm SHA256).Hash.ToLowerInvariant()
Assert-Hash (Join-Path $slots[0].FullName 'game.recomp.dll') $guestHash
if ($CheckOnly) { Write-Output "G1_RUN_PREFLIGHT_OK baseline=$baselineKind no_game_started=true"; return }
$run = Join-Path $root ('original-' + [guid]::NewGuid().ToString('N'))
$app = Join-Path $run 'app'
New-Item -ItemType Directory -Path $app -Force | Out-Null
Get-ChildItem -LiteralPath $baseline -File | Where-Object { $_.Extension -in @('.dll', '.exe', '.json', '.ini') } |
    Copy-Item -Destination $app
foreach ($name in @('runtimes', 'Recomp', 'Ui')) {
    $path = Join-Path $baseline $name
    if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination (Join-Path $app $name) -Recurse }
}
$slot = Join-Path $app ('game/' + $manifest.Fingerprint)
New-Item -ItemType Directory -Path $slot -Force | Out-Null
Copy-Item -LiteralPath $manifest.DllPath -Destination (Join-Path $slot 'game.recomp.dll')
$manifest.DllPath = Join-Path $slot 'game.recomp.dll'
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $slot 'manifest.json') -Encoding utf8
Copy-Item -LiteralPath $runtime -Destination (Join-Path $app 'RecompOne.Runtime.dll') -Force
$settings = Get-Content -LiteralPath (Join-Path $app 'settings.json') -Raw | ConvertFrom-Json
$settings.CdPath = $disc; $settings.ActiveMods = @(); $settings.ModsConfigured = $true
$settings.AssetHotWatch = $false; $settings.Muted = $true
$settings | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $app 'settings.json') -Encoding utf8
Assert-Hash (Join-Path $app 'CrashBandicoot.exe') $seal.original_exe
Assert-Hash (Join-Path $app 'CrashBandicoot.dll') $seal.original_crash_dll
Assert-Hash $manifest.DllPath $guestHash
Assert-Hash (Join-Path $app 'RecompOne.Runtime.dll') $build.runtime_sha256
$stdout = Join-Path $run 'host.log'
$windowStyle = if ($VisibleOperatorWindow) { 'Normal' } else { 'Hidden' }
$process = Start-Process -FilePath (Join-Path $app 'CrashBandicoot.exe') -WorkingDirectory $app `
    -ArgumentList @('--run', ('"' + $disc + '"')) -WindowStyle $windowStyle `
    -Environment @{ CM64_WORLD_SOURCE_PROBE = '1'; CM64_EMBED_ENABLE = '0'; CM64_TEXTURE_ATLAS = '0';
        CM64_INOUTPUT = '0'; TEMP = $run; TMP = $run } `
    -RedirectStandardOutput $stdout -RedirectStandardError (Join-Path $run 'errors.log') -PassThru
$responsive = $false
try {
    Start-Sleep -Seconds $Seconds
    $process.Refresh()
    if (-not $process.HasExited) { $responsive = $process.Responding }
} finally {
    $process.Refresh()
    if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit(5000) | Out-Null }
}
if (-not $process.HasExited) { throw 'Owned native test process did not terminate' }
Push-Location $repo
try {
    & $python -m tools.assess_world_source_probe $stdout
    $accepted = $LASTEXITCODE -eq 0
} finally { Pop-Location }
@{ schema = 1; g1_candidate = $accepted; verified_real = $false; owned_pid = $process.Id;
    process_stopped = $process.HasExited; responsive = $responsive;
    input_sent = $(if ($VisibleOperatorWindow) { $null } else { $false });
    visible_operator_window = $VisibleOperatorWindow.IsPresent;
    overlay_enabled = $false; runtime_sha256 = $build.runtime_sha256; guest_sha256 = $guestHash;
    postphysics = $false; depth_complete = $false; collision_ready = $false } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'summary.json') -Encoding utf8
Write-Output "G1_ORIGINAL_ATTEMPT candidate=$accepted pid_stopped=true operator_window_visible=$($VisibleOperatorWindow.IsPresent) private_run=$run"
if (-not $accepted) { throw 'G1 BLOCKED: no audited in-level GTE/OT source receipts; operator input is not proof' }
