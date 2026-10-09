#Requires -Version 7.0
[CmdletBinding()]
param([Parameter(Mandatory)][string]$CrashDisc, [switch]$Apply,
    [ValidateRange(30,3600)][int]$Seconds = 300, [string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
$disc = (Resolve-Path -LiteralPath $CrashDisc).Path
if ([IO.Path]::GetExtension($disc) -notin @('.cue','.chd')) { throw 'Crash needs your own CUE/BIN or CHD.' }
$crashExe = Join-Path $TaskCache 'CrashBandicoot-Launcher/CrashBandicoot.Launcher/bin/Release/net10.0-windows/CrashBandicoot.exe'
$marioExe = Join-Path $TaskCache 'sm64ex-cm64/build/us_pc/sm64.us.exe'
foreach ($exe in @($crashExe,$marioExe)) {
    if (-not (Test-Path -LiteralPath $exe)) { throw 'Run Build-Integration.ps1 with your own ROM first.' }
}
$probe = [System.Net.Sockets.UdpClient]::new([System.Net.IPEndPoint]::new([System.Net.IPAddress]::Loopback,0))
$port = $probe.Client.LocalEndPoint.Port; $probe.Dispose()
$env:CM64_SESSION = [Guid]::NewGuid().ToString('N')
$env:CM64_PORT = [string]$port
$env:CM64_APPLY = if ($Apply) { '1' } else { '0' }
$env:PATH = (Join-Path $MsysRoot 'mingw64/bin') + ';' + $env:PATH
$crash = $null; $mario = $null
try {
    # Fresh nonce per run; no queued events survive process restarts.
    $crash = Start-Process -FilePath $crashExe -ArgumentList @('--run',('"'+$disc+'"')) -PassThru `
        -WorkingDirectory (Split-Path $crashExe) -RedirectStandardOutput (Join-Path $TaskLogs 'crash.stdout.log') `
        -RedirectStandardError (Join-Path $TaskLogs 'crash.stderr.log')
    $deadline = [DateTime]::UtcNow.AddSeconds(120)
    $ready = $false
    while (-not $ready -and [DateTime]::UtcNow -lt $deadline) {
        if ($crash.HasExited) { throw "Crash exited ($($crash.ExitCode)); see $TaskLogs" }
        $ready = [bool](Select-String -LiteralPath (Join-Path $TaskLogs 'crash.stdout.log') -Pattern '\[cm64\] receiver ready' -Quiet)
        if (-not $ready) { Start-Sleep -Milliseconds 200 }
    }
    if (-not $ready) { throw "Native mod did not report readiness; see $TaskLogs" }
    $mario = Start-Process -FilePath $marioExe -PassThru -WorkingDirectory (Split-Path $marioExe) `
        -RedirectStandardOutput (Join-Path $TaskLogs 'mario.stdout.log') `
        -RedirectStandardError (Join-Path $TaskLogs 'mario.stderr.log')
    Write-Output "Both runtime commands started. Apply=$Apply. Hold Crash R1 only in unpaused gameplay; collect ONE yellow coin in Mario. Logs: $TaskLogs"
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline -and -not $crash.HasExited -and -not $mario.HasExited) {
        Start-Sleep -Milliseconds 200
    }
    if ($crash.HasExited -and $crash.ExitCode -ne 0) { throw "Crash failed: $($crash.ExitCode)" }
    if ($mario.HasExited -and $mario.ExitCode -ne 0) { throw "Mario failed: $($mario.ExitCode)" }
} finally {
    foreach ($process in @($crash,$mario)) {
        if ($null -ne $process -and -not $process.HasExited) {
            $null = $process.CloseMainWindow()
            if (-not $process.WaitForExit(5000)) { $process.Kill($true); $process.WaitForExit() }
        }
    }
    @{
        session=$env:CM64_SESSION; apply=[bool]$Apply; utc=[DateTime]::UtcNow.ToString('o')
        mario='d7ca2c04364a6dd0dac58b47151e04e26887e6f0'
        crash='224da7757920a817de2d9242416f657ab95782ea'
        gameplay='NOT_TESTED'; jump_landing='NOT_TESTED'; shared_world='NOT_TESTED'
        note='Review native event logs and actual Windows gameplay; readiness/input application do not prove a jump.'
    } | ConvertTo-Json | Set-Content (Join-Path $TaskLogs 'run.json')
    Remove-Item Env:CM64_SESSION,Env:CM64_PORT,Env:CM64_APPLY -ErrorAction SilentlyContinue
}
