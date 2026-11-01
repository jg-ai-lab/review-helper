# 납품용 폴더를 만듭니다: products\vision-demo\dist\물건세기\ 와 같은 이름의 zip
# 먼저 .venv-vision에서 export_onnx.py로 package\model.onnx를 만들어 둡니다.
# 사용법(저장소 루트): powershell -ExecutionPolicy Bypass -File products\vision-demo\package\build.ps1
$ErrorActionPreference = "Stop"
$pkg = Split-Path -Parent $MyInvocation.MyCommand.Path
$demo = Split-Path -Parent $pkg
$root = Split-Path -Parent (Split-Path -Parent $demo)
$python = Join-Path $root ".venv\Scripts\python.exe"
$name = "물건세기"
$out = Join-Path $demo "dist\$name"
$work = Join-Path $env:TEMP "vision-demo-build"

if (-not (Test-Path (Join-Path $pkg "model.onnx"))) { throw "package\model.onnx가 없습니다. export_onnx.py를 먼저 실행하세요." }
& $python -m PyInstaller --noconfirm --onefile --console --name $name `
    --distpath $work --workpath "$work\build" --specpath $work (Join-Path $demo "count_app.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 실패" }

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory $out | Out-Null
New-Item -ItemType Directory (Join-Path $out "사진넣기") | Out-Null
Copy-Item (Join-Path $work "$name.exe") $out
Copy-Item (Join-Path $pkg "model.onnx"), (Join-Path $pkg "config.json"), (Join-Path $pkg "사용안내.txt") $out

$zip = Join-Path $demo "dist\$name.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $out -DestinationPath $zip
Get-ChildItem $out | Select-Object Name, Length
"zip: $zip ($([math]::Round((Get-Item $zip).Length / 1MB, 1)) MB)"
