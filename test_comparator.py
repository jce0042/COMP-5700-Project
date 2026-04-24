# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import os
import yaml
import pytest
from comparator import load_yaml_files, compare_element_names, compare_element_requirements

@pytest.fixture(scope="module")
def setup_test_data():
    """Set up test data and directories."""
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Define test data
    test_data1 = {
        "element1": {"name": "Element 1", "requirements": ["req1", "req2"]},
        "element2": {"name": "Element 2", "requirements": ["req3"]},
    }
    test_data2 = {
        "element1": {"name": "Element 1", "requirements": ["req1", "req3"]},
        "element3": {"name": "Element 3", "requirements": ["req4"]},
    }

    # Create test YAML files
    file1_path = os.path.join(output_dir, "test1.yaml")
    file2_path = os.path.join(output_dir, "test2.yaml")
    with open(file1_path, "w") as f:
        yaml.dump(test_data1, f)
    with open(file2_path, "w") as f:
        yaml.dump(test_data2, f)

    yield {
        "output_dir": output_dir,
        "file1_path": file1_path,
        "file2_path": file2_path,
        "data1": test_data1,
        "data2": test_data2,
    }

    # Teardown: Clean up created files and directory
    for file_path in [file1_path, file2_path]:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    name_diff_path = os.path.join(output_dir, "element_name_differences.txt")
    if os.path.exists(name_diff_path):
        os.remove(name_diff_path)

    req_diff_path = os.path.join(output_dir, "element_requirements_differences.txt")
    if os.path.exists(req_diff_path):
        os.remove(req_diff_path)

    if os.path.exists(output_dir):
        os.rmdir(output_dir)

def test_load_yaml_files(setup_test_data):
    """Test loading both YAML files together."""
    loaded_data1, loaded_data2 = load_yaml_files(
        setup_test_data["file1_path"], setup_test_data["file2_path"]
    )
    assert loaded_data1 == setup_test_data["data1"]
    assert loaded_data2 == setup_test_data["data2"]

def test_compare_element_names(setup_test_data):
    """Test the compare_element_names function."""
    output_dir = setup_test_data["output_dir"]
    file1_name = os.path.basename(setup_test_data["file1_path"])
    file2_name = os.path.basename(setup_test_data["file2_path"])
    
    compare_element_names(
        setup_test_data["data1"],
        setup_test_data["data2"],
        file1_name,
        file2_name,
        output_dir,
    )

    output_file = os.path.join(output_dir, "element_name_differences.txt")
    assert os.path.exists(output_file)
    with open(output_file, "r") as f:
        content = f.read()
        assert "Elements present only in test1.yaml:" in content
        assert "- element2" in content
        assert "Elements present only in test2.yaml:" in content
        assert "- element3" in content

def test_compare_element_requirements(setup_test_data):
    """Test the compare_element_requirements function."""
    output_dir = setup_test_data["output_dir"]
    file1_name = os.path.basename(setup_test_data["file1_path"])
    file2_name = os.path.basename(setup_test_data["file2_path"])

    compare_element_requirements(
        setup_test_data["data1"],
        setup_test_data["data2"],
        file1_name,
        file2_name,
        output_dir,
    )

    output_file = os.path.join(output_dir, "element_requirements_differences.txt")
    assert os.path.exists(output_file)
    with open(output_file, "r") as f:
        lines = f.readlines()
        # Strip newline characters for comparison
        lines = [line.strip() for line in lines]
        
        expected_lines = [
            "element2,NA",
            "element3,NA",
            "element1,req2",
            "element1,req3",
        ]
        
        # Use a set for comparison to ignore order
        assert set(lines) == set(expected_lines)

