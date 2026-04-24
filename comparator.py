# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import yaml
import os

def load_yaml(file_path):
    """Load data from a single YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data

def load_yaml_files(file_path1, file_path2):
    """
    Loads two YAML files.

    Args:
        file_path1 (str): Path to the first YAML file.
        file_path2 (str): Path to the second YAML file.

    Returns:
        tuple: A tuple containing the loaded data from the two YAML files, or (None, None) if an error occurs.
    """
    try:
        data1 = load_yaml(file_path1)
        data2 = load_yaml(file_path2)
        return data1, data2
    except FileNotFoundError as e:
        print(f"Error: {e.strerror}: {e.filename}")
        return None, None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None, None

def compare_element_names(data1, data2, filename1, filename2, output_dir="outputs/comparator"):
    """
    Compares the names of key data elements between two YAML files and writes the differences to a text file.

    Args:
        data1 (dict): The data from the first YAML file.
        data2 (dict): The data from the second YAML file.
        filename1 (str): The name of the first file.
        filename2 (str): The name of the second file.
        output_dir (str): The directory to save the output file.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "element_name_differences.txt")

    keys1 = set(data1.keys())
    keys2 = set(data2.keys())

    unique_to_1 = keys1 - keys2
    unique_to_2 = keys2 - keys1

    with open(output_path, 'w', encoding='utf-8') as f:
        if not unique_to_1 and not unique_to_2:
            f.write("NO DIFFERENCES IN REGARDS TO ELEMENT NAMES\n")
        else:
            if unique_to_1:
                f.write(f"Elements present only in {filename1}:\n")
                for key in sorted(unique_to_1):
                    f.write(f"- {key}\n")
            if unique_to_2:
                f.write(f"\nElements present only in {filename2}:\n")
                for key in sorted(unique_to_2):
                    f.write(f"- {key}\n")

def compare_element_requirements(data1, data2, filename1, filename2, output_dir="outputs/comparator"):
    """
    Compares key data elements and their requirements between two YAML files and writes the differences to a text file.

    Args:
        data1 (dict): The data from the first YAML file.
        data2 (dict): The data from the second YAML file.
        filename1 (str): The name of the first file.
        filename2 (str): The name of the second file.
        output_dir (str): The directory to save the output file.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "element_requirements_differences.txt")

    keys1 = set(data1.keys())
    keys2 = set(data2.keys())

    all_keys = sorted(keys1 | keys2)
    differences = []

    for key in all_keys:
        in1 = key in data1
        in2 = key in data2

        if in1 and not in2:
            differences.append(f"{key},NA")
        elif not in1 and in2:
            differences.append(f"{key},NA")
        elif in1 and in2:
            reqs1 = set(data1[key].get('requirements', []))
            reqs2 = set(data2[key].get('requirements', []))

            unique_reqs1 = reqs1 - reqs2
            unique_reqs2 = reqs2 - reqs1

            for req in sorted(unique_reqs1):
                differences.append(f"{key},{req}")
            for req in sorted(unique_reqs2):
                differences.append(f"{key},{req}")

    with open(output_path, 'w', encoding='utf-8') as f:
        if not differences:
            f.write("NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS\n")
        else:
            for diff in sorted(set(differences)):
                f.write(f"{diff}\n")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Compare two YAML files for differences in key data elements.")
    parser.add_argument("yaml_file1", help="Path to the first YAML file.")
    parser.add_argument("yaml_file2", help="Path to the second YAML file.")
    parser.add_argument("--output-dir", default="outputs/comparator", help="Directory to save comparison results.")
    args = parser.parse_args()

    data1, data2 = load_yaml_files(args.yaml_file1, args.yaml_file2)

    if data1 is not None and data2 is not None:
        filename1 = os.path.basename(args.yaml_file1)
        filename2 = os.path.basename(args.yaml_file2)

        compare_element_names(data1, data2, filename1, filename2, args.output_dir)
        print(f"Element name comparison saved to {os.path.join(args.output_dir, 'element_name_differences.txt')}")

        compare_element_requirements(data1, data2, filename1, filename2, args.output_dir)
        print(f"Element requirements comparison saved to {os.path.join(args.output_dir, 'element_requirements_differences.txt')}")

