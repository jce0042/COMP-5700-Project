# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import PyPDF2
import os
import yaml
from transformers import pipeline
import torch
from typing import Dict, Iterable, Tuple
import argparse
import shutil

def load_pdf_text(file_path):
    """
    Opens and reads the text from a PDF file.

    Args:
        file_path (str): The path to the PDF file.

    Returns:
        str: The extracted text from the PDF, or None if an error occurs.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None

def load_pdf_pages(file_path):
    """
    Opens a PDF and returns a list of per-page strings.

    Args:
        file_path (str): The path to the PDF file.

    Returns:
        list[str] | None: Per-page text list, or None if an error occurs.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return None

def validate_two_pdfs(pdf_a, pdf_b):
    """
    Validates two PDFs can be opened and returns their per-page text lists.

    Returns:
        tuple[list[str], list[str]] | None: (pages_a, pages_b) or None on failure.
    """
    pages_a = load_pdf_pages(pdf_a)
    pages_b = load_pdf_pages(pdf_b)
    if pages_a is None or pages_b is None:
        return None
    return pages_a, pages_b

def construct_zero_shot_prompt(document_text):
    """
    Constructs a zero-shot prompt for identifying key data elements.

    Args:
        document_text (str): The text of the security document.

    Returns:
        str: The zero-shot prompt.
    """
    return f"""[INST]
Analyze the following security document and identify the key data elements (KDEs) and their corresponding requirements. For each KDE, provide a name and a list of requirements associated with it. Structure the output as a nested dictionary where each key is a KDE, and the value is another dictionary containing the 'name' of the KDE and a 'requirements' list.

Return ONLY YAML matching this schema:

kde_key:
  name: "Readable KDE Name"
  requirements:
    - "req1"
    - "req2"

No code fences, no extra text.

Document:
{document_text}
[/INST]"""

def construct_few_shot_prompt(document_text):
    """
    Constructs a few-shot prompt for identifying key data elements.

    Args:
        document_text (str): The text of the security document.

    Returns:
        str: The few-shot prompt.
    """
    return f"""[INST]
Analyze the following security document and identify the key data elements (KDEs) and their corresponding requirements. For each KDE, provide a name and a list of requirements associated with it. Structure the output as a nested dictionary where each key is a KDE, and the value is another dictionary containing the 'name' of the KDE and a 'requirements' list.

Return ONLY YAML matching this schema:

kde_key:
  name: "Readable KDE Name"
  requirements:
    - "req1"
    - "req2"

No code fences, no extra text.

Here are some examples:

Example 1:
Document: "The system shall enforce password complexity. Passwords must be at least 8 characters long and contain a mix of uppercase, lowercase, and numeric characters."
Output:
password_complexity:
  name: "Password Complexity"
  requirements:
    - "at least 8 characters long"
    - "contain a mix of uppercase, lowercase, and numeric characters"

Example 2:
Document: "All sensitive data must be encrypted at rest using AES-256. Access to encrypted data should be logged."
Output:
data_encryption:
  name: "Data Encryption"
  requirements:
    - "encrypted at rest using AES-256"
access_logging:
  name: "Access Logging"
  requirements:
    - "Access to encrypted data should be logged"

Now, analyze the following document:

Document:
{document_text}
[/INST]"""

def construct_chain_of_thought_prompt(document_text):
    """
    Constructs a chain-of-thought prompt for identifying key data elements.

    Args:
        document_text (str): The text of the security document.

    Returns:
        str: The chain-of-thought prompt.
    """
    return f"""[INST]
Analyze the following security document and identify the key data elements (KDEs) and their corresponding requirements.
This is a Chain of Thought prompt. First, think step-by-step about how to identify the KDEs.

Example of thinking process:
1. Read the document to understand its purpose.
2. Identify sections that describe security controls or requirements.
3. For each control, extract the main subject (the KDE name).
4. Extract the specific requirements associated with that KDE.
5. Format the output as a YAML list.

Example Output Format:
```yaml
- kde_name_1:
    name: "Name of the Key Data Element 1"
    requirements:
    - "Requirement 1.1"
    - "Requirement 1.2"
- kde_name_2:
    name: "Name of the Key Data Element 2"
    requirements:
    - "Requirement 2.1"
```

No code fences, no extra text.

Document:
{document_text}
[/INST]"""

