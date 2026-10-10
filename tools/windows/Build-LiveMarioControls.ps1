#Requires -Version 7.0
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M43-input'
$up=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/CrashBandicoot-Launcher'
$base=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M41B2-texture/app'
$dot=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/dotnet/dotnet.exe'
$python='C:/msys64/mingw64/bin/python.exe'
if(@(Get-Process -Name 'CrashBandicoot*' -ErrorAction SilentlyContinue).Count){throw 'Wait for all original game workstreams to stop before building'}
Push-Location $repo
try {
 $gate=& $python -m tools.m43_live_gate --source $up
 if($LASTEXITCODE -ne 0){throw 'M43 source gate failed'}
 if($CheckOnly){Write-Output 'M43_SOURCE_GATE_OK native_game=NOT_TESTED';return}
 $seal=Get-Content (Join-Path (Split-Path $base) 'sealed-host.json') -Raw|ConvertFrom-Json
 foreach($pair in @(@('CrashBandicoot.exe',$seal.original_exe),@('CrashBandicoot.dll',$seal.original_crash_dll),@('RecompOne.Runtime.dll',$seal.patched_runtime),@('sm64.dll',$seal.original_libsm64))){
  if((Get-FileHash (Join-Path $base $pair[0]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pair[1]){throw 'Original sealed base drift'}
 }
 New-Item -ItemType Directory -Force $root|Out-Null
 $source=Join-Path $root 'source'
 if(-not(Test-Path $source)){
  & git clone --no-hardlinks $up $source
  if($LASTEXITCODE -ne 0){throw 'Private clone failed'}
  & $python -m tools.prepare_m41b_host --source $up --private-clone $source
  if($LASTEXITCODE -ne 0){throw 'Private output hook failed'}
  & $python -m tools.prepare_m41b2_atlas --source $up --private-clone $source
  if($LASTEXITCODE -ne 0){throw 'Private atlas hook failed'}
 }
 & $python -m tools.prepare_m41b2_atlas --source $up --private-clone $source --verify-only
 if($LASTEXITCODE -ne 0){throw 'Private GL host drift'}
 & $python -m tools.prepare_m43_host --source $up --private-clone $source
 if($LASTEXITCODE -ne 0){throw 'Private input seam failed'}
 if((& git -C $source rev-parse HEAD).Trim() -ne '224da7757920a817de2d9242416f657ab95782ea'){throw 'Private pin drift'}
 $dirty=@(& git -C $source status --porcelain)
 if($dirty.Count -ne 5 -or @($dirty|Where-Object{$_ -notmatch 'HostWindow.cs|MenuRegistry.cs|OutputPanel.cs|OriginalMarioAtlas.cs|OriginalMarioInputHost.cs'}).Count){throw 'Private foreign source edits'}
 $runtime=Join-Path $root 'runtime'
 & $dot build (Join-Path $source 'RecompOne.Runtime/RecompOne.Runtime.csproj') -c Release -f net10.0 -o $runtime -v quiet
 if($LASTEXITCODE -ne 0){throw 'Private host compile failed'}
 $app=Join-Path $root 'app'
 if(Test-Path $app){
  $previous=Get-Content (Join-Path $root 'sealed-live.json') -Raw|ConvertFrom-Json
  foreach($entry in $previous.hashes.PSObject.Properties){
   if((Get-FileHash (Join-Path $app $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Isolated app user edits; refuse overwrite'}
  }
  foreach($entry in $previous.mods.PSObject.Properties){
   if((Get-FileHash (Join-Path $app "mods/cm64-embedded-mario/$($entry.Name)") -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Isolated mod user edits; refuse overwrite'}
  }
 } else {Copy-Item -LiteralPath $base -Destination $app -Recurse}
 Copy-Item (Join-Path $runtime 'RecompOne.Runtime.dll') (Join-Path $app 'RecompOne.Runtime.dll') -Force
 $dest=Join-Path $app 'mods/cm64-embedded-mario'
 $names=@('Interop.cs','LiveMarioInput.cs','LiveMarioControls.cs','CrashEmbeddedMarioMod.cs','OriginalMarioPreview.cs','OriginalMarioOutputOverlay.cs','CrashCameraProbe.cs','mod.json')
 foreach($name in $names){Copy-Item (Join-Path $repo "integration/embedded_mario/$name") (Join-Path $dest $name) -Force}
 & $dot build (Join-Path $repo 'integration/embedded_mario/LiveMarioCompile.csproj') "-p:CM64HostDirectory=$app" "-p:BaseIntermediateOutputPath=$root/compile-obj/" -o (Join-Path $root 'compile') -v quiet
 if($LASTEXITCODE -ne 0){throw 'M43 typed mod compile failed; no game started'}
 $hashes=@{}
 foreach($name in @('CrashBandicoot.exe','CrashBandicoot.dll','RecompOne.Runtime.dll','sm64.dll','settings.json')){
  $hashes[$name]=(Get-FileHash (Join-Path $app $name) -Algorithm SHA256).Hash.ToLowerInvariant()
 }
 $mods=@{}
 foreach($name in $names){$mods[$name]=(Get-FileHash (Join-Path $dest $name) -Algorithm SHA256).Hash.ToLowerInvariant()}
 @{schema=1;source=($gate|ConvertFrom-Json);hashes=$hashes;mods=$mods}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $root 'sealed-live.json')
 Write-Output 'M43_PRIVATE_BUILD_OK original_game=NOT_TESTED authored_floor_only=true'
} finally {Pop-Location}
