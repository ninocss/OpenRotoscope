[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Destination,
    [Parameter(Mandatory=$true)][string]$RunnerSource
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "FGT setup requires uv. Install uv from https://docs.astral.sh/uv/ and retry."
}
if (-not (Test-Path -LiteralPath $RunnerSource -PathType Leaf)) {
    throw "OpenRoto FGT runner is missing: $RunnerSource"
}

$finalRoot = [System.IO.Path]::GetFullPath($Destination)
$staging = "$finalRoot.installing"
Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $staging -Force | Out-Null
$temp = Join-Path $staging "downloads"
New-Item -ItemType Directory -Path $temp -Force | Out-Null

Write-Host "Downloading official FGT source..."
$sourceZip = Join-Path $temp "FGT.zip"
Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/hitachinsk/FGT/archive/refs/heads/master.zip" -OutFile $sourceZip
Expand-Archive -LiteralPath $sourceZip -DestinationPath $temp -Force
$expanded = Get-ChildItem -LiteralPath $temp -Directory | Where-Object { $_.Name -like "FGT-*" } | Select-Object -First 1
if (-not $expanded) { throw "Could not unpack the official FGT source archive." }
$source = Join-Path $staging "source"
Move-Item -LiteralPath $expanded.FullName -Destination $source

Write-Host "Creating isolated Python 3.8 FGT runtime..."
$venv = Join-Path $staging ".venv"
uv venv $venv --python 3.8 --clear
if ($LASTEXITCODE -ne 0) { throw "uv could not create the FGT Python 3.8 runtime." }
$python = Join-Path $venv "Scripts\python.exe"

Write-Host "Installing FGT CUDA/PyTorch runtime..."
uv pip install --python $python `
    "torch==1.10.1+cu113" "torchvision==0.11.2+cu113" `
    --index-url "https://download.pytorch.org/whl/cu113"
if ($LASTEXITCODE -ne 0) { throw "Could not install the FGT PyTorch runtime." }

uv pip install --python $python `
    "numpy==1.23.5" `
    "scipy==1.10.1" `
    "scikit-image==0.19.3" `
    "Pillow==9.5.0" `
    "PyYAML==6.0.1" `
    "imageio==2.31.6" `
    "imageio-ffmpeg==0.4.9" `
    "opencv-python==4.8.1.78" `
    "tensorboardX==2.6.2.2" `
    "cvbase==0.5.5" `
    "huggingface-hub>=0.27,<1"
if ($LASTEXITCODE -ne 0) { throw "Could not install the FGT Python dependencies." }

Write-Host "Downloading official MIT-licensed FGT pretrained weights..."
$weights = Join-Path $staging "weights"
$downloadCode = "from huggingface_hub import snapshot_download; snapshot_download('hitachinsk/FGT', local_dir=r'''$weights''')"
& $python -c $downloadCode
if ($LASTEXITCODE -ne 0) { throw "Could not download hitachinsk/FGT from Hugging Face." }

$fgtCheckpoint = Join-Path $source "FGT\checkpoint"
$lafcCheckpoint = Join-Path $source "LAFC\checkpoint"
$raftCheckpoint = Join-Path $source "LAFC\flowCheckPoint"
New-Item -ItemType Directory -Path $fgtCheckpoint -Force | Out-Null
New-Item -ItemType Directory -Path $lafcCheckpoint -Force | Out-Null
New-Item -ItemType Directory -Path $raftCheckpoint -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $weights "fgt.pth.tar") -Destination (Join-Path $fgtCheckpoint "fgt.pth.tar") -Force
Copy-Item -LiteralPath (Join-Path $weights "FGT_config.yaml") -Destination (Join-Path $fgtCheckpoint "config.yaml") -Force
Copy-Item -LiteralPath (Join-Path $weights "lafc.pth.tar") -Destination (Join-Path $lafcCheckpoint "lafc.pth.tar") -Force
Copy-Item -LiteralPath (Join-Path $weights "LAFC_config.yaml") -Destination (Join-Path $lafcCheckpoint "config.yaml") -Force

Write-Host "Downloading the official RAFT pretrained model used by FGT..."
$raftZip = Join-Path $temp "raft-models.zip"
$raftExtract = Join-Path $temp "raft-models"
Invoke-WebRequest -UseBasicParsing -Uri "https://dl.dropboxusercontent.com/s/4j4z58wuv8o0mfz/models.zip" -OutFile $raftZip
Expand-Archive -LiteralPath $raftZip -DestinationPath $raftExtract -Force
$raftThings = Get-ChildItem -LiteralPath $raftExtract -Recurse -File -Filter "raft-things.pth" | Select-Object -First 1
if (-not $raftThings) { throw "The official RAFT archive did not contain raft-things.pth." }
Copy-Item -LiteralPath $raftThings.FullName -Destination (Join-Path $raftCheckpoint "raft-things.pth") -Force

Copy-Item -LiteralPath $RunnerSource -Destination (Join-Path $staging "fgt_runner.py") -Force
Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Validating the FGT runtime..."
& $python -c "import torch, cv2, imageio, scipy, skimage; print('CUDA:', torch.cuda.is_available(), torch.__version__)"
if ($LASTEXITCODE -ne 0) { throw "FGT runtime validation failed." }

Remove-Item -LiteralPath $finalRoot -Recurse -Force -ErrorAction SilentlyContinue
Move-Item -LiteralPath $staging -Destination $finalRoot
$manifest = [ordered]@{
    id = "fgt"
    python = (Join-Path $finalRoot ".venv\Scripts\python.exe")
    runner = (Join-Path $finalRoot "fgt_runner.py")
    source = (Join-Path $finalRoot "source")
    license = "MIT"
    upstream = "https://github.com/hitachinsk/FGT"
    model = "https://huggingface.co/hitachinsk/FGT"
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $finalRoot "backend.json") -Encoding UTF8
Write-Host "FGT backend installed at $finalRoot"
