# 사내 AI 비서 설치 스크립트 (설치.bat이 실행합니다)
# 1) Ollama 설치  2) 그래픽카드 메모리에 맞는 모델 선택·다운로드  3) 프로그램 실행
# 설치할 때만 인터넷이 필요하고, 그 뒤에는 인터넷 없이 동작합니다.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

function Find-Ollama {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $p = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $p) { return $p }
    return $null
}

function Test-OllamaServer {
    try { Invoke-WebRequest "http://127.0.0.1:11434" -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

Write-Host "[1/4] Ollama 확인" -ForegroundColor Cyan
$ollama = Find-Ollama
if (-not $ollama) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "winget이 없어 자동 설치를 할 수 없습니다. https://ollama.com/download 에서 Windows용을 설치한 뒤 다시 실행해 주세요." -ForegroundColor Yellow
        Read-Host "Enter를 누르면 종료합니다"; exit 1
    }
    Write-Host "Ollama를 설치합니다..."
    winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements --silent
    $ollama = Find-Ollama
    if (-not $ollama) { Write-Host "Ollama 설치를 확인하지 못했습니다. PC를 다시 시작한 뒤 다시 실행해 주세요." -ForegroundColor Yellow; Read-Host "Enter"; exit 1 }
}
Write-Host "  $ollama"

Write-Host "[2/4] Ollama 실행 확인" -ForegroundColor Cyan
if (-not (Test-OllamaServer)) {
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (Test-OllamaServer); $i++) { Start-Sleep 1 }
    if (-not (Test-OllamaServer)) { Write-Host "Ollama가 시작되지 않았습니다." -ForegroundColor Yellow; Read-Host "Enter"; exit 1 }
}

Write-Host "[3/4] PC 사양에 맞는 모델 선택" -ForegroundColor Cyan
$configPath = Join-Path $here "config.json"
$config = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$vramGB = 0
try {
    $out = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null
    if ($out) { $vramGB = [math]::Floor([int]($out | Select-Object -First 1) / 1024) }
} catch {}
$model = if ($vramGB -ge 10) { "qwen3:8b" } elseif ($vramGB -ge 6) { "qwen3:4b" } else { "qwen3:1.7b" }
Write-Host "  NVIDIA 그래픽 메모리: $vramGB GB → 답변 모델 $model"
if ($vramGB -lt 6) { Write-Host "  그래픽카드가 없거나 작아 작은 모델을 씁니다. 답이 느리거나 정확도가 낮을 수 있습니다." -ForegroundColor Yellow }
$config.chat_model = $model
$config | ConvertTo-Json | Set-Content $configPath -Encoding UTF8

Write-Host "[4/4] 모델 다운로드 (처음 한 번, 수 GB)" -ForegroundColor Cyan
& $ollama pull bge-m3
& $ollama pull $model

Write-Host "설치가 끝났습니다. 프로그램을 실행합니다." -ForegroundColor Green
Start-Process -FilePath (Join-Path $here "사내AI비서.exe") -WorkingDirectory $here
