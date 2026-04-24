# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import os
import subprocess
import json
import pandas as pd
import re
import sys
import tempfile
import zipfile

def read_difference_files(name_diff_file, req_diff_file):
    """
    Takes the two TEXT files as input from Task-2 and reads them.
    """
    with open(name_diff_file, 'r') as f:
        name_diff_content = f.read()
    with open(req_diff_file, 'r') as f:
        req_diff_content = f.read()
    return name_diff_content, req_diff_content

def determine_kubescape_controls(name_diff_content, req_diff_content, output_dir="outputs/executor"):
    """
    Determines if there are differences and maps them to Kubescape controls.
    """
    os.makedirs(output_dir, exist_ok=True)
    controls_file_path = os.path.join(output_dir, "kubescape_controls.txt")

    if "NO DIFFERENCES" in name_diff_content and "NO DIFFERENCES" in req_diff_content:
        with open(controls_file_path, 'w') as f:
            f.write("NO DIFFERENCES FOUND")
        return "NO DIFFERENCES FOUND"

    # Manual mapping of keywords to Kubescape controls
    # This can be extended or automated with an LLM
    keyword_to_control = {
        "privileged": "C-0057",
        "hostpath": "C-0048",
        "hostnetwork": "C-0041",
        "hostpid": "C-0038",
        "seccomp": "C-0210",
        "capabilities": "C-0046",
        "networkpolicy": "C-0206",
        "secrets": "C-0012",
        "rbac": "C-0088",
    }

    detected_controls = set()
    combined_content = name_diff_content + "\n" + req_diff_content
    for keyword, control in keyword_to_control.items():
        if re.search(r'\b' + keyword + r'\b', combined_content, re.IGNORECASE):
            detected_controls.add(control)

    if not detected_controls:
        # If no specific keywords are found, fall back to a default set or all controls
        # For now, we'll indicate that no specific controls were mapped
        with open(controls_file_path, 'w') as f:
            f.write("NO SPECIFIC CONTROLS MAPPED")
        return "NO SPECIFIC CONTROLS MAPPED"


    with open(controls_file_path, 'w') as f:
        for control in detected_controls:
            f.write(control + "\n")
    
    return list(detected_controls)


