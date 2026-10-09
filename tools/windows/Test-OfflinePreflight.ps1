#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
$repo = Convert-MsysPath $TaskRepo
if ($repo.Contains("'")) { throw 'Paths containing a single quote are unsupported.' }
Invoke-Msys "cd '$repo' && python -m unittest tests.test_observation_alignment tests.test_estimate_calibration tests.test_world_snapshot tests.test_world_coordinates -v && python -m tools.estimate_calibration --input tests/fixtures/calibration_landmarks_synthetic.json" 'offline-preflight-checks.log'
Write-Output 'VERIFIED_SYNTHETIC only: explicit authored landmarks and CMW1 fixtures. No game launched, no native calibration, calibration_ready=false.'
