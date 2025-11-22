"""
Utility functions for loading prompts from files.
"""
import os
import logging

logger = logging.getLogger(__name__)

def load_prompt(file_path):
    """
    Load prompt text from a file.
    
    Args:
        file_path: Path to the prompt file
        
    Returns:
        str: The prompt text
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        prompt_text = f.read().strip()
    
    logger.debug(f"Loaded prompt from {file_path}")
    return prompt_text
