# COMP 5700 Project

## Team Members

- Lily Edgil (jce0042@auburn.edu)

## LLM Used

- google/gemma-3-1b-it

## What This Repository Does

This project automates the full workflow described in `Instructions.md`:

1. Extract KDEs from two CIS PDF documents using zero-shot, few-shot, and chain-of-thought prompts.
2. Compare KDE YAML outputs for element name and requirement differences.
3. Map differences to Kubescape controls and run Kubescape scans.
4. Generate an executor CSV report.

The orchestrator is `main.py` and supports:

- all 9 required input combinations (`--all`)
- one specific pair (`--pdf1 ... --pdf2 ...`)
- scanning from either `project-yamls.zip` or a YAML directory via `--project-input`

## TA Quick Start (Windows PowerShell)

Run commands from the repository root.

### 1) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Run tests

```powershell
pytest -q
```

### 4) Run full workflow for all 9 required inputs

```powershell
python main.py --all --project-input project-yamls.zip
```

If the zip is not available, use the YAML directory:

```powershell
python main.py --all --project-input YAMLfiles
```

### 5) Run one specific pair

```powershell
python main.py --pdf1 cis-r1.pdf --pdf2 cis-r2.pdf --project-input project-yamls.zip
```

## One-Command Runner

You can also run:

```powershell
.\run_ta_workflow.ps1
```

This creates/uses `.venv`, installs dependencies, runs tests, and runs all 9 pairs.

## Expected Outputs

- KDE YAML outputs: `outputs/<pdf-name>/<pdf-name>-kdes.yaml`
- LLM output logs by prompt type:
	- `outputs/<pdf-name>/zero-shot/`
	- `outputs/<pdf-name>/few-shot/`
	- `outputs/<pdf-name>/chain-of-thought/`
- Comparator outputs:
	- `outputs/comparator/element_name_differences.txt`
	- `outputs/comparator/element_requirements_differences.txt`
- Executor outputs:
	- `outputs/executor/kubescape_controls.txt`
	- `outputs/executor/kubescape_scan.json`
	- `outputs/executor/kubescape_report.csv`

## Binary Build (PyInstaller)

```powershell
pyinstaller main.spec
```

Built executable:

- `dist/main.exe`

## Notes

- GitHub Actions runs tests on push and pull request to `main` via `.github/workflows/main.yml`.
- Ensure Kubescape is installed and available on PATH when running executor tasks.
