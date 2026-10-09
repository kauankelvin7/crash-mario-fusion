#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateRange(0,65535)][int]$CrashLevel,
    [Parameter(Mandatory)][ValidateRange(1,32767)][int]$MarioLevel,
    [Parameter(Mandatory)][ValidateRange(1,32767)][int]$MarioArea,
    [Parameter(Mandatory)][ValidateRange(1,4294967295)][long]$CrashEpoch,
    [Parameter(Mandatory)][ValidateRange(1,4294967295)][long]$MarioEpoch,
    [Parameter(Mandatory)][ValidateRange(1,1000000000)][long]$MaxAgeNs,
    [Parameter(Mandatory)][ValidateRange(1,300000000000)][long]$MaxGapNs,
    [ValidateRange(1024,65535)][int]$Port = 39100,
    [ValidateRange(1,300)][int]$Seconds = 60,
    [ValidateRange(1,10000)][int]$MaxPackets = 6000,
    [string]$MsysRoot = 'C:/msys64'
)
. "$PSScriptRoot/Common.ps1"
if ($MaxGapNs -lt $MaxAgeNs) { throw 'Gap threshold must be at least the age threshold.' }
$python = Join-Path $MsysRoot 'mingw64/bin/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Native MinGW Python is required; see WINDOWS.md.' }
$env:PATH = (Join-Path $MsysRoot 'mingw64/bin') + ';' + $env:PATH
$root = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/telemetry'))
$root = & $python -c 'import sys; from pathlib import Path; print(Path(sys.argv[1]).resolve())' $root
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve private configuration directory.' }
$relative = [IO.Path]::GetRelativePath($TaskRepo, $root)
if ($relative -eq '.' -or (-not [IO.Path]::IsPathRooted($relative) -and $relative -ne '..' -and -not $relative.StartsWith('..\') -and -not $relative.StartsWith('../'))) {
    throw 'Keep private receiver configuration outside Git.'
}
New-Item -ItemType Directory -Force $root | Out-Null
$config = Join-Path $root ('receiver-' + [Guid]::NewGuid().ToString('N') + '.json')
$document = @{
    schema_version = 1; max_age_ns = $MaxAgeNs; max_gap_ns = $MaxGapNs
    sources = @{
        crash = @{ session = [Guid]::NewGuid().ToString('N'); frame = ('4d333244{0:x8}{1:x8}00000000' -f $CrashLevel,$CrashEpoch) }
        mario = @{ session = [Guid]::NewGuid().ToString('N'); frame = ('4d333141{0:x4}{1:x4}00000000{2:x8}' -f $MarioLevel,$MarioArea,$MarioEpoch) }
    }
}
$document | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $config -Encoding utf8NoBOM
Write-Output "Emitter configuration for separate operator terminals: $config"
Write-Output "Declare both emitter ports as $Port. Receiver only: no game is launched."
Push-Location $TaskRepo
try {
    Invoke-Logged $python @('-m','tools.collect_observations','--config',$config,'--port',"$Port",'--seconds',"$Seconds",'--max-packets',"$MaxPackets") 'paired-observation-console.log'
} finally { Pop-Location }
