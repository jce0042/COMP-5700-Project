# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import os
import pandas as pd
import pytest
from unittest.mock import patch, mock_open
from executor import (
    read_difference_files,
    determine_kubescape_controls,
    execute_kubescape,
    generate_csv_report,
)

@pytest.fixture
def setup_test_files():
    """Set up mock files for testing."""
    output_dir = "test_executor_outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    name_diff_file = os.path.join(output_dir, "name_diff.txt")
    req_diff_file = os.path.join(output_dir, "req_diff.txt")
    
    with open(name_diff_file, "w") as f:
        f.write("Some name differences")
    with open(req_diff_file, "w") as f:
        f.write("Some requirement differences with secrets")

    yield {
        "output_dir": output_dir,
        "name_diff_file": name_diff_file,
        "req_diff_file": req_diff_file,
    }

    # Teardown
    for f in [name_diff_file, req_diff_file]:
        if os.path.exists(f):
            os.remove(f)
    
    controls_file = os.path.join(output_dir, "kubescape_controls.txt")
    if os.path.exists(controls_file):
        os.remove(controls_file)
        
    scan_json = os.path.join(output_dir, "kubescape_scan.json")
    if os.path.exists(scan_json):
        os.remove(scan_json)

    csv_report = os.path.join(output_dir, "kubescape_report.csv")
    if os.path.exists(csv_report):
        os.remove(csv_report)

    if os.path.exists(output_dir):
        os.rmdir(output_dir)

def test_read_difference_files(setup_test_files):
    """Test reading difference files."""
    name_content, req_content = read_difference_files(
        setup_test_files["name_diff_file"],
        setup_test_files["req_diff_file"],
    )
    assert "Some name differences" in name_content
    assert "Some requirement differences with secrets" in req_content

def test_determine_kubescape_controls(setup_test_files):
    """Test determination of Kubescape controls."""
    name_content, req_content = read_difference_files(
        setup_test_files["name_diff_file"],
        setup_test_files["req_diff_file"],
    )
    
    controls = determine_kubescape_controls(
        name_content, req_content, setup_test_files["output_dir"]
    )
    
    assert "C-0012" in controls
    
    controls_file = os.path.join(setup_test_files["output_dir"], "kubescape_controls.txt")
    with open(controls_file, "r") as f:
        content = f.read()
        assert "C-0012" in content

@patch("executor.subprocess.run")
def test_execute_kubescape(mock_subprocess_run, setup_test_files):
    """Test the execution of Kubescape."""
    # Mock the subprocess call to avoid actual execution
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stdout = '{}' # Empty JSON for successful run
    mock_subprocess_run.return_value.stderr = ""

    # Create a dummy controls file
    controls_file = os.path.join(setup_test_files["output_dir"], "kubescape_controls.txt")
    with open(controls_file, "w") as f:
        f.write("C-0057")

    # Create a dummy scan results file that execute_kubescape is supposed to create
    scan_results_path = os.path.join(setup_test_files["output_dir"], "kubescape_scan.json")
    with open(scan_results_path, "w") as f:
        json_data = {
            "results": [],
            "resources": [],
            "summaryDetails": {
                "controls": {
                    "C-0057": {
                        "name": "Privileged containers",
                        "controlID": "C-0057",
                        "severity": 3,
                        "ResourceCounters": {
                            "failedResources": 1,
                            "passedResources": 1
                        },
                        "complianceScore": 50.0
                    }
                }
            }
        }
        import json
        json.dump(json_data, f)

    dummy_yamls_dir = setup_test_files["output_dir"] # Use the temp dir for this

    df = execute_kubescape(controls_file, dummy_yamls_dir, setup_test_files["output_dir"])
    
    assert not df.empty
    assert df.iloc[0]["Control name"] == "Privileged containers"


def test_generate_csv_report(setup_test_files):
    """Test the generation of the CSV report."""
    data = {
        'FilePath': ['test.yaml'],
        'Severity': ['High'],
        'Control name': ['Privileged containers'],
        'Failed resources': [1],
        'All Resources': [2],
        'Compliance score': [50.0]
    }
    df = pd.DataFrame(data)
    
    generate_csv_report(df, setup_test_files["output_dir"])
    
    csv_path = os.path.join(setup_test_files["output_dir"], "kubescape_report.csv")
    assert os.path.exists(csv_path)
    
    loaded_df = pd.read_csv(csv_path)
    assert not loaded_df.empty
    assert loaded_df.iloc[0]["Control name"] == "Privileged containers"