# タスクスケジューラからも同じ環境・同じ出力先で実行する。
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$scriptPath = Join-Path $PSScriptRoot 'jpx_universe.py'
$logDirectory = Join-Path $projectRoot 'data\jpx\logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$logFile = Join-Path $logDirectory ((Get-Date -Format 'yyyy-MM-dd') + '.log')
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python環境がありません: $pythonPath"
}
& $pythonPath $scriptPath --size 'TOPIX Core30' --size 'TOPIX Large70' --size 'TOPIX Mid400' 2>&1 |
    Tee-Object -FilePath $logFile -Append
$resultCode = $LASTEXITCODE
exit $resultCode
