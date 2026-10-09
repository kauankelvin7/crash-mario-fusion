#Requires -Version 7.0
[CmdletBinding()]
param([string]$MarioRom, [string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
$launcher = Join-Path $TaskCache 'CrashBandicoot-Launcher/CrashBandicoot.Launcher'
Invoke-Logged $TaskDotnet @('build',$launcher,'-c','Release','-f','net10.0-windows',
    '-p:TargetFrameworks=net10.0-windows','-p:PlatformTarget=x64') 'launcher-build.log'
$repo = Convert-MsysPath $TaskRepo
$source = Convert-MsysPath (Join-Path $TaskCache 'sm64ex')
$prepared = Join-Path $TaskCache 'sm64ex-cm64'
$output = Convert-MsysPath $prepared
Invoke-Msys "python '$repo/tools/prepare_integration.py' --source '$source' --output '$output'" 'prepare-native-hook.log'
$appRoot = Convert-MsysPath (Join-Path $launcher 'bin/Release/net10.0-windows')
Invoke-Msys "python '$repo/tools/install_crash_mod.py' --app-root '$appRoot'" 'install-mod.log'
$romDestination = Join-Path $prepared 'baserom.us.z64'
if ($MarioRom) {
    $rom = (Resolve-Path -LiteralPath $MarioRom).Path
    if ((Get-FileHash -LiteralPath $rom -Algorithm SHA1).Hash.ToLowerInvariant() -ne
        '9bef1128717f958171a4afac3ed78ee2bb4e86ce') { throw 'SM64 US ROM hash mismatch.' }
    if (Test-Path -LiteralPath $romDestination) {
        if ((Get-FileHash -LiteralPath $romDestination -Algorithm SHA1).Hash -ne
            (Get-FileHash -LiteralPath $rom -Algorithm SHA1).Hash) { throw 'Existing ROM differs; preserve it.' }
    } else { Copy-Item -LiteralPath $rom -Destination $romDestination }
}
if (-not (Test-Path -LiteralPath $romDestination)) {
    throw 'Native hook/mod prepared; full sm64ex build BLOCKED. Supply your own US ROM via -MarioRom.'
}
if ((Get-FileHash -LiteralPath $romDestination -Algorithm SHA1).Hash.ToLowerInvariant() -ne
    '9bef1128717f958171a4afac3ed78ee2bb4e86ce') { throw 'Cached ROM hash mismatch.' }
Invoke-Msys "cd '$output'; make -j2 VERSION=us TARGET_BITS=64 RENDER_API=GL WINDOWS_CONSOLE=1" 'sm64ex-native-build.log'
Write-Output "Original runtime adapters built. Native gameplay NOT_TESTED until actually run. Logs: $TaskLogs"
