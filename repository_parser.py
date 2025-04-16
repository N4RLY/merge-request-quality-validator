import os
import re
from typing import Dict, List, Tuple, Optional

def parse_repository_file(file_path: str) -> Dict[str, str]:
    """
    Parse a repository file in the yeongpin-cursor-free-vip.txt format.
    
    Args:
        file_path: Path to the repository file
        
    Returns:
        Dictionary mapping file paths to their content
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Parse directory structure (optional)
    directory_structure = None
    if content.startswith("Directory structure:"):
        structure_end_idx = content.find("\n\n")
        if structure_end_idx != -1:
            directory_structure = content[:structure_end_idx].strip()
    
    # Split content into file sections using the delimiter
    file_delimiter = "================================================"
    file_sections = content.split(file_delimiter)
    
    # Remove any sections before the first file (like directory structure)
    file_sections = [section for section in file_sections if "FILE: " in section]
    
    # Process each file section
    repository_files = {}
    for section in file_sections:
        # Extract filename and content
        file_match = re.search(r"FILE: (.+?)\n", section)
        if file_match:
            filename = file_match.group(1).strip()
            
            # Get content after the FILE: line
            content_start = file_match.end()
            file_content = section[content_start:].strip()
            
            # Store in dictionary
            repository_files[filename] = file_content
    
    return repository_files

def save_parsed_repository(repository_files: Dict[str, str], output_dir: str) -> List[str]:
    """
    Save the parsed repository files to the given output directory.
    
    Args:
        repository_files: Dictionary mapping file paths to their content
        output_dir: Directory where to save the parsed files
        
    Returns:
        List of saved file paths
    """
    saved_files = []
    
    for file_path, content in repository_files.items():
        # Create the target directory if needed
        target_path = os.path.join(output_dir, file_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Write file content
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        saved_files.append(target_path)
    
    return saved_files

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python repository_parser.py <repository_file> <output_directory>")
        sys.exit(1)
    
    repo_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    try:
        repository_files = parse_repository_file(repo_file)
        saved_files = save_parsed_repository(repository_files, output_dir)
        
        print(f"Successfully parsed {len(repository_files)} files.")
        print(f"Files saved to {output_dir}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 