def _normalize_kde_name(name: str) -> str:
    return " ".join("".join(ch for ch in name.lower().strip() if ch.isalnum() or ch.isspace()).split())


def merge_kdes(base: Dict, new: Dict) -> Dict:
    """
    Merges KDE dictionaries by normalized name, combining requirements lists.
    """
    if not base:
        base = {}
    if not new:
        return base

    name_map = {_normalize_kde_name(k): k for k in base.keys()}
    for key, value in new.items():
        norm = _normalize_kde_name(key)
        if norm in name_map:
            existing_key = name_map[norm]
            existing_reqs = base.get(existing_key, {}).get("requirements", []) or []
            incoming_reqs = value.get("requirements", []) or []
            merged_reqs = list(dict.fromkeys(existing_reqs + incoming_reqs))
            base[existing_key]["requirements"] = merged_reqs
        else:
            base[key] = value
            name_map[norm] = key
    return base

def process_pdf_in_chunks(
    pdf_path,
    prompt_builder,
    prompt_type,
    pages_per_chunk=4,
    overlap_pages=1,
    llm_name="google/gemma-3-1b-it",
):
    """
    Processes a PDF in page-based chunks and merges KDEs across chunks.
    """
    merged_kdes = {}
    for chunk_index, (chunk_text, page_range) in enumerate(
        stream_pdf_chunks(pdf_path, pages_per_chunk=pages_per_chunk, overlap_pages=overlap_pages),
        start=1,
    ):
        prompt = prompt_builder(chunk_text)
        output_tag = f"chunk{chunk_index}_p{page_range[0]}-{page_range[1]}"
        chunk_kdes = identify_kdes(prompt, prompt_type, llm_name=llm_name, output_tag=output_tag)
        merged_kdes = merge_kdes(merged_kdes, chunk_kdes)
    return merged_kdes

def process_pages_in_chunks(
    pages,
    prompt_builder,
    prompt_type,
    pages_per_chunk=4,
    overlap_pages=1,
    llm_name="google/gemma-3-1b-it",
    pdf_name=None,
    output_root="outputs",
):
    """
    Processes in-memory page text in chunks and merges KDEs across chunks.
    """
    merged_kdes = {}
    for chunk_index, (chunk_text, page_range) in enumerate(
        stream_pages_chunks(pages, pages_per_chunk=pages_per_chunk, overlap_pages=overlap_pages),
        start=1,
    ):
        prompt = prompt_builder(chunk_text)
        output_tag = f"chunk{chunk_index}_p{page_range[0]}-{page_range[1]}"
        chunk_kdes = identify_kdes(
            prompt,
            prompt_type,
            llm_name=llm_name,
            output_tag=output_tag,
            pdf_name=pdf_name,
            output_root=output_root,
        )
        merged_kdes = merge_kdes(merged_kdes, chunk_kdes)
    return merged_kdes

