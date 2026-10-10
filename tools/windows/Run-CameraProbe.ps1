#Requires -Version 7.0
<#
.SYNOPSIS
Run a bounded private native Crash process with the original Mario mesh
drawn on the actual OutputPanel image, without claiming calibrated depth.
#>
[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$MarioRom,
 [Parameter(Mandatory)][string]$CrashDisc,
 [ValidateRange(25,120)][int]$Seconds=45,
 [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M41B2B-camera'
$app=Join-Path $root 'app'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$m=Get-Content (Join-Path $root 'sealed-host.json') -Raw|ConvertFrom-Json
if($m.public_pin -ne '224da7757920a817de2d9242416f657ab95782ea'){throw 'Unknown source revision'}
foreach($pair in @(
 @('CrashBandicoot.exe',$m.original_exe),
 @('CrashBandicoot.dll',$m.original_crash_dll),
 @('RecompOne.Runtime.dll',$m.patched_runtime),
 @('sm64.dll',$m.original_libsm64)
)){
 $h=(Get-FileHash (Join-Path $app $pair[0]) -Algorithm SHA256).Hash.ToLowerInvariant()
 if($h -ne $pair[1]){throw "Private binary hash changed: $($pair[0])"}
}
foreach($n in @('CrashEmbeddedMarioMod.cs','CrashCameraProbe.cs','LiveMarioInput.cs','LiveMarioControls.cs','Interop.cs','OriginalMarioPreview.cs','OriginalMarioOutputOverlay.cs','mod.json')){
 $sha=(Get-FileHash (Join-Path $repo "integration/embedded_mario/$n") -Algorithm SHA256).Hash.ToLowerInvariant()
 $live=(Get-FileHash (Join-Path $app "mods/cm64-embedded-mario/$n") -Algorithm SHA256).Hash.ToLowerInvariant()
 if($sha -ne $m.mod_sources.PSObject.Properties[$n].Value -or $sha -ne $live){throw "Private mod source changed: $n"}
}
$s=Get-Content (Join-Path $app 'settings.json') -Raw|ConvertFrom-Json
if($s.ModsConfigured -ne $true -or @($s.ActiveMods).Count -ne 1 -or
   @($s.ActiveMods)[0] -ne 'cm64-embedded-mario'){throw 'Unexpected mods enabled'}
$rom=(Resolve-Path -LiteralPath $MarioRom -ErrorAction Stop).Path
$disc=(Resolve-Path -LiteralPath $CrashDisc -ErrorAction Stop).Path
if((Get-Item $rom).Length -ne 8388608 -or
 (Get-FileHash $rom -Algorithm SHA1).Hash.ToLowerInvariant() -ne '9bef1128717f958171a4afac3ed78ee2bb4e86ce'){
 throw 'Invalid private owned original SM64 US ROM'
}
if(-not (Test-Path $disc -PathType Leaf) -or [IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue','.chd')){throw 'Invalid private owned Crash disc'}
if($CheckOnly){
 Write-Output "M41B_PREFLIGHT_OK sealed_runtime=true private_source=true gameplay_NOT_TESTED"
 return
}
$run=Join-Path $root ('verified-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run|Out-Null
$envVars=@{CM64_EMBED_ENABLE='1';CM64_INOUTPUT='1';CM64_TEXTURE_ATLAS='1';CM64_CAMERA_PROBE='1';CM64_EMBED_ROM=$rom;
 PATH=('C:/msys64/mingw64/bin;'+$env:PATH)}
$runargs=@{FilePath=(Join-Path $app 'CrashBandicoot.exe');WorkingDirectory=$app;
 ArgumentList=@('--run',('"'+$disc+'"'));Environment=$envVars;
 RedirectStandardOutput=(Join-Path $run 'host.log');
 RedirectStandardError=(Join-Path $run 'errors.log');PassThru=$true}
$p=Start-Process @runargs
$responsive=$false
try {
 Start-Sleep -Seconds $Seconds
 $p.Refresh();if(-not $p.HasExited){$responsive=$p.Responding}
}finally{
 $p.Refresh();if(-not $p.HasExited){
  Stop-Process -Id $p.Id -ErrorAction SilentlyContinue
  $p.WaitForExit(5000)|Out-Null
 }
}
$lines=Get-Content (Join-Path $run 'host.log') -ErrorAction SilentlyContinue
$errors=@(Get-Content (Join-Path $run 'errors.log') -ErrorAction SilentlyContinue)
$mod=[bool]($lines|Where-Object{$_ -match '\[Mods\] loaded 1/1 mod'})
$init=[bool]($lines|Where-Object{$_ -match '\[cm64-embedded\] INIT_OK'})
$mesh=[bool]($lines|Where-Object{$_ -match 'HOST_SOLVER frames=180 mesh_frames=180 moving_frames=101'})
$overlay=[bool]($lines|Where-Object{$_ -match 'M41B_OUTPUT_OVERLAY_DREW original_triangles=[1-9][0-9]* original_crash_image_bounds=true overlay=true guest_tick_first=[1-9][0-9]* guest_tick_last=[1-9][0-9]* camera_calibrated=false'})
$upload=[bool]($lines|Where-Object{$_ -match 'HOST_GL_ATLAS_UPLOADED width=704 height=64 private=true'})
$textured=[bool]($lines|Where-Object{$_ -match 'M41B2_TEXTURED_MESH_DREW original_textured_triangles=[1-9][0-9]* native_guest_tick=[1-9][0-9]* authored_screen_anchor=true'})
$failed=[bool]($lines|Where-Object{$_ -match 'FAIL_CLOSED|overlay disabled:|upload disabled:'})
$ok=$mod -and $init -and $mesh -and $overlay -and $upload -and $textured -and -not $failed -and $responsive -and $errors.Count -eq 0
$cameraEvidence=$false
if($ok){
 $python='C:/msys64/mingw64/bin/python.exe'
 if(-not (Test-Path -LiteralPath $python)){throw 'Private camera auditor Python unavailable'}
 Push-Location $repo
 try {
  & $python -m tools.assess_camera_probe --private-log (Join-Path $run 'host.log')
  $cameraEvidence=($LASTEXITCODE -eq 0)
 } finally {Pop-Location}
}
$ok=$ok -and $cameraEvidence
@{schema_version=1;passed=$ok;host_responsive=$responsive;mod_loaded=$mod;
 mesh=$mesh;overlay=$overlay;host_atlas_uploaded=$upload;textured_triangle_draw=$textured;
 raw_camera_variation=$cameraEvidence;source_phase='PAD_UNKNOWN';shared_depth=$false;camera_calibrated=$false;
 authentic_crash_collision=$false;in_level_visual_proof=$false
}|ConvertTo-Json|Set-Content (Join-Path $run 'summary.json') -Encoding utf8
Write-Output "M41B2B_CAMERA_GATE passed=$ok camera_source_varied=$cameraEvidence mario_mesh=$mesh texture_gpu=$upload responsive=$responsive depth_complete=false"
if(-not $ok){throw 'Native in-image overlay gate failed; private logs retained'}
