import os
import json
import re
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple
from yandex_cloud_ml_sdk import YCloudML
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
MODEL_NAME = os.getenv("YANDEX_CLOUD_MODEL_NAME")

if not API_KEY or not FOLDER_ID or not MODEL_NAME:
    raise ValueError("Missing environment variables. Please check your .env file.")

def parse_repository_file(file_path: str) -> Dict[str, str]:
    """
    Parse a repository file in the yeongpin-cursor-free-vip.txt format.
    
    Args:
        file_path: Path to the repository file
        
    Returns:
        Dictionary mapping file paths to their content
    """
    logger.info(f"Parsing repository file: {file_path}")
    try:
        # Check if file exists
        if not os.path.isfile(file_path):
            logger.error(f"Repository file does not exist: {file_path}")
            raise FileNotFoundError(f"Repository file does not exist: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        if not content:
            logger.warning("Repository file is empty")
            return {}
            
        # Parse directory structure (optional)
        directory_structure = None
        if content.startswith("Directory structure:"):
            structure_end_idx = content.find("\n\n")
            if structure_end_idx != -1:
                directory_structure = content[:structure_end_idx].strip()
                logger.debug(f"Found directory structure: {directory_structure}")
                # Move past the directory structure
                content = content[structure_end_idx+2:]
        
        # Split content into file sections using the delimiter
        filtered_file_sections = []
        file_delimiter = "================================================"
        file_sections = content.split(file_delimiter)
        for i in range(len(file_sections)):
            if "FILE: " in file_sections[i]:
                filtered_file_sections.append(file_sections[i] + file_sections[i+1])
        logger.info(f"Found {len(filtered_file_sections)} file sections")
        for section in filtered_file_sections:
            # logger.info(section)
            pass

        if not filtered_file_sections:
            logger.warning("No file sections found in the repository file")
            return {}
            
        # Process each file section
        repository_files = {}
        for section in filtered_file_sections:
            # Extract filename and content
            file_match = re.search(r"FILE: (.+?)\n", section)
            if file_match:
                filename = file_match.group(1).strip()
                
                # Skip empty filenames
                if not filename:
                    logger.warning("Found empty filename in section, skipping")
                    continue
                    
                # Get content after the FILE: line
                content_start = file_match.end()
                file_content = section[content_start:].strip()
                
                # Store in dictionary
                repository_files[filename] = file_content
                logger.debug(f"Processed file: {filename} ({len(file_content)} bytes)")
            else:
                logger.warning(f"Could not extract filename from section: {section[:100]}...")
        
        logger.info(f"Successfully parsed {len(repository_files)} files")
        return repository_files
    except Exception as e:
        logger.error(f"Error parsing repository file: {str(e)}", exc_info=True)
        raise

def generate_diff_content(repository_files: Dict[str, str]) -> str:
    """
    Generate a unified diff-like content from the repository files
    
    Args:
        repository_files: Dictionary mapping file paths to their content
        
    Returns:
        A string containing a unified diff-like representation
    """
    logger.info("Generating diff content")
    try:
        if not repository_files:
            logger.warning("No files to generate diff for")
            return ""
            
        diff_content = ""
        
        for file_path, content in repository_files.items():
            logger.debug(f"Processing file for diff: {file_path}")
            
            # Skip binary files or files that might cause issues
            if '\0' in content or not content.isprintable():
                logger.warning(f"Skipping potentially binary file: {file_path}")
                continue
                
            # Limit content size to avoid exceeding token limits
            if len(content) > 10000:
                logger.warning(f"File content too large ({len(content)} chars), truncating: {file_path}")
                content = content[:10000] + "\n[... TRUNCATED DUE TO SIZE ...]"
                
            # Create proper diff format
            file_lines = content.split('\n')
            diff_content += f"--- /dev/null\n+++ b/{file_path}\n"
            diff_content += f"@@ -0,0 +1,{len(file_lines)} @@\n"
            
            # Add each line with a '+' prefix to indicate addition
            for line in file_lines:
                diff_content += f"+{line}\n"
            
            diff_content += "\n"
        
        logger.info(f"Successfully generated diff content for {len(repository_files)} files")
        
        # Check if the diff content is too large
        if len(diff_content) > 100000:
            logger.warning(f"Diff content too large ({len(diff_content)} chars), truncating")
            diff_content = diff_content[:100000] + "\n[... TRUNCATED DUE TO SIZE ...]"
            
        return diff_content
    except Exception as e:
        logger.error(f"Error generating diff content: {str(e)}", exc_info=True)
        raise

class MergeRequestAnalyzer:
    """Main class for analyzing merge request quality"""
    
    def __init__(self):
        logger.info("Initializing MergeRequestAnalyzer")
        self.api_key = API_KEY
        self.folder_id = FOLDER_ID
        self.model_name = MODEL_NAME
        self.sdk = YCloudML(folder_id=self.folder_id, auth=self.api_key)
        logger.info("Successfully initialized MergeRequestAnalyzer")
        
    def call_yandex_cloud_api(self, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
        """
        Call Yandex Cloud API with the given prompt using the SDK
        
        Args:
            prompt: The prompt to send to the API
            temperature: Temperature parameter for generation (lower = more deterministic)
            
        Returns:
            The API response
        """
        logger.info("Calling Yandex Cloud API")
        try:
            # Check if we have valid credentials
            if not self.api_key or not self.folder_id or not self.model_name:
                logger.error("Missing required API credentials")
                return {"error": "Missing required API credentials"}
            
            # Truncate prompt if too long
            if len(prompt) > 32000:
                logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to 32000 chars")
                prompt = prompt[:32000]
            
            model = self.sdk.models.completions(self.model_name, model_version="latest")
            model = model.configure(temperature=temperature, max_tokens=1500)
            
            logger.info(f"Sending request to model: {self.model_name}")
            result = model.run(
                [
                    {"role": "system", "text": "You are a code review expert providing detailed analysis of code changes."},
                    {"role": "user", "text": prompt}
                ]
            )
            
            # Get the first alternative as our response
            alternatives = [alt for alt in result]
            if alternatives:
                logger.info(f"Successfully received response from Yandex Cloud API with {len(alternatives)} alternatives")
                return {"result": {"alternatives": alternatives}}
            else:
                logger.warning("No alternatives returned from the model")
                return {"error": "No alternatives returned from the model"}
            
        except ConnectionError as ce:
            logger.error(f"Connection error: {str(ce)}")
            return {"error": f"Connection error: {str(ce)}"}
        except TimeoutError as te:
            logger.error(f"API request timed out: {str(te)}")
            return {"error": f"API request timed out: {str(te)}"}
        except Exception as e:
            logger.error(f"API request failed: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def analyze_code_changes(self, diff_content: str) -> Dict[str, Any]:
        """
        Analyze code changes in a merge request
        
        Args:
            diff_content: Git diff content of the merge request
            
        Returns:
            Analysis results
        """
        logger.info("Starting code changes analysis")
        
        try:
            prompt = f"""You are a senior Python code reviewer. Analyze this code diff. Identify:
1. Code quality issues and anti-patterns (explain).
2. Good practices or design patterns used.
3. Overall quality score (0–10) with short justification.

Code diff:
{diff_content}
"""
            
            response = self.call_yandex_cloud_api(prompt)
            return self._parse_analysis_response(response)
            
        except Exception as e:
            logger.error(f"Error during code changes analysis: {str(e)}")
            raise
    
    def analyze_repository_file(self, repository_file_path: str) -> Dict[str, Any]:
        """
        Analyze a repository file in the yeongpin-cursor-free-vip.txt format
        
        Args:
            repository_file_path: Path to the repository file
            
        Returns:
            Analysis results
        """
        logger.info(f"Starting repository file analysis: {repository_file_path}")
        try:
            # Parse the repository file
            repository_files = parse_repository_file(repository_file_path)
            
            if not repository_files:
                logger.error("No files found in the repository file")
                return {"error": "No files found in the repository file"}
            
            # Generate diff content from the repository files
            diff_content = generate_diff_content(repository_files)
            
            # Analyze the code changes
            logger.info("Analyzing code changes from repository file")
            return self.analyze_code_changes(diff_content)
            
        except Exception as e:
            logger.error(f"Error analyzing repository file: {str(e)}")
            raise
    
    def _parse_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and structure the API response"""
        if "error" in response:
            logger.error(f"API returned an error: {response['error']}")
            return {"error": response["error"]}
        
        try:
            # Extract the relevant parts from the API response
            if "result" in response and "alternatives" in response["result"]:
                alternatives = response["result"]["alternatives"]
                if alternatives and len(alternatives) > 0:
                    # Try to handle different response structures
                    if hasattr(alternatives[0], 'text'):
                        message = alternatives[0].text
                    elif isinstance(alternatives[0], dict) and 'text' in alternatives[0]:
                        message = alternatives[0]['text']
                    else:
                        # Fall back to string representation
                        message = str(alternatives[0])
                    
                    # Parse the analysis into structured data
                    analysis = {
                        "quality_issues": [],
                        "good_practices": [],
                        "overall_score": None,
                        "raw_response": message
                    }
                    
                    # Try to extract structured data
                    quality_match = re.search(r"1\.\s+Code quality issues.*?(?=2\.)", message, re.DOTALL | re.IGNORECASE)
                    if quality_match:
                        quality_text = quality_match.group(0).strip()
                        # Extract bullet points or numbered items
                        issues = re.findall(r"[-•*]\s+(.*?)(?=[-•*]|\Z)", quality_text, re.DOTALL)
                        if not issues:
                            issues = re.findall(r"\d+\.\s+(.*?)(?=\d+\.|\Z)", quality_text, re.DOTALL)
                        analysis["quality_issues"] = [issue.strip() for issue in issues if issue.strip()]
                    
                    practices_match = re.search(r"2\.\s+Good practices.*?(?=3\.)", message, re.DOTALL | re.IGNORECASE)
                    if practices_match:
                        practices_text = practices_match.group(0).strip()
                        # Extract bullet points or numbered items
                        practices = re.findall(r"[-•*]\s+(.*?)(?=[-•*]|\Z)", practices_text, re.DOTALL)
                        if not practices:
                            practices = re.findall(r"\d+\.\s+(.*?)(?=\d+\.|\Z)", practices_text, re.DOTALL)
                        analysis["good_practices"] = [practice.strip() for practice in practices if practice.strip()]
                    
                    score_match = re.search(r"3\.\s+Overall quality score.*?(\d+(?:\.\d+)?)/10", message, re.DOTALL | re.IGNORECASE)
                    if score_match:
                        try:
                            analysis["overall_score"] = float(score_match.group(1))
                        except ValueError:
                            pass
                    
                    logger.info("Successfully parsed API response")
                    return analysis
                else:
                    logger.warning("API response contains empty alternatives")
            else:
                logger.warning(f"Unexpected API response structure: {response.keys()}")
            
            return {"error": "Unexpected API response format", "raw_response": str(response)[:500]}
        except Exception as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            return {"error": f"Failed to parse API response: {str(e)}", "raw_response": str(response)[:500]}
        
if __name__ == "__main__":
    import argparse
    
    logger.info("Starting merge request analyzer")
    
    parser = argparse.ArgumentParser(description="Analyze merge requests or repository files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--diff", help="Path to a file containing git diff content")
    group.add_argument("--repo", help="Path to a repository file in yeongpin-cursor-free-vip.txt format")
    parser.add_argument("--output", help="Path to output file (optional)")
    
    args = parser.parse_args()
    
    try:
        analyzer = MergeRequestAnalyzer()
        
        if args.repo:
            logger.info(f"Analyzing repository file: {args.repo}")
            analysis = analyzer.analyze_repository_file(args.repo)
        else:
            with open(args.diff, 'r', encoding='utf-8') as f:
                diff_content = f.read()
            logger.info(f"Analyzing diff file: {args.diff}")
            analysis = analyzer.analyze_code_changes(diff_content)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            logger.info(f"Analysis results saved to: {args.output}")
        else:
            print(json.dumps(analysis, indent=2))
            
        logger.info("Analysis completed successfully")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise
