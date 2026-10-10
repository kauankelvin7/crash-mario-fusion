#Requires -Version 5.1
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$cache = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion'
$root = Join-Path $cache 'M42-playable/collision-probe'
$base = Join-Path $cache 'M3-crash-pose/app'
$pins = @{
 'c1' = '256fdcef59f15a190290cc19db3fa9a707843b69'
 'CrashBandicoot-Launcher' = '224da7757920a817de2d9242416f657ab95782ea'
 'libsm64' = 'fd11813208272b4271d92bd92feb8f3fdbe61be5'
 'sm64ex' = 'd7ca2c04364a6dd0dac58b47151e04e26887e6f0'
}
foreach ($name in $pins.Keys) {
 $source = Join-Path $cache "M0/$name"
 $head = & git -C $source rev-parse HEAD
 if ($LASTEXITCODE -ne 0 -or $head -ne $pins[$name]) { throw "Wrong public source pin: $name" }
 $dirty = & git -C $source status --porcelain
 if ($LASTEXITCODE -ne 0 -or $dirty) { throw "Preserve dirty public source: $name" }
}
$seal = Get-Content (Join-Path $cache 'M3-crash-pose/observer-build.json') -Raw | ConvertFrom-Json
foreach ($name in @('CrashBandicoot.exe','CrashBandicoot.dll','RecompOne.Runtime.dll')) {
 $hash = (Get-FileHash -LiteralPath (Join-Path $base $name) -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($hash -ne $seal.hashes.PSObject.Properties[$name].Value) { throw "Sealed original drift: $name" }
}
if ($CheckOnly) { Write-Output 'COLLISION_PREFLIGHT pins=true original_seal=true game_not_run=true'; return }
if (Test-Path -LiteralPath $root) { throw 'Private probe directory exists; preserve it, never overwrite a sealed build.' }
$app = Join-Path $root 'app'
$mod = Join-Path $app 'mods/cm64-crash-collision'
New-Item -ItemType Directory -Path $mod -Force | Out-Null
foreach ($file in Get-ChildItem -LiteralPath $base -File) {
 if ($file.Extension -in @('.exe','.dll','.json','.txt','.ini') -and $file.Name -ne 'settings.json') {
  Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $app $file.Name)
 }
}
foreach ($directory in @('Recomp','Ui','runtimes')) {
 Copy-Item -LiteralPath (Join-Path $base $directory) -Destination (Join-Path $app $directory) -Recurse
}
$settings = Get-Content (Join-Path $base 'settings.json') -Raw | ConvertFrom-Json
$settings.CdPath = ''; $settings.ModsConfigured = $true; $settings.ActiveMods = @('cm64-crash-collision')
$settings.CatalogDiscovery = $false; $settings.AssetHotWatch = $false
$settings | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $app 'settings.json') -Encoding utf8
foreach ($name in @('CrashOctree.cs','CrashCollisionMod.cs','mod.json')) {
 Copy-Item -LiteralPath (Join-Path $repo "integration/crash_collision/$name") -Destination $mod
}
$hashes = @{}
foreach ($file in Get-ChildItem -LiteralPath $app -File -Recurse) {
 $relative = $file.FullName.Substring($app.Length + 1).Replace('\','/')
 $hashes[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
@{version=1;pins=$pins;hashes=$hashes;disc_copied=$false;game_cache_copied=$false;
 diagnostic_only=$true;g1_passed=$false;g2_allowed=$false} | ConvertTo-Json -Depth 6 |
 Set-Content (Join-Path $root 'probe-build.json') -Encoding utf8
Write-Output 'COLLISION_PRIVATE_BUILD source_grounded=true read_only=true original_binaries_unchanged=true'
