#Requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory)][string]$CrashDisc,
 [ValidateRange(25,90)][int]$Seconds=75, [switch]$CheckOnly, [switch]$NativeQuery)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M42-playable/collision-probe'
if ($NativeQuery) { $root = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M42-playable/native-query-probe' }
$app = Join-Path $root 'app'
$manifest = Get-Content (Join-Path $root 'probe-build.json') -Raw | ConvertFrom-Json
if ([bool]$manifest.native_query -ne $NativeQuery.IsPresent) { throw 'Wrong diagnostic mode' }
if ($manifest.version -ne 1 -or $manifest.pins.'c1' -ne '256fdcef59f15a190290cc19db3fa9a707843b69' -or
 $manifest.pins.'CrashBandicoot-Launcher' -ne '224da7757920a817de2d9242416f657ab95782ea') {
 throw 'Wrong collision source version or pin'
}
$seal = Get-Content (Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose/observer-build.json') -Raw | ConvertFrom-Json
foreach ($name in @('CrashBandicoot.exe','CrashBandicoot.dll','RecompOne.Runtime.dll')) {
 $hash = (Get-FileHash -LiteralPath (Join-Path $app $name) -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($hash -ne $seal.hashes.PSObject.Properties[$name].Value) { throw "Original sealed binary drift: $name" }
}
foreach ($property in $manifest.hashes.PSObject.Properties) {
 if ($property.Name -eq 'settings.json') { continue }
 $hash = (Get-FileHash -LiteralPath (Join-Path $app $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($hash -ne $property.Value) { throw "Private sealed file drift: $($property.Name)" }
}
$sources = if ($NativeQuery) { @('CrashOctree.cs','CrashNativeQuery.cs','CrashNativeQueryMod.cs','mod.json') }
 else { @('CrashOctree.cs','CrashCollisionMod.cs','mod.json') }
foreach ($name in $sources) {
 $relative = "mods/cm64-crash-collision/$name"
 $hash = (Get-FileHash -LiteralPath (Join-Path $repo "integration/crash_collision/$name") -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($hash -ne $manifest.hashes.PSObject.Properties[$relative].Value) { throw "Current source drift: $name" }
}
$settings = Get-Content (Join-Path $app 'settings.json') -Raw | ConvertFrom-Json
if ($settings.ModsConfigured -ne $true -or @($settings.ActiveMods).Count -ne 1 -or
 $settings.ActiveMods[0] -ne 'cm64-crash-collision') { throw 'Foreign active mod' }
$disc = (Resolve-Path -LiteralPath $CrashDisc).Path
if ([IO.Path]::GetExtension($disc).ToLowerInvariant() -notin @('.cue','.chd') -or $disc.Contains('"')) {
 throw 'Invalid owned private Crash disc path'
}
$python = 'C:/msys64/mingw64/bin/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Existing Windows Python unavailable' }
if (Get-Process -Name CrashBandicoot,CrashBandicoot.Launcher -ErrorAction SilentlyContinue) {
 throw 'Another original Crash host is running; do not launch a second game'
}
if ($NativeQuery -and -not $disc.StartsWith(
    ([IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) {
 throw 'Owned disc must remain under LOCALAPPDATA'
}
if ($CheckOnly) { Write-Output 'COLLISION_RUN_PREFLIGHT game_not_run=true g1_passed=false'; return }
$run = Join-Path $root ('run-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run | Out-Null
$old = $env:CM64_COLLISION_PROBE
$oldNative = $env:CM64_NATIVE_QUERY_PROBE
$env:CM64_COLLISION_PROBE = if ($NativeQuery) { $null } else { '1' }
$env:CM64_NATIVE_QUERY_PROBE = if ($NativeQuery) { '1' } else { $null }
try {
 $process = Start-Process -FilePath (Join-Path $app 'CrashBandicoot.exe') -WorkingDirectory $app -WindowStyle Hidden -PassThru -ArgumentList @('--run',('"' + $disc + '"')) -RedirectStandardOutput (Join-Path $run 'host.log') -RedirectStandardError (Join-Path $run 'errors.log')
 Write-Output "COLLISION_PRIVATE_PID=$($process.Id) budget_seconds=$Seconds"
 $responsive = $false
 try {
  Start-Sleep -Seconds $Seconds
  $process.Refresh()
  if (-not $process.HasExited) { $responsive = $process.Responding }
 } finally {
  $process.Refresh()
  if (-not $process.HasExited) { Stop-Process -Id $process.Id; $process.WaitForExit(5000) | Out-Null }
 }
} finally { $env:CM64_COLLISION_PROBE = $old; $env:CM64_NATIVE_QUERY_PROBE = $oldNative }
Push-Location $repo
try {
 if ($NativeQuery) {
  $receiptCount = 0
  $reason = 'NO_ORIGINAL_QUERY_RECEIPTS'
  try {
   foreach ($line in Get-Content -LiteralPath (Join-Path $run 'host.log')) {
    if (-not $line.StartsWith('CM64_NATIVE_QUERY ')) { continue }
    $record = $line.Substring(18) | ConvertFrom-Json
    if ($record.version -ne 1 -or $record.sequence -ne ($receiptCount + 1) -or $receiptCount -ge 24 -or
        $record.phase -ne 'ORIGINAL_QUERY_RETURN' -or
        $record.c1Pin -ne $manifest.pins.c1 -or
        $record.launcherPin -ne $manifest.pins.'CrashBandicoot-Launcher' -or
        $record.receipt.SurfacesAllowed -ne $false -or
        $record.receipt.AllocationGenerationKnown -ne $false -or
        $record.receipt.NativeFrameKnown -ne $false -or
        $record.receipt.MaterialMappingKnown -ne $false) { throw 'Invalid native receipt' }
    ++$receiptCount
   }
   if ($receiptCount -gt 0) { $reason = 'ORIGINAL_QUERY_DIAGNOSTIC_ONLY' }
  } catch { $receiptCount = 0; $reason = 'INVALID_NATIVE_RECEIPT' }
  $audit = @{status='BLOCKED';reason=$reason;native_query_receipts=$receiptCount;
   g1_passed=$false;g2_allowed=$false;physical_contact_verified=$false} | ConvertTo-Json -Compress
  $auditCode = 2
 } else {
  $audit = & $python -m tools.assess_crash_collision --private-log (Join-Path $run 'host.log')
  $auditCode = $LASTEXITCODE
 }
 $audit | Set-Content (Join-Path $run 'audit.json') -Encoding utf8
 Write-Output $audit
} finally { Pop-Location }
$loaded = [bool](Select-String -LiteralPath (Join-Path $run 'host.log') -Pattern '\[Mods\] loaded 1/1 mod' -Quiet)
$errors = (Get-Item -LiteralPath (Join-Path $run 'errors.log')).Length
@{version=1;responsive=$responsive;mod_loaded=$loaded;stderr_bytes=$errors;gate_exit=$auditCode;
 g1_passed=$false;g2_allowed=$false;assets_uploaded=$false} | ConvertTo-Json |
 Set-Content (Join-Path $run 'summary.json') -Encoding utf8
Write-Output "G1_BLOCKED responsive=$responsive mod_loaded=$loaded gate_exit=$auditCode triangles=false"
exit 2
