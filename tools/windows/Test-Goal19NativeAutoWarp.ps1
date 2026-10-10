#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$MarioRom,
    [Parameter(Mandatory)][string]$CrashDisc,
    [ValidateRange(30,120)][int]$Seconds = 100,
    [switch]$CheckOnly,
    [switch]$ApproveHumanRun
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$cache = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion'
$base = Join-Path $cache 'M43-input/app'
$app = Join-Path $cache 'M44-native-warp/app'
$seal = Get-Content (Join-Path $cache 'M43-input/sealed-live.json') -Raw | ConvertFrom-Json
if ($seal.schema -ne 1 -or $seal.source.pin -ne '224da7757920a817de2d9242416f657ab95782ea') {
    throw 'Expected pinned, sealed original private M43 source'
}
foreach ($entry in $seal.hashes.PSObject.Properties) {
    $file = Join-Path $base $entry.Name
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
        throw 'Sealed original M43 host was altered'
    }
}
foreach ($entry in $seal.mods.PSObject.Properties) {
    $file = Join-Path $base ('mods/cm64-embedded-mario/' + $entry.Name)
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
        throw 'Sealed original M43 source mod was altered'
    }
}
$rom = (Resolve-Path -LiteralPath $MarioRom).Path
$disc = (Resolve-Path -LiteralPath $CrashDisc).Path
$owned = (Resolve-Path -LiteralPath (Join-Path $cache 'owned')).Path
if ((Get-Item -LiteralPath $rom).Length -ne 8388608 -or
    (Get-FileHash -LiteralPath $rom -Algorithm SHA1).Hash.ToLowerInvariant() -ne '9bef1128717f958171a4afac3ed78ee2bb4e86ce') {
    throw 'Only the locally owned, source-pinned Mario ROM is allowed'
}
if (-not $disc.StartsWith($owned + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase) -or
    [IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue','.chd')) {
    throw 'Only the owned private Crash disc is allowed'
}
$python = 'C:/msys64/mingw64/bin/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'MSYS2 Python unavailable' }
foreach ($name in @('CrashEmbeddedMarioMod.cs','LiveMarioControls.cs')) {
    if (-not (Test-Path -LiteralPath (Join-Path $repo "integration/embedded_mario/$name"))) {
        throw 'GOAL19 native auto-warp source missing'
    }
}
Push-Location $repo
try {
    & $python -m tools.m43_live_gate --source (Join-Path $cache 'M0/CrashBandicoot-Launcher') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Public pinned source contract failed' }
} finally { Pop-Location }
if ($CheckOnly) {
    Write-Output 'GOAL19_AUTOWARP_PREFLIGHT_OK original_game_not_started=true collision=false'
    return
}
if (-not $ApproveHumanRun) { throw 'Explicit -ApproveHumanRun required' }
$mutex = [Threading.Mutex]::new($false,'Local\CrashMarioFusion-OriginalGame')
$locked = $false
try {
    $locked = $mutex.WaitOne(0)
    if (-not $locked -or @(Get-Process -Name 'CrashBandicoot*' -ErrorAction SilentlyContinue).Count) {
        throw 'Another original Crash host is running'
    }
    if (-not (Test-Path -LiteralPath $app)) {
        New-Item -ItemType Directory -Force -Path $app | Out-Null
        Copy-Item -Path (Join-Path $base '*') -Destination $app -Recurse -Force
        foreach ($name in @('CrashEmbeddedMarioMod.cs','LiveMarioControls.cs')) {
            Copy-Item (Join-Path $repo "integration/embedded_mario/$name") -Destination (Join-Path $app 'mods/cm64-embedded-mario') -Force
        }
        $settings = Get-Content (Join-Path $app 'settings.json') -Raw | ConvertFrom-Json
        $settings.AssetHotWatch = $false
        $settings.CatalogDiscovery = $false
        $settings | ConvertTo-Json -Depth 8 |
            Set-Content (Join-Path $app 'settings.json') -Encoding utf8
    }
    foreach ($entry in $seal.hashes.PSObject.Properties) {
        if ($entry.Name -eq 'settings.json') { continue }
        if ((Get-FileHash -LiteralPath (Join-Path $app $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
            throw 'Private diagnostic host binary drift'
        }
    }
    foreach ($name in @('CrashEmbeddedMarioMod.cs','LiveMarioControls.cs')) {
        $expected = (Get-FileHash (Join-Path $repo "integration/embedded_mario/$name") -Algorithm SHA256).Hash
        $actual = (Get-FileHash (Join-Path $app "mods/cm64-embedded-mario/$name") -Algorithm SHA256).Hash
        if ($expected -ne $actual) { throw 'Private diagnostic mod source drift' }
    }
    $settings = Get-Content (Join-Path $app 'settings.json') -Raw | ConvertFrom-Json
    if ($settings.ActiveMods.Count -ne 1 -or $settings.ActiveMods[0] -ne 'cm64-embedded-mario') {
        throw 'Unknown active mods'
    }
    $run = Join-Path $cache ('M43-input/autowarp-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $run | Out-Null
    $trace = Join-Path $run 'native.jsonl'
    $envVars = @{
        CM64_EMBED_ENABLE='1'; CM64_INOUTPUT='1'; CM64_TEXTURE_ATLAS='1';
        CM64_LIVE_CONTROLS='1'; CM64_CAMERA_PROBE='0'; CM64_EMBED_ROM=$rom;
        CM64_LIVE_TRACE=$trace; CM64_GOAL19_NATIVE_AUTOWARP='1';
        PATH=('C:/msys64/mingw64/bin;' + $env:PATH)
    }
    $p = Start-Process -FilePath (Join-Path $app 'CrashBandicoot.exe') -WorkingDirectory $app -PassThru `
        -ArgumentList @('--run', ('"' + $disc + '"')) -WindowStyle Normal -Environment $envVars `
        -RedirectStandardOutput (Join-Path $run 'host.log') -RedirectStandardError (Join-Path $run 'errors.log')
    Write-Output "GOAL19_NATIVE_PID=$($p.Id) time_budget=$Seconds input=IJKL/U private_evidence=$run"
    try {
        Start-Sleep -Seconds $Seconds
        $p.Refresh()
        $responsive = -not $p.HasExited -and $p.Responding
    } finally {
        $p.Refresh()
        if (-not $p.HasExited) {
            $p.CloseMainWindow() | Out-Null
            if (-not $p.WaitForExit(5000)) {
                Stop-Process -Id $p.Id
                $p.WaitForExit(5000) | Out-Null
            }
        }
    }
    $log = Get-Content (Join-Path $run 'host.log') -Raw
    $stderrSize = (Get-Item (Join-Path $run 'errors.log')).Length
    $nativeScene = $log.Contains('ORIGINAL_SCENE_OBSERVED level=9')
    $mesh = $log.Contains('M41B2_TEXTURED_MESH_DREW')
    $requested = $log.Contains('HOST_DEV_WARP_REQUESTED level=9')
    $audit = ''
    $auditExit = 1
    if (Test-Path -LiteralPath $trace) {
        Push-Location $repo
        try {
            $audit = (& $python -m tools.m43_live_gate --trace $trace | Out-String).Trim()
            $auditExit = $LASTEXITCODE
        } finally { Pop-Location }
    }
    @{schema=1; original_scene_observed=$nativeScene; native_authored_input_passed=($auditExit -eq 0);
      real_crash_collider=$false; full_playable=$false; process_stopped=$p.HasExited;
      host_responsive=$responsive; mesh_drew=$mesh; stderr_bytes=$stderrSize; audit=$audit} |
        ConvertTo-Json -Depth 4 | Set-Content (Join-Path $run 'summary.json') -Encoding utf8
    if (-not $p.HasExited -or -not $responsive -or $stderrSize -ne 0 -or
        -not $requested -or -not $nativeScene -or -not $mesh -or $auditExit -ne 0) {
        throw 'Native original-game scene/input gate BLOCKED; preserve private evidence'
    }
    Write-Output "GOAL19_NATIVE_AUTHORED_INPUT_PASS original_scene=9 original_guest_input=true shared_crash_collider=false private_evidence=$run"
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