def identify_kdes(prompt, prompt_type, llm_name="google/gemma-3-1b-it", output_tag="", pdf_name=None, output_root="outputs"):
    """
    Uses a constructed prompt to identify key data elements (KDEs) in a document.

    Args:
        prompt (str): The prompt to send to the LLM.
        prompt_type (str): The type of prompt (e.g., "zero-shot").
        llm_name (str): The name of the LLM to use.
        output_tag (str): Optional tag for output file names (e.g., chunk id).

    Returns:
        dict: A nested dictionary of KDEs.
    """
    use_cuda = torch.cuda.is_available()
    device = 0 if use_cuda else -1
    dtype = torch.float16 if use_cuda else torch.bfloat16
    pipe = pipeline("text-generation", model=llm_name, device=device, dtype=dtype)
    messages = [
            {
                "role": "user",
                "content": prompt,
            },
    ]
    output = pipe(messages, max_new_tokens=1024)
    generated_text = output[0]['generated_text']

    safe_tag = f"_{output_tag}" if output_tag else ""
    output_dir = output_root
    if pdf_name:
        output_dir = os.path.join(output_root, os.path.splitext(os.path.basename(pdf_name))[0], prompt_type)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{prompt_type}{safe_tag}_llm_output.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"*LLM Name*\n{llm_name}\n\n")
        f.write(f"*Prompt Used*\n{prompt}\n\n")
        f.write(f"*Prompt Type*\n{prompt_type}\n\n")
        f.write(f"*LLM Output*\n{generated_text}\n")

    try:
        # The model might return fenced code blocks; strip the fence and language tag.
        if "```" in generated_text:
            parts = generated_text.split("```")
            if len(parts) >= 3:
                fenced = parts[1].strip()
                first_line, *rest = fenced.split("\n", 1)
                if first_line.strip().lower() in {"yaml", "yml", "json", "python"} and rest:
                    fenced = rest[0]
                generated_text = fenced.strip()
        parsed = yaml.safe_load(generated_text)
        return _coerce_kde_structure(parsed)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML from LLM output: {e}")
        return None

def _coerce_kde_structure(raw):
    """
    Coerces model output into the required KDE mapping structure.
    """
    if raw is None:
        return None

    def _normalize_entry(entry):
        name = entry.get("name") or entry.get("Name") or entry.get("KDE") or ""
        requirements = entry.get("requirements") or entry.get("Requirements") or []
        if isinstance(requirements, str):
            requirements = [requirements]
        return {
            "name": name,
            "requirements": requirements,
        }

    if isinstance(raw, list):
        coerced = {}
        for item in raw:
            if isinstance(item, dict):
                # The key of the outer dict should be the first key in the list item
                item_key = next(iter(item), None)
                if item_key:
                    coerced[item_key] = _normalize_entry(item[item_key])
        return coerced or None

    if isinstance(raw, dict):
        if "KDE" in raw or "Requirements" in raw:
            key = raw.get("KDE") or raw.get("name") or raw.get("Name") or "kde"
            return {key: _normalize_entry(raw)}

        coerced = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                coerced[key] = _normalize_entry(value)
            else:
                coerced[key] = {"name": str(key), "requirements": [str(value)]}
        return coerced or None

    return None

def save_kdes_to_yaml(kdes, pdf_path, output_dir="outputs"):
    """
    Saves the extracted KDEs to a YAML file.
    The output path will be based on the PDF file name.
    """
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_output_dir = os.path.join(output_dir, pdf_name)
    os.makedirs(pdf_output_dir, exist_ok=True)
    output_path = os.path.join(pdf_output_dir, f"{pdf_name}-kdes.yaml")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(kdes, f, default_flow_style=False, sort_keys=False)
        print(f"KDEs saved to {output_path}")
    except Exception as e:
        print(f"Error saving YAML file: {e}")

