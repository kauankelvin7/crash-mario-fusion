#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$CrashLog,
    [Parameter(Mandatory)][string]$Calibration,
    [string]$MsysRoot = 'C:/msys64'
)
. "$PSScriptRoot/Common.ps1"
$repo = Convert-MsysPath $TaskRepo
$log = Convert-MsysPath (Resolve-Path -LiteralPath $CrashLog).Path
$calibrationPath = Convert-MsysPath (Resolve-Path -LiteralPath $Calibration).Path
# Invoke-Msys interpolates a single-quoted shell argument. Reject its delimiter.
foreach ($path in @($repo, $log, $calibrationPath)) {
    if ($path.Contains("'")) { throw "Paths containing a single quote are unsupported." }
}
Invoke-Msys "cd '$repo'; python -m unittest tests/test_world_coordinates.py -v; python tools/world_coordinates.py --log '$log' --calibration '$calibrationPath'" 'world-coordinates.log'
Write-Output 'Read-only coordinate preflight. Neither shared collision nor a verified Mario area is implied. Keep logs/calibration private.'
