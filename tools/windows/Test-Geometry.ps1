#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
$repo = Convert-MsysPath $TaskRepo
$source = Convert-MsysPath (Join-Path $TaskCache 'sm64ex')
foreach ($path in @($repo, $source)) {
    if ($path.Contains("'")) { throw 'Paths containing a single quote are unsupported.' }
}
Invoke-Msys "cd '$repo'; export CM64_SM64EX_ROOT='$source'; python -m unittest tests/test_geometry_preflight.py tests/test_native_geometry.py tests/test_world_snapshot.py -v" 'geometry-snapshot-checks.log'
Write-Output 'VERIFIED_SYNTHETIC only: isolated original collision code, authored triangles, fixture pools. No game launched, no live collision or GPU validation.'
