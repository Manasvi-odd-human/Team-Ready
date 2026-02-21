import pytest
import os
import json
import shutil

# Dynamically import the Flask app from the backend directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import get_file_path, read_json_file, write_json_file, append_to_log_file, get_precis, DATA_DIR, app

# Ensure the .team-ready directory is unique for testing utilities
TEST_UTILITIES_DIR = '.team-ready-utilities-test'

@pytest.fixture(scope='function')
def setup_test_data_dir():
    original_data_dir = app.config.get('DATA_DIR', None)
    test_dir_path = os.path.join(os.getcwd(), TEST_UTILITIES_DIR)
    app.config['DATA_DIR'] = test_dir_path # Temporarily set DATA_DIR for utilities testing

    if os.path.exists(test_dir_path):
        shutil.rmtree(test_dir_path)
    os.makedirs(test_dir_path)
    
    yield test_dir_path

    if os.path.exists(test_dir_path):
        shutil.rmtree(test_dir_path)
    
    if original_data_dir is not None:
        app.config['DATA_DIR'] = original_data_dir

def test_get_file_path(setup_test_data_dir):
    filename = "test_file.txt"
    expected_path = os.path.join(setup_test_data_dir, filename)
    assert get_file_path(filename) == expected_path

def test_read_and_write_json_file(setup_test_data_dir):
    filename = "test_config.json"
    test_data = {"key": "value", "number": 123}

    # Test writing
    write_json_file(filename, test_data)
    filepath = get_file_path(filename)
    assert os.path.exists(filepath)
    with open(filepath, 'r') as f:
        read_content = json.load(f)
    assert read_content == test_data

    # Test reading
    read_data = read_json_file(filename)
    assert read_data == test_data

    # Test reading non-existent file with default value
    non_existent_file = "non_existent.json"
    default_data = {"default": "data"}
    read_default = read_json_file(non_existent_file, default_data)
    assert read_default == default_data

    # Test reading non-existent file without default value
    read_none = read_json_file(non_existent_file)
    assert read_none is None

def test_append_to_log_file(setup_test_data_dir):
    filename = "test_log.log"
    message1 = "This is the first log message."
    message2 = "This is the second log message with SECRET_API_KEY and PASSWORD."
    
    append_to_log_file(filename, message1)
    append_to_log_file(filename, message2)

    filepath = get_file_path(filename)
    assert os.path.exists(filepath)
    
    with open(filepath, 'r') as f:
        content = f.readlines()
    
    assert len(content) == 2
    assert content[0].strip() == message1
    assert "This is the second log message with [REDACTED]_[REDACTED] and [REDACTED]." in content[1]


def test_get_precis(setup_test_data_dir):
    log_filename = "agents_internal.log"
    log_filepath = get_file_path(log_filename)

    # Test with empty log
    precis = get_precis()
    assert precis == "No internal agent logs yet."

    # Test with less than 10 lines
    messages = [f"Log line {i}" for i in range(5)]
    # Clear existing log before appending new messages
    if os.path.exists(log_filepath):
        with open(log_filepath, 'w') as f:
            pass
    for msg in messages:
        append_to_log_file(log_filename, msg)
    
    precis = get_precis()
    expected_precis = "Previous internal agent thoughts:\n" + "\n".join(messages)
    assert precis == expected_precis

    # Test with exactly 10 lines
    messages = [f"Log line {i}" for i in range(10)]
    # Clear existing log
    if os.path.exists(log_filepath):
        with open(log_filepath, 'w') as f:
            pass
    for msg in messages:
        append_to_log_file(log_filename, msg)
    
    precis = get_precis()
    expected_precis = "Previous internal agent thoughts:\n" + "\n".join(messages)
    assert precis == expected_precis

    # Test with more than 10 lines
    messages = [f"Log line {i}" for i in range(15)]
    # Clear existing log
    if os.path.exists(log_filepath):
        with open(log_filepath, 'w') as f:
            pass
    for msg in messages:
        append_to_log_file(log_filename, msg)
    
    precis = get_precis()
    expected_precis = "Previous internal agent thoughts:\n" + "\n".join(messages[-10:])
    assert precis == expected_precis