def stream_pdf_chunks(file_path, pages_per_chunk=4, overlap_pages=1) -> Iterable[Tuple[str, Tuple[int, int]]]:
    """
    Streams PDF text in page-based chunks with overlap.

    Args:
        file_path (str): The path to the PDF file.
        pages_per_chunk (int): Number of pages per chunk.
        overlap_pages (int): Number of pages to overlap between chunks.

    Yields:
        tuple[str, tuple[int, int]]: (chunk_text, (start_page, end_page)) 1-based page range.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return
    if pages_per_chunk <= 0:
        raise ValueError("pages_per_chunk must be > 0")
    if overlap_pages < 0 or overlap_pages >= pages_per_chunk:
        raise ValueError("overlap_pages must be >= 0 and < pages_per_chunk")

    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        total_pages = len(reader.pages)

        start = 0
        while start < total_pages:
            end = min(start + pages_per_chunk, total_pages)
            chunk_text = ""
            for page_index in range(start, end):
                page_text = reader.pages[page_index].extract_text() or ""
                chunk_text += page_text + "\n"

            if chunk_text.strip():
                # Convert to 1-based page range for readability.
                yield chunk_text, (start + 1, end)

            if end == total_pages:
                break
            start = end - overlap_pages

def stream_pages_chunks(pages: Iterable[str], pages_per_chunk=4, overlap_pages=1) -> Iterable[Tuple[str, Tuple[int, int]]]:
    """
    Streams text chunks from an in-memory list of page strings with overlap.

    Args:
        pages (Iterable[str]): Per-page text strings.
        pages_per_chunk (int): Number of pages per chunk.
        overlap_pages (int): Number of pages to overlap between chunks.

    Yields:
        tuple[str, tuple[int, int]]: (chunk_text, (start_page, end_page)) 1-based page range.
    """
    if pages_per_chunk <= 0:
        raise ValueError("pages_per_chunk must be > 0")
    if overlap_pages < 0 or overlap_pages >= pages_per_chunk:
        raise ValueError("overlap_pages must be >= 0 and < pages_per_chunk")

    page_list = list(pages)
    total_pages = len(page_list)
    start = 0
    while start < total_pages:
        end = min(start + pages_per_chunk, total_pages)
        chunk_text = ""
        for page_index in range(start, end):
            page_text = page_list[page_index] or ""
            chunk_text += page_text + "\n"

        if chunk_text.strip():
            yield chunk_text, (start + 1, end)

        if end == total_pages:
            break
        start = end - overlap_pages

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract KDEs from two PDF documents.")
    parser.add_argument("pdf_a", help="First PDF file path", nargs='?')
    parser.add_argument("pdf_b", help="Second PDF file path", nargs='?')
    parser.add_argument("--pages-per-chunk", type=int, default=4, dest="pages_per_chunk")
    parser.add_argument("--overlap-pages", type=int, default=1, dest="overlap_pages")
    parser.add_argument("--output-root", default="outputs", dest="output_root")
    parser.add_argument(
        "--clean",
        action="store_true",
        dest="clean_output_root",
        help="Delete the output root directory before writing new outputs.",
    )
    args = parser.parse_args()

    if args.clean_output_root:
        if os.path.exists(args.output_root):
            shutil.rmtree(args.output_root)
            print(f"Cleaned output directory: {args.output_root}")
        if not (args.pdf_a and args.pdf_b):
            raise SystemExit(0)


    if not (args.pdf_a and args.pdf_b):
        raise SystemExit("Both pdf_a and pdf_b are required if --clean is not the sole action.")

    pdf_paths = [args.pdf_a, args.pdf_b]
    validated = validate_two_pdfs(pdf_paths[0], pdf_paths[1])
    if not validated:
        raise SystemExit("PDF validation failed. Check file paths and readability.")

    for index, pdf_path in enumerate(pdf_paths):
        pages = validated[index]
        if pages is None:
            print(f"Skipping {pdf_path} due to load failure.")
            continue

        zero_shot_kdes = process_pages_in_chunks(
            pages,
            construct_zero_shot_prompt,
            "zero-shot",
            pages_per_chunk=args.pages_per_chunk,
            overlap_pages=args.overlap_pages,
            pdf_name=pdf_path,
            output_root=args.output_root,
        )
        if zero_shot_kdes:
            save_kdes_to_yaml(zero_shot_kdes, pdf_path, output_dir=args.output_root)

        few_shot_kdes = process_pages_in_chunks(
            pages,
            construct_few_shot_prompt,
            "few-shot",
            pages_per_chunk=args.pages_per_chunk,
            overlap_pages=args.overlap_pages,
            pdf_name=pdf_path,
            output_root=args.output_root,
        )
        if few_shot_kdes:
            save_kdes_to_yaml(few_shot_kdes, pdf_path, output_dir=args.output_root)

        cot_kdes = process_pages_in_chunks(
            pages,
            construct_chain_of_thought_prompt,
            "chain-of-thought",
            pages_per_chunk=args.pages_per_chunk,
            overlap_pages=args.overlap_pages,
            pdf_name=pdf_path,
            output_root=args.output_root,
        )
        if cot_kdes:
            save_kdes_to_yaml(cot_kdes, pdf_path, output_dir=args.output_root)