#!/usr/bin/env python3
import re
import logging
import os
import fnmatch


def setup_logging(level=logging.INFO):
    """
    Set up logging configuration

    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def filter_files(files, max_changes, exclusion_patterns=None):
    """
    Filter files to review based on criteria

    Args:
        files (list): List of file dictionaries from GitHub API
        max_changes (int): Maximum number of changes to consider
        exclusion_patterns (list): List of glob patterns to exclude

    Returns:
        list: Filtered list of files to review
    """
    exclusion_patterns = exclusion_patterns or []
    filtered_files = []

    for file_data in files:
        filename = file_data["filename"]

        # Skip files that are too large or binary
        if file_data.get("status") == "removed" or file_data.get("changes", 0) > max_changes:
            continue

        # Skip files without patches
        if not file_data.get("patch"):
            continue

        # Skip excluded file patterns
        if any(fnmatch.fnmatch(filename, pattern) for pattern in exclusion_patterns):
            continue

        # Add file to review list
        filtered_files.append(file_data)

    return filtered_files


def parse_patch_for_line(patch):
    """
    Parse a Git patch to find the best line for a comment

    Args:
        patch (str): Git patch/diff string

    Returns:
        int: Line number for placing a comment
    """
    # Default to line 1 if parsing fails
    line = 1

    # Try to find the first added line
    lines = patch.split('\n')
    for idx, line_content in enumerate(lines):
        if line_content.startswith('+') and not line_content.startswith('+++'):
            # Extract line number from the preceding hunk header
            for i in range(idx, -1, -1):
                if lines[i].startswith('@@'):
                    match = re.search(r'\+(\d+)', lines[i])
                    if match:
                        line_offset = idx - i - 1
                        line = int(match.group(1)) + line_offset
                        return line

    return line


def extract_code_from_file(file_path):
    """
    Extract code from a file

    Args:
        file_path (str): Path to the file

    Returns:
        str: File content
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        return ""


def get_diff_hunk_contexts(patch):
    """
    Extract diff hunks with context

    Args:
        patch (str): Git patch/diff string

    Returns:
        list: List of tuples (start_line, hunk_content)
    """
    hunks = []
    current_hunk = []
    current_start = 0

    for line in patch.split('\n'):
        if line.startswith('@@'):
    # If we were already processing a hunk, save it