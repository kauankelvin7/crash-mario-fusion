#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64', [switch]$FullSuite)
. "$PSScriptRoot/Common.ps1"
$source = Join-Path $TaskCache 'c1'
$pin = '256fdcef59f15a190290cc19db3fa9a707843b69'
if (-not (Test-Path -LiteralPath $source)) {
    Invoke-Logged git @('clone','--depth','1','https://github.com/wurlyfox/c1.git',$source) 'c1-source-clone.log'
    $head = & git -C $source rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read public c1 cache HEAD.' }
    if ($head -ne $pin) {
        Invoke-Logged git @('-C',$source,'fetch','--depth','1','origin',$pin) 'c1-source-fetch.log'
        Invoke-Logged git @('-C',$source,'checkout','--detach',$pin) 'c1-source-checkout.log'
    }
}
$head = & git -C $source rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $head -ne $pin) { throw 'Wrong c1 cache revision; preserve it.' }
$dirty = & git -C $source status --porcelain
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Preserve and inspect dirty c1 source cache.' }
$repo = Convert-MsysPath $TaskRepo
$c1 = Convert-MsysPath $source
$mario = Convert-MsysPath (Join-Path $TaskCache 'sm64ex')
foreach ($path in @($repo,$c1,$mario)) {
    if ($path.Contains("'")) { throw 'Paths containing a single quote are unsupported.' }
}
$check = if ($FullSuite) { 'discover -s tests -v' } else { 'tests/test_volume_boundary.py -v' }
Invoke-Msys "cd '$repo' && export CM64_C1_ROOT='$c1' CM64_SM64EX_ROOT='$mario' && python -m unittest $check" 'reference-box-checks.log'
Write-Output 'VERIFIED_SYNTHETIC: authored geometry, original reference queries, no game launched. New native Windows execution is not established by Cloud results.'
