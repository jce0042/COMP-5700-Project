$ErrorActionPreference = 'Stop'

Write-Host 'Setting up Python virtual environment...'
if (-not (Test-Path '.venv')) {
    python -m venv .venv
}

$pythonExe = '.venv\Scripts\python.exe'

Write-Host 'Installing dependencies...'
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r requirements.txt

Write-Host 'Running tests...'
& $pythonExe -m pytest -q

Write-Host 'Running full 9-input workflow...'
if (Test-Path 'project-yamls.zip') {
    & $pythonExe main.py --all --project-input project-yamls.zip
} elseif (Test-Path 'YAMLfiles') {
    & $pythonExe main.py --all --project-input YAMLfiles
} else {
    throw 'Neither project-yamls.zip nor YAMLfiles directory was found.'
}

Write-Host 'TA workflow completed successfully.'
