#Requires -Version 7.0
<#
.SYNOPSIS
Rebuild one private pinned public Crash runtime with the safe OutputPanel hook.
No game/retail assets are read here, and the sealed original M3 app is untouched.
#>
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$public=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/CrashBandicoot-Launcher'
$root=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M41B-overlay'
$private=Join-Path $root 'source-verified'
$runtime=Join-Path $root 'runtime-verified'
$app=Join-Path $root 'app-verified'
$baseApp=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M4-embed/crash-app'
$dot=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/dotnet/dotnet.exe'
$python='C:/msys64/mingw64/bin/python.exe'
$expected='224da7757920a817de2d9242416f657ab95782ea'
$pin=(& git -C $public rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $pin -ne $expected -or
   (& git -C $public status --porcelain)){throw 'Unrecognized original public Crash source'}
if(-not (Test-Path $dot) -or -not (Test-Path $python)){throw 'Private Windows build tools unavailable'}
foreach($n in @('CrashEmbeddedMarioMod.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','OriginalMarioPreview.cs','OriginalMarioOutputOverlay.cs','mod.json')){
    if(-not (Test-Path -LiteralPath (Join-Path $repo "integration/embedded_mario/$n"))){throw "Missing source $n"}
}
if($CheckOnly){
    Write-Output "M41B_SOURCE_PREFLIGHT_OK original_pin=$expected private_build_not_tested=true"
    return
}
New-Item -ItemType Directory -Force $root|Out-Null
if(-not (Test-Path $private)){
    & git clone --no-hardlinks $public $private
    if($LASTEXITCODE -ne 0){throw 'Private public runtime checkout creation failed'}
    Push-Location $repo
    try{
        & $python -m tools.prepare_m41b_host --source $public --private-clone $private
        if($LASTEXITCODE -ne 0){throw 'Pinned private renderer patch failed'}
    }finally{Pop-Location}
}
if((& git -C $private rev-parse HEAD).Trim() -ne $expected){throw 'Private source pin differs'}
Push-Location $repo
try {
    & $python -m tools.prepare_m41b_host --source $public --private-clone $private --verify-only
    if($LASTEXITCODE -ne 0){throw 'Private renderer sources changed unexpectedly'}
}finally{Pop-Location}
$dirty=@(git -C $private status --porcelain)
if($dirty.Count -ne 2 -or (@($dirty|Where-Object{$_ -notmatch 'MenuRegistry.cs|OutputPanel.cs'})).Count -ne 0){
    throw 'Private runtime checkout has unrelated changes'
}
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
& $dot build (Join-Path $private 'RecompOne.Runtime/RecompOne.Runtime.csproj') -c Release -f net10.0 -o $runtime -v quiet
if($LASTEXITCODE -ne 0){throw 'Patched private host runtime build failed'}
if(-not (Test-Path $app)){Copy-Item -LiteralPath $baseApp -Destination $app -Recurse}
$seal=Get-Content (Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose/observer-build.json') -Raw|ConvertFrom-Json
foreach($n in @('CrashBandicoot.exe','CrashBandicoot.dll')){
    $hash=(Get-FileHash (Join-Path $app $n) -Algorithm SHA256).Hash.ToLowerInvariant()
    if($hash -ne $seal.hashes.PSObject.Properties[$n].Value){throw "Original host shell modified: $n"}
}
$settings=Get-Content (Join-Path $app 'settings.json') -Raw|ConvertFrom-Json
if(@($settings.ActiveMods).Count -ne 1 -or @($settings.ActiveMods)[0] -ne 'cm64-embedded-mario'){
    throw 'Unknown active mods in private app'
}
$target=Join-Path $app 'mods/cm64-embedded-mario'
foreach($n in @('CrashEmbeddedMarioMod.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','OriginalMarioPreview.cs','OriginalMarioOutputOverlay.cs','mod.json')){
    Copy-Item (Join-Path $repo "integration/embedded_mario/$n") (Join-Path $target $n) -Force
}
Copy-Item (Join-Path $runtime 'RecompOne.Runtime.dll') (Join-Path $app 'RecompOne.Runtime.dll') -Force
$native=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M4-embed/libsm64/dist/sm64.dll'
Copy-Item $native (Join-Path $app 'sm64.dll') -Force
$metadata=[ordered]@{
    version=1
    original_pin=$expected
    original_host_exe_sha256=$seal.hashes.'CrashBandicoot.exe'
    original_host_dll_sha256=$seal.hashes.'CrashBandicoot.dll'
    host_runtime_sha256=(Get-FileHash (Join-Path $app 'RecompOne.Runtime.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
    mario_dll_sha256=(Get-FileHash (Join-Path $app 'sm64.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
    sources=@{}
}
foreach($n in @('CrashEmbeddedMarioMod.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','OriginalMarioPreview.cs','OriginalMarioOutputOverlay.cs','mod.json')){
    $metadata.sources[$n]=(Get-FileHash (Join-Path $repo "integration/embedded_mario/$n") -Algorithm SHA256).Hash.ToLowerInvariant()
}
$metadata|ConvertTo-Json -Depth 5|Set-Content (Join-Path $root 'host-verified.json') -Encoding utf8
Write-Output 'M41B_PRIVATE_BUILD_OK host_runtime=patched_source public_pin_preserved=true native_mario=unchanged'
