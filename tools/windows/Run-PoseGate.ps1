#Requires -Version 7.0
<#
.SYNOPSIS
Operator-guided, bounded read-only CMW1 check for ONE original game.
.DESCRIPTION
Requires an explicit -Game and, for Crash, -CrashDisc from an owned local copy.
Do not claim shared-world calibration: a successful capture only proves that
one original-game observer delivered locally accepted snapshots.
-CheckOnly validates prerequisites without launching either game.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Crash','Mario')][string]$Game,
    [string]$CrashDisc,
    [ValidateRange(30,300)][int]$Seconds = 180,
    [ValidateRange(1,3000)][int]$MaxSamples = 2100,
    [switch]$CheckOnly,
    [string]$MsysRoot = 'C:/msys64'
)
. "$PSScriptRoot/Common.ps1"

$python = Join-Path $MsysRoot 'mingw64/bin/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Native MinGW64 Python is missing. Run Setup.ps1.'
}
$env:PATH = (Join-Path $MsysRoot 'mingw64/bin') + ';' + $env:PATH
$arguments = @()
if ($Game -eq 'Crash') {
    if (-not $CrashDisc) { throw 'Crash requires -CrashDisc pointing to your own local .cue or .chd.' }
    $disc = (Resolve-Path -LiteralPath $CrashDisc -ErrorAction Stop).Path
    if (-not (Test-Path -LiteralPath $disc -PathType Leaf) -or
        [IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue','.chd')) {
        throw 'CrashDisc must be an existing .cue or .chd file.'
    }
    Push-Location $TaskRepo
    try {
        # checked_launcher verifies sealed private hashes and exactly one observer mod.
        & $python -c 'from tools.collect_crash_pose import checked_launcher; checked_launcher()'
        if ($LASTEXITCODE -ne 0) { throw 'Crash private diagnostic launcher failed verification. Preserve its original files.' }
    } finally { Pop-Location }
    $arguments = @('-m','tools.collect_crash_pose','--crash-disc',$disc)
} else {
    if ($CrashDisc) { throw '-CrashDisc applies only to Crash.' }
    $prepared = Join-Path $TaskCache 'sm64ex-cm64'
    $marioExe = Join-Path $prepared 'build/us_pc/sm64.us.f3dex2e.exe'
    $marker = Join-Path $prepared '.cm64-generated.json'
    if (-not (Test-Path -LiteralPath $marioExe -PathType Leaf) -or
        -not (Test-Path -LiteralPath $marker -PathType Leaf)) {
        throw 'Mario private instrumented build is missing. Run Build-Integration.ps1 with your own verified ROM.'
    }
    # The generated manifest protects the private instrumented source seam.
    $manifest = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if ($manifest.pin -ne 'd7ca2c04364a6dd0dac58b47151e04e26887e6f0' -or
        $null -eq $manifest.hashes) { throw 'Unrecognized Mario source pin/manifest.' }
    $tracked = @('src/game/interaction.c','Makefile','src/pc/cm64_coin.c',
                 'src/pc/cm64_coin.h','src/game/level_update.c','src/game/area.c',
                 'src/pc/cm64_pose.c','src/pc/cm64_pose.h')
    if (@($manifest.hashes.PSObject.Properties).Count -ne $tracked.Count) {
        throw 'Unexpected Mario source manifest entries.'
    }
    foreach ($name in $tracked) {
        $entry = $manifest.hashes.PSObject.Properties[$name]
        $sourcePath = Join-Path $prepared $name
        if ($null -eq $entry -or -not (Test-Path -LiteralPath $sourcePath -PathType Leaf) -or
            (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
            throw 'Mario instrumented source integrity differs from private manifest; preserve local changes.'
        }
    }
    $arguments = @('-m','tools.collect_pose','--mario-exe',$marioExe)
}
if ($CheckOnly) {
    Write-Output "PREFLIGHT_OK game=$Game source_preflight_verified=true gameplay=NOT_TESTED"
    exit 0
}
Write-Output "OPERATOR_GATE game=$Game read_only=true seconds=$Seconds max_samples=$MaxSamples"
Write-Output 'ENTER A PLAYABLE LEVEL, then walk and jump normally. Pause briefly and resume.'
Write-Output 'Menus/intro screens may send ZERO packets; do not interpret launch as pose validation.'
Write-Output 'This captures ONE original engine at a time; NOT cross-engine physical synchronization.'
Write-Output 'No virtual controller input, shared collision, geometry injection or publishing occurs.'
Push-Location $TaskRepo
try {
    & $python @arguments '--seconds' "$Seconds" '--count' "$MaxSamples"
    $result = $LASTEXITCODE
} finally { Pop-Location }
if ($result -ne 0) {
    throw "POSE_NOT_VERIFIED: no valid completed live capture. Inspect the private summary/logs printed above. Exit=$result"
}
Write-Output "POSE_OBSERVED game=$Game provenance=ORIGINAL_RUNTIME_RECEIVER_ONLY calibration_ready=false physical_status=BLOCKED"
