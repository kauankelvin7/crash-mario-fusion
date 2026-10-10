#Requires -Version 7.0
<#
.SYNOPSIS
Run bounded original Crash host with embedded libsm64 physics in a private app.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$MarioRom,
    [Parameter(Mandatory)][string]$CrashDisc,
    [ValidateRange(20,120)][int]$Seconds = 40,
    [switch]$RequirePreview,
    [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root=Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M4-embed'
$app=Join-Path $root 'crash-app'
$manifest=Get-Content -LiteralPath (Join-Path $root 'embedded-build.json') -Raw|ConvertFrom-Json
if($manifest.libsm64_pin -ne 'fd11813208272b4271d92bd92feb8f3fdbe61be5' -or $manifest.crash_pin -ne '224da7757920a817de2d9242416f657ab95782ea'){
    throw 'Unknown pinned source revisions'
}
$source=Join-Path $repo 'integration/embedded_mario'
foreach($n in @('Interop.cs','CrashEmbeddedMarioMod.cs','OriginalMarioPreview.cs','mod.json')){
    $h=(Get-FileHash -LiteralPath (Join-Path $source $n) -Algorithm SHA256).Hash.ToLowerInvariant()
    if($h -ne $manifest.source_hashes.PSObject.Properties[$n].Value){throw "Source differs from prepared private manifest: $n"}
    $installed=(Get-FileHash -LiteralPath (Join-Path $app "mods/cm64-embedded-mario/$n") -Algorithm SHA256).Hash.ToLowerInvariant()
    if($h -ne $installed){throw "Private installed mod differs: $n"}
}
$hash=(Get-FileHash -LiteralPath (Join-Path $app 'sm64.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
if($hash -ne $manifest.dll_sha256){throw 'Private native DLL differs from prepared build'}
$seal=Get-Content -LiteralPath (Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose/observer-build.json') -Raw | ConvertFrom-Json
foreach($n in @('CrashBandicoot.exe','CrashBandicoot.dll','RecompOne.Runtime.dll')){
    $h=(Get-FileHash -LiteralPath (Join-Path $app $n) -Algorithm SHA256).Hash.ToLowerInvariant()
    if($h -ne $seal.hashes.PSObject.Properties[$n].Value){throw "Original Crash runtime changed: $n"}
}
$settings=Get-Content -LiteralPath (Join-Path $app 'settings.json') -Raw | ConvertFrom-Json
if($settings.ModsConfigured -ne $true -or @($settings.ActiveMods).Count -ne 1 -or
   @($settings.ActiveMods)[0] -ne 'cm64-embedded-mario'){
    throw 'Unexpected enabled mod(s) in private host'
}
$rom=(Resolve-Path -LiteralPath $MarioRom -ErrorAction Stop).Path
$disc=(Resolve-Path -LiteralPath $CrashDisc -ErrorAction Stop).Path
if((Get-Item -LiteralPath $rom).Length -ne 8388608 -or
   (Get-FileHash -LiteralPath $rom -Algorithm SHA1).Hash.ToLowerInvariant() -ne
   '9bef1128717f958171a4afac3ed78ee2bb4e86ce'){
    throw 'Owned original Super Mario US ROM failed size/SHA1 pin'
}
if([IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue','.chd') -or
   -not (Test-Path -LiteralPath $disc -PathType Leaf)){
    throw 'Owned local Crash .cue/.chd required'
}
if($CheckOnly){
    Write-Output 'HOSTED_MARIO_PREFLIGHT_OK hashes=true runtime_NOT_TESTED'
    return
}
$log=Join-Path $root ('run-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $log | Out-Null
$envs=@{CM64_EMBED_ENABLE='1';CM64_EMBED_ROM=$rom;PATH=('C:/msys64/mingw64/bin;'+$env:PATH)}
$p=Start-Process -FilePath (Join-Path $app 'CrashBandicoot.exe') -WorkingDirectory $app -ArgumentList @('--run',('"'+$disc+'"')) -Environment $envs -RedirectStandardOutput (Join-Path $log 'host.log') -RedirectStandardError (Join-Path $log 'errors.log') -PassThru
$responsive=$false
try {
    Start-Sleep -Seconds $Seconds
    $p.Refresh()
    if(-not $p.HasExited){$responsive=$p.Responding}
}
finally {
    $p.Refresh()
    if(-not $p.HasExited){
        Stop-Process -Id $p.Id -ErrorAction SilentlyContinue
        $p.WaitForExit(5000)|Out-Null
    }
}
$lines=Get-Content (Join-Path $log 'host.log') -ErrorAction SilentlyContinue
$errors=@(Get-Content (Join-Path $log 'errors.log') -ErrorAction SilentlyContinue)
$init=[bool]($lines|Where-Object {$_ -match '\[cm64-embedded\] INIT_OK'})
$solver=[bool]($lines|Where-Object {$_ -match '\[cm64-embedded\] HOST_SOLVER frames=180 mesh_frames=180 moving_frames=101'})
$failure=[bool]($lines|Where-Object {$_ -match '\[cm64-embedded\] FAIL_CLOSED'})
$preview=[bool]($lines|Where-Object {$_ -match '\[cm64-embedded\] M41_PREVIEW_DREW native_mesh=true original_triangles=[1-9][0-9]* guest_window=true shared_scene=false'})
$ok=$init -and $solver -and -not $failure -and $errors.Count -eq 0 -and $responsive -and (-not $RequirePreview -or $preview)
@{schema_version=1;passed=$ok;host_responsive=$responsive;native_init=$init;native_solver=$solver;
  guest_mesh_preview=$preview;physical_status='BLOCKED';shared_geometry=$false;shared_rendering=$false
 }|ConvertTo-Json|Set-Content (Join-Path $log 'summary.json') -Encoding utf8
Write-Output "HOSTED_MARIO_RESULT passed=$ok init=$init solver=$solver preview=$preview responsive=$responsive physical=BLOCKED"
if(-not $ok){throw 'Host solver gate failed: private logs retained'}
