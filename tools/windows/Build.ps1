#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64', [string]$MarioRom)
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
$launcher = Join-Path $TaskCache 'CrashBandicoot-Launcher/CrashBandicoot.Launcher'
Invoke-Logged $TaskDotnet @('build',$launcher,'-c','Release','-f','net10.0-windows',
    '-p:PlatformTarget=x64') 'launcher-build.log'
$lib = Convert-MsysPath (Join-Path $TaskCache 'libsm64')
Invoke-Msys "cd '$lib'; make -j2 lib" 'libsm64-build.log'
if ($MarioRom) {
    # Own big-endian US ROM only; hash is the pinned sm64ex project's US reference.
    $rom = (Resolve-Path -LiteralPath $MarioRom).Path
    if ((Get-FileHash -LiteralPath $rom -Algorithm SHA1).Hash.ToLowerInvariant() -ne
        '9bef1128717f958171a4afac3ed78ee2bb4e86ce') { throw 'SM64 US ROM hash mismatch.' }
    $destination = Join-Path $TaskCache 'sm64ex/baserom.us.z64'
    if (Test-Path -LiteralPath $destination) {
        if ((Get-FileHash -LiteralPath $destination -Algorithm SHA1).Hash -ne
            (Get-FileHash -LiteralPath $rom -Algorithm SHA1).Hash) { throw 'Existing ROM differs; preserve it.' }
    } else { Copy-Item -LiteralPath $rom -Destination $destination }
    $mario = Convert-MsysPath (Join-Path $TaskCache 'sm64ex')
    Invoke-Msys "cd '$mario'; make -j2 VERSION=us TARGET_BITS=64 RENDER_API=GL WINDOWS_BUILD=1 HOST_OS=Windows" 'sm64ex-build.log'
} else { Write-Output 'BLOCKED: full sm64ex build needs your own SM64 US ROM via -MarioRom.' }
Write-Output "Build logs: $TaskLogs. Compilation alone does not verify gameplay."
