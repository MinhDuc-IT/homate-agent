param([string]$UnityEditor = $env:UNITY_EDITOR)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$projectPath = Join-Path $repoRoot 'apps/unity-sim'
$logDirectory = Join-Path $repoRoot '.work'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
if (-not $UnityEditor -or -not (Test-Path -LiteralPath $UnityEditor -PathType Leaf)) {
    throw 'Provide Unity Editor with WebGL Build Support: ./tools/build_unity.ps1 -UnityEditor "I:/Program Files/Unity/Hub/Editor/6000.0.38f1/Editor/Unity.exe"'
}
$webglSupport = Join-Path (Split-Path $UnityEditor -Parent) 'Data/PlaybackEngines/WebGLSupport'
foreach ($required in @('Managed/UnityEngine.CoreModule.dll', 'Variations', 'BuildTools/Emscripten')) {
    if (-not (Test-Path -LiteralPath (Join-Path $webglSupport $required))) {
        throw "WebGL Build Support is incomplete. Reinstall the matching module in Unity Hub. Missing: $required"
    }
}
$logPath = Join-Path $logDirectory 'unity-webgl.log'
$arguments = @('-batchmode', '-quit', '-projectPath', ('"' + $projectPath + '"'), '-buildTarget', 'WebGL',
    '-job-worker-count', '2', '-executeMethod', 'HomateWebGLBuild.Build', '-logFile', ('"' + $logPath + '"'))
$buildEnvironment = @{
    UPM_CACHE_ROOT = Join-Path $logDirectory 'unity-cache/upm'
    BEE_CACHE_DIRECTORY = Join-Path $logDirectory 'unity-cache/bee'
    TEMP = Join-Path $logDirectory 'unity-temp'
    TMP = Join-Path $logDirectory 'unity-temp'
}
$previousEnvironment = @{}
try {
    foreach ($entry in $buildEnvironment.GetEnumerator()) {
        $previousEnvironment[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, 'Process')
        New-Item -ItemType Directory -Force -Path $entry.Value | Out-Null
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
    }
    $process = Start-Process -FilePath $UnityEditor -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
} finally {
    foreach ($entry in $previousEnvironment.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
    }
}
if ($process.ExitCode -ne 0) { throw "Unity build failed ($($process.ExitCode)). See $logPath" }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'apps/web/public/unity/build-status.json'))) {
    throw "Unity did not produce a ready build. See $logPath"
}
Write-Host 'WebGL built. Run: docker compose up -d --build web'
