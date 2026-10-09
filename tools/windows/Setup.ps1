#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
Get-Command git -ErrorAction Stop | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $MsysRoot 'usr/bin/bash.exe'))) {
    throw 'Install MSYS2 from https://www.msys2.org/ first, then rerun Setup.ps1.'
}
$pins = @(
    @('Matteo842/CrashBandicoot-Launcher','224da7757920a817de2d9242416f657ab95782ea'),
    @('sm64pc/sm64ex','d7ca2c04364a6dd0dac58b47151e04e26887e6f0'),
    @('libsm64/libsm64','fd11813208272b4271d92bd92feb8f3fdbe61be5')
)
foreach ($pin in $pins) {
    $directory = Join-Path $TaskCache ($pin[0].Split('/')[-1])
    if (-not (Test-Path -LiteralPath $directory)) {
        Invoke-Logged git @('clone','--depth','1',"https://github.com/$($pin[0]).git",$directory) 'clone.log'
        $head = & git -C $directory rev-parse HEAD
        if ($LASTEXITCODE -ne 0) { throw 'Cannot read cached HEAD.' }
        if ($head -ne $pin[1]) {
            Invoke-Logged git @('-C',$directory,'fetch','--depth','1','origin',$pin[1]) 'fetch.log'
            Invoke-Logged git @('-C',$directory,'checkout','--detach',$pin[1]) 'checkout.log'
        }
    }
    $head = & git -C $directory rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $head -ne $pin[1]) { throw "Wrong cached revision: $directory" }
    $dirty = & git -C $directory status --porcelain
    if ($LASTEXITCODE -ne 0 -or $dirty) { throw "Preserve and inspect dirty cache: $directory" }
}
$installer = Join-Path $TaskCache 'dotnet-install.ps1'
$dotnetPath = Join-Path $TaskCache 'dotnet/dotnet.exe'
if (-not (Test-Path -LiteralPath $dotnetPath)) {
    Invoke-WebRequest 'https://dot.net/v1/dotnet-install.ps1' -OutFile $installer
    & $installer -Version '10.0.401' -Architecture x64 -InstallDir (Join-Path $TaskCache 'dotnet') -NoPath
}
Use-Dotnet
Invoke-Msys 'pacman -S --needed --noconfirm make python mingw-w64-x86_64-gcc mingw-w64-x86_64-SDL2 mingw-w64-x86_64-glew' 'msys-packages.log'
Write-Output "Setup completed locally; run Build.ps1. Logs: $TaskLogs"
