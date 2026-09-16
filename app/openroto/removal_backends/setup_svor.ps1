[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Destination,
    [Parameter(Mandatory=$true)][string]$RunnerSource
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "SVOR setup requires uv. Install uv from https://docs.astral.sh/uv/ and retry."
}
if (-not (Test-Path -LiteralPath $RunnerSource -PathType Leaf)) {
    throw "OpenRoto SVOR runner is missing: $RunnerSource"
}

$finalRoot = [System.IO.Path]::GetFullPath($Destination)
$staging = "$finalRoot.installing"
Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $staging -Force | Out-Null
$temp = Join-Path $staging "downloads"
New-Item -ItemType Directory -Path $temp -Force | Out-Null

Write-Host "Downloading official SVOR source..."
$sourceZip = Join-Path $temp "SVOR.zip"
Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/xiaomi-research/svor/archive/refs/heads/main.zip" -OutFile $sourceZip
Expand-Archive -LiteralPath $sourceZip -DestinationPath $temp -Force
$expanded = Get-ChildItem -LiteralPath $temp -Directory | Where-Object { $_.Name -like "svor-*" } | Select-Object -First 1
if (-not $expanded) { throw "Could not unpack the official SVOR source archive." }
$source = Join-Path $staging "source"
Move-Item -LiteralPath $expanded.FullName -Destination $source

Write-Host "Creating isolated Python 3.10 SVOR runtime..."
$venv = Join-Path $staging ".venv"
uv venv $venv --python 3.10 --clear
if ($LASTEXITCODE -ne 0) { throw "uv could not create the SVOR Python 3.10 runtime." }
$python = Join-Path $venv "Scripts\python.exe"

Write-Host "Installing the SVOR PyTorch runtime..."
uv pip install --python $python `
    "torch==2.7.0" "torchvision==0.22.0" "torchaudio==2.7.0" "xformers==0.0.30"
if ($LASTEXITCODE -ne 0) { throw "Could not install the SVOR PyTorch runtime." }

uv pip install --python $python -r (Join-Path $source "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install the SVOR Python dependencies." }
uv pip install --python $python "huggingface-hub>=0.30,<1"
if ($LASTEXITCODE -ne 0) { throw "Could not install Hugging Face model download support." }

$modelRoot = Join-Path $source "models"
New-Item -ItemType Directory -Path $modelRoot -Force | Out-Null
$wanRoot = Join-Path $modelRoot "Wan2.1-VACE-1.3B"
$svorWeights = Join-Path $staging "svor-weights"

Write-Host "Downloading Wan2.1-VACE-1.3B. This is a large model and can take a while..."
$wanCode = "from huggingface_hub import snapshot_download; snapshot_download('Wan-AI/Wan2.1-VACE-1.3B', local_dir=r'''$wanRoot''')"
& $python -c $wanCode
if ($LASTEXITCODE -ne 0) { throw "Could not download Wan-AI/Wan2.1-VACE-1.3B." }

Write-Host "Downloading SVOR LoRA weights..."
$svorCode = "from huggingface_hub import snapshot_download; snapshot_download('HigherHu/SVOR', local_dir=r'''$svorWeights''')"
& $python -c $svorCode
if ($LASTEXITCODE -ne 0) { throw "Could not download HigherHu/SVOR." }
Copy-Item -LiteralPath (Join-Path $svorWeights "remove_model_stage1.safetensors") -Destination (Join-Path $modelRoot "remove_model_stage1.safetensors") -Force
Copy-Item -LiteralPath (Join-Path $svorWeights "remove_model_stage2.safetensors") -Destination (Join-Path $modelRoot "remove_model_stage2.safetensors") -Force
Remove-Item -LiteralPath $svorWeights -Recurse -Force -ErrorAction SilentlyContinue

Copy-Item -LiteralPath $RunnerSource -Destination (Join-Path $staging "svor_runner.py") -Force
Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Validating the SVOR runtime..."
& $python -c "import torch, diffusers, transformers, cv2, imageio; print('CUDA:', torch.cuda.is_available(), torch.__version__)"
if ($LASTEXITCODE -ne 0) { throw "SVOR runtime validation failed." }

Remove-Item -LiteralPath $finalRoot -Recurse -Force -ErrorAction SilentlyContinue
Move-Item -LiteralPath $staging -Destination $finalRoot
$manifest = [ordered]@{
    id = "svor"
    python = (Join-Path $finalRoot ".venv\Scripts\python.exe")
    runner = (Join-Path $finalRoot "svor_runner.py")
    source = (Join-Path $finalRoot "source")
    license = "Apache-2.0"
    upstream = "https://github.com/xiaomi-research/svor"
    model = "https://huggingface.co/HigherHu/SVOR"
    base_model = "https://huggingface.co/Wan-AI/Wan2.1-VACE-1.3B"
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $finalRoot "backend.json") -Encoding UTF8
Write-Host "SVOR backend installed at $finalRoot"
