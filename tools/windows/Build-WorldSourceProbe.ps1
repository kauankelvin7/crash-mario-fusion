#Requires -Version 7.0
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$root = Join-Path $repo '.cache/m42-g1'
$source = Join-Path $root 'world-source-reviewed'
$m0 = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0'
$upstream = Join-Path $m0 'CrashBandicoot-Launcher'
$dotnet = Join-Path $m0 'dotnet/dotnet.exe'
$python = 'C:/msys64/mingw64/bin/python.exe'
$pin = '224da7757920a817de2d9242416f657ab95782ea'
$sourcePins = @('--c1', (Join-Path $m0 'c1'), '--libsm64', (Join-Path $m0 'libsm64'))
foreach ($path in @($python, $dotnet, (Join-Path $upstream 'RecompOne.Runtime/Hardware/Gte.cs'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing pinned local tool/source: $path" }
}
if ((& git -C $upstream rev-parse HEAD).Trim() -ne $pin -or (& git -C $upstream status --porcelain)) {
    throw 'Preserve dirty or unpinned original launcher'
}
Push-Location $repo
try {
    & $python -m tools.prepare_world_source_probe --source $upstream --private-clone $source @sourcePins --check-target-only
    if ($LASTEXITCODE -ne 0) { throw 'Private build root escapes workspace' }
} finally { Pop-Location }
if ($CheckOnly) { Write-Output 'G1_PREFLIGHT_OK original_game_NOT_TESTED'; return }
New-Item -ItemType Directory -Force $root | Out-Null
$env:DOTNET_CLI_HOME = Join-Path $root 'dotnet-home'
$env:NUGET_PACKAGES = Join-Path $root 'nuget'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
$env:TEMP = Join-Path $root 'tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
Push-Location $repo
try {
    if (-not (Test-Path -LiteralPath $source)) {
        & git clone --no-hardlinks $upstream $source
        if ($LASTEXITCODE -ne 0) { throw 'Private public-source clone failed; no fallback download' }
        & $python -m tools.prepare_m41b_host --source $upstream --private-clone $source
        if ($LASTEXITCODE -ne 0) { throw 'Existing original output pipeline preparation failed' }
        & $python -m tools.prepare_m41b2_atlas --source $upstream --private-clone $source
        if ($LASTEXITCODE -ne 0) { throw 'Existing original Mario texture pipeline preparation failed' }
        & $python -m tools.prepare_world_source_probe --source $upstream --private-clone $source @sourcePins
        if ($LASTEXITCODE -ne 0) { throw 'Pinned original GTE/OT probe adaptation failed' }
    }
    & $python -m tools.prepare_m41b2_atlas --source $upstream --private-clone $source --verify-only
    if ($LASTEXITCODE -ne 0) { throw 'Mario atlas owner source drift' }
    & $python -m tools.prepare_world_source_probe --source $upstream --private-clone $source @sourcePins --verify-only
    if ($LASTEXITCODE -ne 0) { throw 'G1 source drift' }
    $expected = @('RecompOne.Runtime/Dispatch/Dispatcher.cs', 'RecompOne.Runtime/Hardware/Gte.cs',
        'RecompOne.Runtime/Memory/Dma.cs', 'RecompOne.Runtime/Memory/PSMemory.cs',
        'RecompOne.Runtime/Hardware/CrashWorldSourceProbe.cs', 'RecompOne.Runtime/Host/Window/MenuRegistry.cs',
        'RecompOne.Runtime/Host/Window/HostWindow.cs', 'RecompOne.Runtime/Host/Window/OriginalMarioAtlas.cs',
        'RecompOne.Runtime/Host/Window/Panels/Debug/OutputPanel.cs')
    $changed = @(& git -C $source status --porcelain | ForEach-Object { $_.Substring(3).Replace('\', '/') })
    if ($LASTEXITCODE -ne 0 -or $changed.Count -ne $expected.Count -or
        @($changed | Where-Object { $_ -notin $expected }).Count) { throw 'Unknown private source changes; preserve clone' }
    $project = Join-Path $source 'RecompOne.Runtime/RecompOne.Runtime.csproj'
    & $dotnet restore $project --source (Join-Path $m0 'nuget') -p:NuGetAudit=false -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Offline native runtime restore failed; no network fallback' }
    & $dotnet build $project --no-restore -c Release -o (Join-Path $root 'runtime') -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Native private runtime compilation failed' }
    $env:CM64_WORLD_SOURCE_PROBE = '1'
    & $dotnet run --project (Join-Path $repo 'tests/native_world_probe/WorldProbeFixture.csproj') -p:CrashSource=$upstream -p:NuGetAudit=false -v quiet | Tee-Object (Join-Path $root 'fixture.log')
    if ($LASTEXITCODE -ne 0) { throw 'Asset-free original GTE/probe fixture failed' }
    & $python -m tools.assess_world_source_probe (Join-Path $root 'fixture.log')
    if ($LASTEXITCODE -ne 0) { throw 'Native synthetic GTE receipt audit failed' }
    $fixture = Join-Path $repo 'tests/native_world_probe/bin/Debug/net10.0/WorldProbeFixture.dll'
    & $dotnet $fixture rotated | Tee-Object (Join-Path $root 'fixture-rotated.log')
    if ($LASTEXITCODE -ne 0) { throw 'Native nontrivial matrix fixture failed' }
    & $python -m tools.assess_world_source_probe (Join-Path $root 'fixture-rotated.log')
    if ($LASTEXITCODE -ne 0) { throw 'Native nontrivial matrix reprojection failed' }
    & $dotnet $fixture gt3 | Tee-Object (Join-Path $root 'fixture-gt3.log')
    if ($LASTEXITCODE -ne 0) { throw 'Native textured packet fixture failed' }
    & $python -m tools.assess_world_source_probe (Join-Path $root 'fixture-gt3.log')
    if ($LASTEXITCODE -ne 0) { throw 'Native textured packet reprojection failed' }
    $scenarios = @('no-ot', 'bad-ot', 'paused', 'wrong-call', 'bad-scratch', 'bad-vertex',
        'saturated', 'frame-drift', 'zone-drift', 'missing-link', 'bad-sxy', 'ot-reset', 'guest-throw',
        'bad-matrix', 'camera-drift', 'zone-header-drift', 'zone-magic-drift', 'world-count-drift', 'poly-id-drift')
    foreach ($scenario in $scenarios) {
        $output = @(& $dotnet $fixture $scenario)
        if ($LASTEXITCODE -ne 0 -or @($output | Where-Object { $_.StartsWith('[cm64-world]') }).Count -ne 0 -or
            @($output | Where-Object { $_ -match 'memory_gte_unchanged=true' }).Count -ne 1) {
            throw "Native probe negative fixture failed: $scenario"
        }
    }
    $env:CM64_WORLD_SOURCE_PROBE = '0'
    $output = @(& $dotnet $fixture valid)
    if ($LASTEXITCODE -ne 0 -or @($output | Where-Object { $_.StartsWith('[cm64-world]') }).Count -ne 0) {
        throw 'Native probe opt-out failed'
    }
    Write-Output 'G1_NATIVE_NEGATIVE_FIXTURES_OK cases=20 original_game_NOT_TESTED'
    @{
        schema = 1; evidence = 'VERIFIED_SYNTHETIC'; original_game_run = $false
        source_pin = $pin; repo_head = (& git -C $repo rev-parse HEAD).Trim()
        c1_pin = '256fdcef59f15a190290cc19db3fa9a707843b69'; libsm64_pin = 'fd11813208272b4271d92bd92feb8f3fdbe61be5'
        dotnet_sdk = (& $dotnet --version).Trim(); positive_fixtures = 3; negative_optout_fixtures = 20
        probe_sha256 = (Get-FileHash (Join-Path $repo 'integration/embedded_mario/CrashWorldSourceProbe.cs') -Algorithm SHA256).Hash.ToLowerInvariant()
        runtime_sha256 = (Get-FileHash (Join-Path $root 'runtime/RecompOne.Runtime.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
    } | ConvertTo-Json | Set-Content (Join-Path $root 'build-evidence.json') -Encoding utf8
} finally { Pop-Location }
Write-Output 'VERIFIED_SYNTHETIC G1_NATIVE_BUILD_OK texture_pipeline_preserved=true original_game_NOT_TESTED'