def execute_kubescape(controls_file, project_yamls_dir, output_dir="outputs/executor"):
    """
    Executes the Kubescape tool from the command line.
    """
    os.makedirs(output_dir, exist_ok=True)
    scan_results_path = os.path.join(output_dir, "kubescape_scan.json")

    with open(controls_file, 'r') as f:
        content = f.read().strip()

    # Base command
    command = ["kubescape", "scan"]

    # Dynamically build the command based on the controls file content
    if "NO DIFFERENCES FOUND" in content or "NO SPECIFIC CONTROLS MAPPED" in content:
        # If no specific controls, scan all controls in the 'nsa' framework (or another default)
        print("No specific controls detected. Running Kubescape with 'nsa' framework.")
        command.extend(["framework", "nsa", project_yamls_dir, "--format", "json", "--output", scan_results_path])
    else:
        # If specific controls are listed, scan only those controls
        controls = ",".join([line for line in content.split('\n') if line])
        print(f"Specific controls detected. Running Kubescape with controls: {controls}")
        command.extend(["control", controls, project_yamls_dir, "--format", "json", "--output", scan_results_path])


    try:
        # The --output flag directs kubescape to write the JSON output to the file.
        # We don't need to capture stdout.
        result = subprocess.run(command, capture_output=True, text=True)

        # Check if the command executed successfully
        if result.returncode != 0:
            # Check if the error is "no resources found" which we can ignore
            if "no resources found to scan" in result.stderr.lower():
                print("Kubescape scan completed with a 'no resources found' warning, proceeding.")
                # Create an empty JSON file to avoid decode errors later
                with open(scan_results_path, 'w') as f:
                    json.dump([], f)
            else:
                raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)

        print("Kubescape scan completed successfully.")

    except FileNotFoundError:
        print("Error: 'kubescape' command not found. Make sure it is installed and in your PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing Kubescape: {e}")
        print(f"Command: {' '.join(command)}")
        print(f"Stderr: {e.stderr}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

    with open(scan_results_path, 'r') as f:
        try:
            scan_results = json.load(f)
        except json.JSONDecodeError:
            print("Error: Could not decode Kubescape JSON output.")
            return None
            
    # Convert to DataFrame for easier processing
    # This part needs to be adjusted based on the actual JSON structure from Kubescape
    # The following is a placeholder structure
    rows = []
    # The root of the JSON can be a list of summaries (framework scan) or a single summary object (control scan)
    summaries = []
    if isinstance(scan_results, list):
        # Framework scan returns a list of summaries, where each summary has a 'controls' key
        summaries = scan_results
    elif isinstance(scan_results, dict):
        # Control scan returns a single summary object. We can treat its 'summaryDetails' as a single summary.
        if 'summaryDetails' in scan_results:
            summaries = [scan_results['summaryDetails']]

    if not summaries:
        print("Warning: Could not find any summaries to process in the Kubescape output.")

    # Create a mapping from resourceID to file path
    resource_id_to_path = {}
    if 'resources' in scan_results:
        for resource in scan_results.get('resources', []):
            source = resource.get('source')
            if source:
                # The full path is a combination of the base path and the relative path
                full_path = os.path.join(source.get('path', ''), source.get('relativePath', ''))
                resource_id_to_path[resource.get('resourceID')] = full_path

    # Create a mapping from control ID to a set of failed file paths
    control_to_failed_paths = {}
    if 'results' in scan_results:
        for result in scan_results.get('results', []):
            resource_id = result.get('resourceID')
            file_path = resource_id_to_path.get(resource_id)
            if not file_path:
                continue # Skip if we can't find the file path for the resource

            for control in result.get('controls', []):
                if control.get('status', {}).get('status') == 'failed':
                    control_id = control.get('controlID')
                    if control_id not in control_to_failed_paths:
                        control_to_failed_paths[control_id] = set()
                    control_to_failed_paths[control_id].add(file_path)

    for summary in summaries:
        # The 'controls' key holds a dictionary of control summaries, not a list.
        # We need to iterate over the values of this dictionary.
        for control_summary in summary.get('controls', {}).values():
            control_id = control_summary.get('controlID')
            failed_file_paths = control_to_failed_paths.get(control_id, set())

            rows.append({
                'Control name': control_summary.get('name'),
                'Severity': control_summary.get('severity'),
                'Failed resources': control_summary.get('ResourceCounters', {}).get('failedResources'),
                'All Resources': control_summary.get('ResourceCounters', {}).get('passedResources', 0) + control_summary.get('ResourceCounters', {}).get('failedResources', 0),
                'Compliance score': control_summary.get('complianceScore'),
                'FilePath': ", ".join(sorted(list(failed_file_paths))) if failed_file_paths else 'N/A'
            })
    
    return pd.DataFrame(rows)


def resolve_scan_input(project_input):
    """
    Resolves project scan input to a directory path.

    Accepts either:
    - a directory containing YAML files
    - a .zip archive that will be extracted to a temp directory

    Returns:
        tuple[str, str | None]: (directory_to_scan, temp_dir_to_cleanup)
    """
    if os.path.isdir(project_input):
        return project_input, None

    if os.path.isfile(project_input) and project_input.lower().endswith(".zip"):
        temp_dir = tempfile.mkdtemp(prefix="project_yamls_")
        with zipfile.ZipFile(project_input, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
        return temp_dir, temp_dir

    raise ValueError(f"'{project_input}' is not a valid directory or .zip file.")


def generate_csv_report(df, output_dir="outputs/executor"):
    """
    Generates a CSV file from the pandas DataFrame.
    """
    if df is None or df.empty:
        print("No data to generate CSV report.")
        return

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "kubescape_report.csv")
    
    # Ensure all required columns are present
    required_columns = ['FilePath', 'Severity', 'Control name', 'Failed resources', 'All Resources', 'Compliance score']
    for col in required_columns:
        if col not in df.columns:
            df[col] = None # Add missing columns with None
            
    df = df[required_columns] # Ensure correct order
    
    df.to_csv(csv_path, index=False)
    print(f"CSV report generated at {csv_path}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Task 3: Executor for Kubescape scanning.")
    parser.add_argument("name_diff_file", help="Path to the element name differences file from Task 2.")
    parser.add_argument("req_diff_file", help="Path to the element requirements differences file from Task 2.")
    parser.add_argument("project_yamls_dir", help="Path to project YAML directory or project-yamls.zip.")
    parser.add_argument("--output-dir", default="outputs/executor", help="Directory to save execution results.")
    
    args = parser.parse_args()

    # 1. Read difference files
    name_diff, req_diff = read_difference_files(args.name_diff_file, args.req_diff_file)

    # 2. Determine controls
    controls = determine_kubescape_controls(name_diff, req_diff, args.output_dir)
    controls_file = os.path.join(args.output_dir, "kubescape_controls.txt")
    print(f"Kubescape controls determined: {controls}")

    # 3. Execute Kubescape
    extracted_temp_dir = None
    try:
        scan_target_dir, extracted_temp_dir = resolve_scan_input(args.project_yamls_dir)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    df = execute_kubescape(controls_file, scan_target_dir, args.output_dir)

    # 4. Generate CSV report
    if df is not None:
        generate_csv_report(df, args.output_dir)

    if extracted_temp_dir and os.path.isdir(extracted_temp_dir):
        import shutil
        shutil.rmtree(extracted_temp_dir, ignore_errors=True)
