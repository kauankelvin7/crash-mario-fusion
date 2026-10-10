#Requires -Version 7.0
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$up=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/CrashBandicoot-Launcher'
$root=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M41B2B-camera'
$src=Join-Path $root 'source'
$runtime=Join-Path $root 'runtime'
$app=Join-Path $root 'app'
$base=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M41B-overlay/app-verified'
$dot=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/dotnet/dotnet.exe'
$python='C:/msys64/mingw64/bin/python.exe'
$pin='224da7757920a817de2d9242416f657ab95782ea'
if((& git -C $up rev-parse HEAD).Trim() -ne $pin -or (& git -C $up status --porcelain)){
 throw 'Public upstream source not pinned and clean'
}
foreach($name in @('OriginalMarioAtlasHost.cs','CrashEmbeddedMarioMod.cs','CrashCameraProbe.cs',
 'OriginalMarioPreview.cs','OriginalMarioOutputOverlay.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','mod.json')){
 if(-not (Test-Path (Join-Path $repo "integration/embedded_mario/$name"))){throw "Missing $name"}
}
if($CheckOnly){Write-Output 'M41B2_PREFLIGHT_OK original_game_NOT_TESTED';return}
New-Item -ItemType Directory -Force $root|Out-Null
Push-Location $repo
try{
 if(-not(Test-Path $src)){
  & git clone --no-hardlinks $up $src
  if($LASTEXITCODE -ne 0){throw 'Clone of pinned public source failed'}
  & $python -m tools.prepare_m41b_host --source $up --private-clone $src
  if($LASTEXITCODE -ne 0){throw 'Original output hook source generation failed'}
  & $python -m tools.prepare_m41b2_atlas --source $up --private-clone $src
  if($LASTEXITCODE -ne 0){throw 'Original Mario GPU atlas host patch failed'}
 }
 & $python -m tools.prepare_m41b2_atlas --source $up --private-clone $src --verify-only
 if($LASTEXITCODE -ne 0){throw 'Private pinned GL owner source drift'}
}finally{Pop-Location}
if((& git -C $src rev-parse HEAD).Trim() -ne $pin){throw 'Private public source pin mismatch'}
$dirty=@(git -C $src status --porcelain)
if($dirty.Count -ne 4){throw 'Unexpected private original Crash source alterations'}
if(@($dirty|Where-Object{$_ -notmatch 'HostWindow.cs|MenuRegistry.cs|OutputPanel.cs|OriginalMarioAtlas.cs'}).Count){
 throw 'Foreign modification in private source checkout'
}
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
& $dot build (Join-Path $src 'RecompOne.Runtime/RecompOne.Runtime.csproj') -c Release -f net10.0 -o $runtime -v quiet
if($LASTEXITCODE -ne 0){throw 'Host-managed GL atlas resource build failed'}
if(-not(Test-Path $app)){Copy-Item -LiteralPath $base -Destination $app -Recurse}
$seal=Get-Content (Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose/observer-build.json') -Raw|ConvertFrom-Json
foreach($name in @('CrashBandicoot.exe','CrashBandicoot.dll')){
 $hash=(Get-FileHash (Join-Path $app $name) -Algorithm SHA256).Hash.ToLowerInvariant()
 if($hash -ne $seal.hashes.PSObject.Properties[$name].Value){throw "Unknown original Crash $name"}
}
$settings=Get-Content (Join-Path $app 'settings.json') -Raw|ConvertFrom-Json
if(@($settings.ActiveMods).Count -ne 1 -or @($settings.ActiveMods)[0] -ne 'cm64-embedded-mario'){
 throw 'Unexpected active mod'
}
$dest=Join-Path $app 'mods/cm64-embedded-mario'
foreach($name in @('CrashEmbeddedMarioMod.cs','CrashCameraProbe.cs','OriginalMarioPreview.cs',
 'OriginalMarioOutputOverlay.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','mod.json')){
 Copy-Item -LiteralPath (Join-Path $repo "integration/embedded_mario/$name") -Destination (Join-Path $dest $name) -Force
}
Copy-Item (Join-Path $runtime 'RecompOne.Runtime.dll') (Join-Path $app 'RecompOne.Runtime.dll') -Force
$hashes=@{}
foreach($name in @('CrashEmbeddedMarioMod.cs','CrashCameraProbe.cs','OriginalMarioPreview.cs',
 'OriginalMarioOutputOverlay.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','mod.json')){
 $hashes[$name]=(Get-FileHash (Join-Path $dest $name) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$manifest=@{
 schema=1;public_pin=$pin;original_exe=$seal.hashes.'CrashBandicoot.exe'
 original_crash_dll=$seal.hashes.'CrashBandicoot.dll'
 patched_runtime=(Get-FileHash (Join-Path $app 'RecompOne.Runtime.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
 original_libsm64=(Get-FileHash (Join-Path $app 'sm64.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
 mod_sources=$hashes
}
$manifest|ConvertTo-Json -Depth 6 |Set-Content (Join-Path $root 'sealed-host.json') -Encoding utf8
Write-Output 'M41B2_PRIVATE_BUILD_OK host_gl_owner=true original_exe_unchanged=true native_mario_unchanged=true'
