# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import argparse
import os
import subprocess
import sys


DEFAULT_PDF_PAIRS = [
    ("cis-r1.pdf", "cis-r1.pdf"),
    ("cis-r1.pdf", "cis-r2.pdf"),
    ("cis-r1.pdf", "cis-r3.pdf"),
    ("cis-r1.pdf", "cis-r4.pdf"),
    ("cis-r2.pdf", "cis-r2.pdf"),
    ("cis-r2.pdf", "cis-r3.pdf"),
    ("cis-r2.pdf", "cis-r4.pdf"),
    ("cis-r3.pdf", "cis-r3.pdf"),
    ("cis-r3.pdf", "cis-r4.pdf"),
]


def run_cmd(cmd):
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def ensure_exists(path, kind="file"):
    if kind == "file" and not os.path.isfile(path):
        raise FileNotFoundError(f"Missing required file: {path}")
    if kind == "dir" and not os.path.isdir(path):
        raise FileNotFoundError(f"Missing required directory: {path}")


def run_pipeline_for_pair(pdf1, pdf2, project_input):
    python_executable = sys.executable

    ensure_exists(pdf1, "file")
    ensure_exists(pdf2, "file")

    if os.path.isdir(project_input):
        ensure_exists(project_input, "dir")
    else:
        ensure_exists(project_input, "file")

    print(f"Running analysis for: {pdf1} and {pdf2}")

    run_cmd([python_executable, "extractor.py", pdf1, pdf2])

    yaml1 = os.path.join("outputs", os.path.splitext(os.path.basename(pdf1))[0], f"{os.path.splitext(os.path.basename(pdf1))[0]}-kdes.yaml")
    yaml2 = os.path.join("outputs", os.path.splitext(os.path.basename(pdf2))[0], f"{os.path.splitext(os.path.basename(pdf2))[0]}-kdes.yaml")

    ensure_exists(yaml1, "file")
    ensure_exists(yaml2, "file")

    run_cmd([python_executable, "comparator.py", yaml1, yaml2])

    name_diff = os.path.join("outputs", "comparator", "element_name_differences.txt")
    req_diff = os.path.join("outputs", "comparator", "element_requirements_differences.txt")

    ensure_exists(name_diff, "file")
    ensure_exists(req_diff, "file")

    run_cmd([python_executable, "executor.py", name_diff, req_diff, project_input])


def main():
    parser = argparse.ArgumentParser(description="Run the full COMP 5700 pipeline.")
    parser.add_argument("--all", action="store_true", help="Run all 9 required PDF input pairs.")
    parser.add_argument("--pdf1", help="First PDF path for single run.")
    parser.add_argument("--pdf2", help="Second PDF path for single run.")
    parser.add_argument(
        "--project-input",
        default="project-yamls.zip" if os.path.isfile("project-yamls.zip") else "YAMLfiles",
        help="Path to YAML directory or project-yamls.zip for Kubescape scan.",
    )

    args = parser.parse_args()

    if args.all:
        for index, (pdf1, pdf2) in enumerate(DEFAULT_PDF_PAIRS, start=1):
            print(f"Input-{index}")
            run_pipeline_for_pair(pdf1, pdf2, args.project_input)
        return

    if args.pdf1 and args.pdf2:
        run_pipeline_for_pair(args.pdf1, args.pdf2, args.project_input)
        return

    parser.error("Use --all or provide both --pdf1 and --pdf2.")


if __name__ == "__main__":
    main()
