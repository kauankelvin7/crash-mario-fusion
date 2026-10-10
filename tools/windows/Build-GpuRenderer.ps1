#Requires -Version 5.1
[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$base = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0'
$upstream = Join-Path $base 'CrashBandicoot-Launcher'
$cache = Join-Path $repo '.cache/goal19-renderer'
$source = Join-Path $cache 'source'
$python = 'C:/msys64/mingw64/bin/python.exe'
$dotnet = Join-Path $base 'dotnet/dotnet.exe'
$savedEnvironment = @{}
foreach ($name in @('DOTNET_CLI_TELEMETRY_OPTOUT','DOTNET_CLI_HOME','NUGET_PACKAGES')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
Push-Location $repo
try {
    & $python -m tools.prepare_goal19_renderer --source $upstream
    if ($LASTEXITCODE -ne 0) { throw 'Original source pin/GL seam verification failed' }
    if ($CheckOnly) { return }
    New-Item -ItemType Directory -Force $cache | Out-Null
    if (-not (Test-Path -LiteralPath $source)) {
        & git clone --no-hardlinks $upstream $source
        if ($LASTEXITCODE -ne 0) { throw 'Public source clone failed' }
        & $python -m tools.prepare_m41b_host --source $upstream --private-clone $source
        if ($LASTEXITCODE -ne 0) { throw 'Pinned OutputPanel source generation failed' }
        & $python -m tools.prepare_m41b2_atlas --source $upstream --private-clone $source
        if ($LASTEXITCODE -ne 0) { throw 'Pinned atlas source generation failed' }
        & $python -m tools.prepare_goal19_renderer --source $upstream --private-clone $source
        if ($LASTEXITCODE -ne 0) { throw 'GPU source generation failed' }
    }
    & $python -m tools.prepare_goal19_renderer --source $upstream --private-clone $source --verify-only
    if ($LASTEXITCODE -ne 0) { throw 'Generated host source drift' }
    if ((& git -C $source rev-parse HEAD).Trim() -ne '224da7757920a817de2d9242416f657ab95782ea') {
        throw 'Generated clone pin differs'
    }
    $allowed = @('HostWindow.cs','MenuRegistry.cs','OriginalMarioAtlas.cs','OriginalMarioGpu.cs',
        'OriginalMarioClipFrame.cs','MarioGpuState.cs','Panels/Debug/OutputPanel.cs')
    $dirty = @(& git -C $source status --porcelain --untracked-files=all)
    if ($dirty.Count -ne $allowed.Count) { throw 'Unexpected generated source modification count' }
    foreach ($entry in $dirty) {
        if ($entry.Substring(3) -notin @($allowed | ForEach-Object { 'RecompOne.Runtime/Host/Window/' + $_ })) {
            throw 'Foreign generated source modification'
        }
    }
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $env:DOTNET_CLI_HOME = Join-Path $cache 'dotnet-home'
    $env:NUGET_PACKAGES = Join-Path $cache 'nuget'
    & $dotnet build (Join-Path $source 'RecompOne.Runtime/RecompOne.Runtime.csproj') -c Release -v quiet `
        -p:NuGetAudit=false -p:RestoreIgnoreFailedSources=true "-p:RestoreFallbackFolders=$(Join-Path $base 'nuget')" `
        -o (Join-Path $cache 'runtime')
    if ($LASTEXITCODE -ne 0) { throw 'Pinned public host GPU seam compilation failed' }
    Write-Output 'GOAL19_GPU_HOST_BUILD_OK source_only=true original_game=NOT_TESTED playable=false'
} finally {
    Pop-Location
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
}
