#Requires -Version 5.1
[CmdletBinding()]
param([switch]$Gpu)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$base = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0'
$cache = Join-Path $repo '.cache/goal19-renderer'
$source = Join-Path $cache 'source'
$python = 'C:/msys64/mingw64/bin/python.exe'
$dotnet = Join-Path $base 'dotnet/dotnet.exe'
$gcc = 'C:/msys64/mingw64/bin/gcc.exe'
$savedEnvironment = @{}
foreach ($name in @('DOTNET_CLI_TELEMETRY_OPTOUT','DOTNET_CLI_HOME','NUGET_PACKAGES',
    'CM64_C1_ROOT','CM64_SM64EX_ROOT','CM64_CRASH_HOST_ROOT','TMP','TEMP','PATH')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
New-Item -ItemType Directory -Force (Join-Path $cache 'logs'), (Join-Path $cache 'temp') | Out-Null
function Invoke-Check([string]$Executable, [string[]]$Arguments, [string]$Label) {
    $log = Join-Path $cache "logs/$Label.log"
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Missing tool: $Executable" }
    $ErrorActionPreference = 'Continue'
    $global:LASTEXITCODE = $null
    $result = & $Executable @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $result | Out-File -LiteralPath $log -Encoding utf8
    if ($null -eq $exitCode -or $exitCode -ne 0) { throw "$Label failed; inspect private $log" }
    Write-Output "$Label PASS"
}
Push-Location $repo
try {
    $scripts = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1')
    foreach ($script in $scripts) {
        $tokens = $null; $errors = $null
        [Management.Automation.Language.Parser]::ParseFile($script.FullName, [ref]$tokens, [ref]$errors) | Out-Null
        if ($errors.Count -ne 0) { throw "PowerShell syntax failure: $($script.Name)" }
    }
    Write-Output "PowerShell-parser PASS scripts=$($scripts.Count)"
    & (Join-Path $PSScriptRoot 'Build-GpuRenderer.ps1')
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $env:DOTNET_CLI_HOME = Join-Path $cache 'dotnet-home'
    $env:NUGET_PACKAGES = Join-Path $cache 'nuget'
    $pins = @{
        'c1' = '256fdcef59f15a190290cc19db3fa9a707843b69'
        'sm64ex' = 'd7ca2c04364a6dd0dac58b47151e04e26887e6f0'
        'libsm64' = 'fd11813208272b4271d92bd92feb8f3fdbe61be5'
    }
    foreach ($entry in $pins.GetEnumerator()) {
        if ((& git -C (Join-Path $base $entry.Key) rev-parse HEAD).Trim() -ne $entry.Value) {
            throw "Reference source pin drift: $($entry.Key)"
        }
        if (& git -C (Join-Path $base $entry.Key) status --porcelain --untracked-files=no) {
            throw "Reference tracked source drift: $($entry.Key)"
        }
    }
    $env:CM64_C1_ROOT = Join-Path $base 'c1'
    $env:CM64_SM64EX_ROOT = Join-Path $base 'sm64ex'
    $env:CM64_CRASH_HOST_ROOT = Join-Path $base 'CrashBandicoot-Launcher'
    $env:TMP = Join-Path $cache 'temp'
    $env:TEMP = $env:TMP
    $env:PATH = 'C:/msys64/mingw64/bin;' + $env:PATH
    Invoke-Check $python @('-m','unittest','discover','-s','tests','-q') 'python-regression'
    $sender = Join-Path $cache 'native-coin-sender.exe'
    Invoke-Check $gcc @('-std=c11','-Wall','-Wextra','-Werror','-Iintegration/sm64',
        'integration/sm64/cm64_coin.c','tests/integration/native_sender.c','-lws2_32','-o',$sender) 'sender-build'
    $projects = @{
        'IntegrationChecks' = 'tests/integration/IntegrationChecks.csproj'
        'CrashPoseChecks' = 'tests/crash_pose/CrashPoseChecks.csproj'
        'CrashOctree.Tests' = 'tests/CrashOctree.Tests.csproj'
        'InputTests' = 'tests/m43_input/InputTests.csproj'
        'MarioGpuChecks' = 'tests/mario_gpu/MarioGpuChecks.csproj'
    }
    foreach ($entry in $projects.GetEnumerator()) {
        $output = Join-Path $cache "contracts/$($entry.Key)"
        $buildArgs = @('build',$entry.Value,'-v','quiet',"-p:CrashRoot=$source",'-p:NuGetAudit=false',
            "-p:RestoreFallbackFolders=$(Join-Path $base 'nuget')",'-p:RestoreIgnoreFailedSources=true','-o',$output)
        if ($entry.Key -in @('InputTests','CrashOctree.Tests')) {
            $buildArgs += "-p:BaseIntermediateOutputPath=$output/obj/"
        }
        Invoke-Check $dotnet $buildArgs "$($entry.Key)-build"
        $arguments = @((Join-Path $output "$($entry.Key).dll"))
        if ($entry.Key -eq 'IntegrationChecks') { $arguments += @($repo,$sender) }
        if ($entry.Key -eq 'CrashPoseChecks') { $arguments += $repo }
        if ($entry.Key -eq 'MarioGpuChecks' -and $Gpu) { $arguments += '--gpu' }
        Invoke-Check $dotnet $arguments "$($entry.Key)-checks"
    }
    Write-Output 'GOAL19_SOURCE_WINDOWS_CHECKS_OK original_game=NOT_TESTED playable=false'
} finally {
    Pop-Location
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
}
