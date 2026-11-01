# 납품용 폴더를 만듭니다: products\local-llm-demo\dist\사내AI비서\ 와 같은 이름의 zip
# 사용법(저장소 루트): powershell -ExecutionPolicy Bypass -File products\local-llm-demo\package\build.ps1
$ErrorActionPreference = "Stop"
$pkg = Split-Path -Parent $MyInvocation.MyCommand.Path
$demo = Split-Path -Parent $pkg
$root = Split-Path -Parent (Split-Path -Parent $demo)
$python = Join-Path $root ".venv\Scripts\python.exe"
$name = "사내AI비서"
$out = Join-Path $demo "dist\$name"
$work = Join-Path $env:TEMP "llm-demo-build"

& $python -m PyInstaller --noconfirm --onefile --console --name $name `
    --hidden-import pypdf --distpath $work --workpath "$work\build" --specpath $work (Join-Path $demo "app.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 실패" }

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory $out | Out-Null
Copy-Item (Join-Path $work "$name.exe") $out
Copy-Item (Join-Path $pkg "setup.ps1"), (Join-Path $pkg "설치.bat"), (Join-Path $pkg "config.json"), (Join-Path $pkg "사용안내.txt"), (Join-Path $pkg "확인질문.txt") $out
Copy-Item (Join-Path $demo "docs") (Join-Path $out "docs") -Recurse

$zip = Join-Path $demo "dist\$name.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $out -DestinationPath $zip
Get-ChildItem $out | Select-Object Name, Length
"zip: $zip ($([math]::Round((Get-Item $zip).Length / 1MB, 1)) MB)"
