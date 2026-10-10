#Requires -Version 7.0
[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$MarioRom,
 [Parameter(Mandatory)][string]$CrashDisc,
 [ValidateRange(30,120)][int]$Seconds=90,
 [switch]$CheckOnly,
 [switch]$ApproveHumanRun
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M43-input'
$app=Join-Path $root 'app'
$python='C:/msys64/mingw64/bin/python.exe'
$seal=Get-Content (Join-Path $root 'sealed-live.json') -Raw|ConvertFrom-Json
if($seal.schema -ne 1 -or $seal.source.pin -ne '224da7757920a817de2d9242416f657ab95782ea'){throw 'Unknown private seal'}
foreach($entry in $seal.hashes.PSObject.Properties){
 if((Get-FileHash (Join-Path $app $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Private host drift'}
}
foreach($entry in $seal.mods.PSObject.Properties){
 foreach($path in @((Join-Path $app "mods/cm64-embedded-mario/$($entry.Name)"),(Join-Path $repo "integration/embedded_mario/$($entry.Name)"))){
  if((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value){throw 'Private mod drift'}
 }
}
$settings=Get-Content (Join-Path $app 'settings.json') -Raw|ConvertFrom-Json
if(-not $settings.ModsConfigured -or @($settings.ActiveMods).Count -ne 1 -or $settings.ActiveMods[0] -ne 'cm64-embedded-mario'){throw 'Unexpected mods'}
$rom=(Resolve-Path -LiteralPath $MarioRom).Path
$disc=(Resolve-Path -LiteralPath $CrashDisc).Path
if((Get-Item $rom).Length -ne 8388608 -or (Get-FileHash $rom -Algorithm SHA1).Hash.ToLowerInvariant() -ne '9bef1128717f958171a4afac3ed78ee2bb4e86ce'){throw 'Owned Mario ROM rejected'}
if(-not(Test-Path $disc -PathType Leaf) -or [IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue','.chd')){throw 'Owned Crash disc rejected'}
Push-Location $repo
try {
 & $python -m tools.m43_live_gate --source (Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/CrashBandicoot-Launcher') | Out-Null
 if($LASTEXITCODE -ne 0){throw 'Current source gate failed'}
 if($CheckOnly){Write-Output 'M43_PREFLIGHT_OK human_gameplay=NOT_TESTED';return}
 if(-not $ApproveHumanRun){throw 'Explicit -ApproveHumanRun required; coordinate no other workstream game first'}
 $mutex=[Threading.Mutex]::new($false,'Local\CrashMarioFusion-OriginalGame')
 $locked=$false
 try {
  $locked=$mutex.WaitOne(0)
  if(-not $locked -or @(Get-Process -Name 'CrashBandicoot*' -ErrorAction SilentlyContinue).Count){throw 'Other original game active; wait, do not kill it'}
  $run=Join-Path $root ('human-'+[guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory $run|Out-Null
  $trace=Join-Path $run 'native.jsonl'
  Write-Host 'Enter a gameplay level, click Crash image, release Mario keys. IJKL move, U jump. Move both horizontal axes, jump then land; steer Crash independently. AUTHORED floor, NOT Crash collision.'
  $environment=@{CM64_EMBED_ENABLE='1';CM64_INOUTPUT='1';CM64_TEXTURE_ATLAS='1';CM64_LIVE_CONTROLS='1';CM64_CAMERA_PROBE='0';CM64_EMBED_ROM=$rom;CM64_LIVE_TRACE=$trace;PATH=('C:/msys64/mingw64/bin;'+$env:PATH)}
  $process=Start-Process -FilePath (Join-Path $app 'CrashBandicoot.exe') -WorkingDirectory $app -ArgumentList @('--run',('"'+$disc+'"')) -Environment $environment -WindowStyle Normal -RedirectStandardOutput (Join-Path $run 'host.log') -RedirectStandardError (Join-Path $run 'errors.log') -PassThru
  try {Start-Sleep -Seconds $Seconds; $process.Refresh(); $responsive=-not $process.HasExited -and $process.Responding}
  finally {
   $process.Refresh()
   if(-not $process.HasExited){$process.CloseMainWindow()|Out-Null; if(-not $process.WaitForExit(5000)){Stop-Process -Id $process.Id; $process.WaitForExit(5000)|Out-Null}}
  }
  $log=Get-Content (Join-Path $run 'host.log') -Raw
  $errors=Get-Content (Join-Path $run 'errors.log') -Raw
  if(-not $responsive -or $errors -or $log -match 'FAIL_CLOSED|disabled:|cleanup deferred' -or $log -notmatch '\[Mods\] loaded 1/1 mod' -or $log -notmatch 'M41B2_TEXTURED_MESH_DREW'){throw 'Native host/mesh/cleanup gate failed; preserve private logs'}
  & $python -m tools.m43_live_gate --trace $trace | Set-Content (Join-Path $run 'summary.json')
  if($LASTEXITCODE -ne 0){throw 'Actual native displacement/jump/land gate failed'}
  Write-Output "M43_NATIVE_AUTHORED_GATE_OK private_evidence=$run human_independence_requires_visual_review=true"
 } finally {if($locked){$mutex.ReleaseMutex()};$mutex.Dispose()}
} finally {Pop-Location}
