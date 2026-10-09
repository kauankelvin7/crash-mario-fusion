#Requires -Version 7.0
[CmdletBinding()]
param([ValidateSet('Crash','Mario')][string]$Game, [string]$CrashDisc, [switch]$Smoke,
    [string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
if (-not $Game) { throw 'Select -Game Crash or -Game Mario.' }
if ($Game -eq 'Crash') {
    Use-Dotnet
    if (-not $CrashDisc) { throw 'Use -CrashDisc with your own NTSC-U SCUS-94900 CUE/BIN or CHD.' }
    $disc = (Resolve-Path -LiteralPath $CrashDisc).Path
    if ([IO.Path]::GetExtension($disc) -notin @('.cue','.chd')) { throw 'Use CUE or CHD.' }
    $exe = Join-Path $TaskCache 'CrashBandicoot-Launcher/CrashBandicoot.Launcher/bin/Release/net10.0-windows/CrashBandicoot.exe'
    $mode = if ($Smoke) { '--smoke' } else { '--run' }
    # AppPaths.Root follows ProcessPath: launching dotnet.exe would put user data/mods in the SDK folder.
    Invoke-Logged $exe @($mode,$disc) 'crash-run.log'
} else {
    if ($Smoke) { throw 'sm64ex has no inspected automated smoke mode; run and observe it normally.' }
    $exe = Join-Path $TaskCache 'sm64ex/build/us_pc/sm64.us.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw 'Build sm64ex with your own ROM first.' }
    # Make runtime DLLs from the chosen native MSYS2 toolchain discoverable.
    $env:PATH = (Join-Path $MsysRoot 'mingw64/bin') + ';' + $env:PATH
    Push-Location (Split-Path $exe)
    try { Invoke-Logged $exe @() 'mario-run.log' } finally { Pop-Location }
}
@{
    platform = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
    runtime = $Game; utc = [DateTime]::UtcNow.ToString('o'); command_exit = 0
    gameplay = 'NOT_TESTED'; graphics = 'NOT_TESTED'; shared_event = 'NOT_TESTED'
    note = 'Process exit/smoke timeout alone is insufficient; review actual gameplay and instrumentation.'
} | ConvertTo-Json | Set-Content (Join-Path $TaskLogs 'observation.json')
Write-Output "Runtime command completed. Observe and review gameplay evidence separately: $TaskLogs"
