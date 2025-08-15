"""
Mock folder_paths module for testing outside of ComfyUI environment
"""

import os

def get_folder_paths(folder_type):
    """Mock implementation of folder_paths.get_folder_paths"""
    if folder_type == "custom_nodes":
        # Return a mock custom_nodes path
        return [os.path.join(os.path.dirname(__file__), "mock_custom_nodes")]
    return ["/tmp"]

def get_output_directory():
    """Mock implementation of folder_paths.get_output_directory"""
    return os.path.join(os.path.dirname(__file__), "test_output")
