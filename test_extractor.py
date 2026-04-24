# Author: Lily Edgil
# Created with assistance from GitHub Copilot.

import pytest
import os
import torch
from extractor import (
    load_pdf_text,
    construct_zero_shot_prompt,
    construct_few_shot_prompt,
    construct_chain_of_thought_prompt,
    identify_kdes,
    save_kdes_to_yaml,
    process_pages_in_chunks,
)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

@pytest.fixture
def setup_test_pdf():
    """Set up a dummy PDF for testing and clean it up afterwards."""
    test_pdf_path = "test.pdf"
    test_document_text = "This is a test document."
    c = canvas.Canvas(test_pdf_path, pagesize=letter)
    c.drawString(100, 750, test_document_text)
    c.save()
    yield test_pdf_path, test_document_text
    # Teardown
    if os.path.exists(test_pdf_path):
        os.remove(test_pdf_path)
    output_yaml_path = "outputs/test/test-kdes.yaml"
    if os.path.exists(output_yaml_path):
        os.remove(output_yaml_path)
    # Clean up directory if empty
    output_dir = os.path.dirname(output_yaml_path)
    if os.path.exists(output_dir) and not os.listdir(output_dir):
        os.rmdir(output_dir)


def test_load_pdf_text(setup_test_pdf):
    """Test loading text from a PDF file."""
    test_pdf_path, test_document_text = setup_test_pdf
    text = load_pdf_text(test_pdf_path)
    assert test_document_text in text

def test_construct_zero_shot_prompt(setup_test_pdf):
    """Test constructing a zero-shot prompt."""
    _, test_document_text = setup_test_pdf
    prompt = construct_zero_shot_prompt(test_document_text)
    assert test_document_text in prompt
    assert "Analyze the following security document" in prompt

def test_construct_few_shot_prompt(setup_test_pdf):
    """Test constructing a few-shot prompt."""
    _, test_document_text = setup_test_pdf
    prompt = construct_few_shot_prompt(test_document_text)
    assert test_document_text in prompt
    assert "Here are some examples:" in prompt

def test_construct_chain_of_thought_prompt(setup_test_pdf):
    """Test constructing a chain-of-thought prompt."""
    _, test_document_text = setup_test_pdf
    prompt = construct_chain_of_thought_prompt(test_document_text)
    assert test_document_text in prompt
    assert "First, think step-by-step" in prompt
    assert "Chain of Thought" in prompt

def test_identify_kdes(mocker):
    """
    Test the identify_kdes function.
    Mocks the transformer pipeline to avoid actual LLM calls.
    """
    # Mock torch.cuda.is_available to ensure consistent behavior
    mocker.patch('torch.cuda.is_available', return_value=False)

    # Mock the pipeline where it is used in the extractor module
    mock_pipeline = mocker.patch('extractor.pipeline')
    # This mock now returns the structure the function expects
    mock_pipeline.return_value.return_value = [{'generated_text': '```yaml\n- element1:\n    name: Test Element\n    requirements:\n      - req1\n```'}]

    # Mock file writing
    mock_open = mocker.patch('builtins.open', mocker.mock_open())

    prompt = "Test prompt"
    prompt_type = "zero-shot"
    llm_name = "google/gemma-3-1b-it"
    output_tag = "test_output"
    
    result = identify_kdes(prompt, prompt_type, llm_name, output_tag)

    # Assert that the pipeline was called
    mock_pipeline.assert_called_with("text-generation", model=llm_name, device=-1, dtype=torch.bfloat16)

    # Assert that the file was written to
    mock_open.assert_called()
    
    # Assert that the result is the parsed YAML
    assert "element1" in result
    assert result["element1"]["name"] == "Test Element"

def test_save_kdes_to_yaml(setup_test_pdf):
    """Test saving KDEs to a YAML file."""
    test_pdf_path, _ = setup_test_pdf
    kdes = {"test_element": {"name": "Test Element", "requirements": ["req1", "req2"]}}
    save_kdes_to_yaml(kdes, test_pdf_path)
    assert os.path.exists("outputs/test/test-kdes.yaml")

def test_process_pages_in_chunks(mocker):
    """
    Test the process_pages_in_chunks function.
    Mocks identify_kdes to avoid LLM calls.
    """
    # Mock the identify_kdes function
    mock_identify_kdes = mocker.patch('extractor.identify_kdes')
    mock_identify_kdes.return_value = {"element1": {"name": "Test Element", "requirements": ["req1"]}}

    pages = ["Page 1 content", "Page 2 content", "Page 3 content"] # 3 pages
    pdf_name = "test_pdf"
    prompt_builder = construct_zero_shot_prompt 
    prompt_type = "zero-shot"
    llm_name = "google/gemma-3-1b-it"
    chunk_size = 2
    overlap_pages = 1

    result = process_pages_in_chunks(
        pages,
        prompt_builder,
        prompt_type,
        pages_per_chunk=chunk_size,
        overlap_pages=overlap_pages,
        llm_name=llm_name,
        pdf_name=pdf_name,
    )

    # With 3 pages, chunk size 2, and overlap 1, we expect 2 chunks.
    # Chunk 1: pages 1-2. Chunk 2: pages 2-3.
    assert mock_identify_kdes.call_count == 2

    # Assert that the results are merged correctly
    assert "element1" in result
    assert result["element1"]["name"] == "Test Element"
    assert len(result["element1"]["requirements"]) == 1
