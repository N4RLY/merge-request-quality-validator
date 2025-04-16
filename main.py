import argparse
import json
import sys
import os
import re # Added for parse_repository_file
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any # Added for type hints

# Assuming analyzer and gh_fetcher are importable
# Adjust paths if necessary based on your project structure
try:
    from app.modules.analyzer import MergeRequestAnalyzer
    from app.modules.gh_fetcher import GithubFetcher
except ImportError as e:
    print(f"Error importing modules: {e}. Make sure the paths are correct.")
    sys.exit(1)

# Configure logging (optional, can reuse from analyzer or set up anew)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables for GitHub Fetcher and Analyzer
load_dotenv()

# --- Environment Variable Checks ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# REPO_NAME = os.getenv("GITHUB_REPO_NAME") # Assuming you'll add this to .env for repo name - REMOVED

# Analyzer needs these, but they are checked within its __init__
# YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
# YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
# YANDEX_CLOUD_MODEL_NAME = os.getenv("YANDEX_CLOUD_MODEL_NAME")

# --- Input Parsing Functions (moved from analyzer.py) ---

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

        # Simple parsing logic based on the original function
        # Assumes format: FILE: path\ncontent\n================================================
        repository_files = {}
        file_delimiter = "\n================================================\n"
        # Split using a more robust delimiter that includes newline
        sections = content.split(file_delimiter)

        for section in sections:
            if not section.strip():
                continue
            # Find the first line which should be the FILE: line
            lines = section.strip().split('\n', 1)
            if len(lines) >= 1 and lines[0].startswith("FILE:"):
                filename = lines[0][len("FILE:"):].strip()
                file_content = lines[1].strip() if len(lines) > 1 else ""

                if not filename:
                    logger.warning("Found empty filename in section, skipping")
                    continue

                repository_files[filename] = file_content
                logger.debug(f"Parsed file: {filename} ({len(file_content)} bytes)")
            else:
                # Handle cases where the section might not start correctly
                # Perhaps log a warning or attempt alternative parsing if needed
                logger.warning(f"Could not parse FILE: line from section: {section[:100]}...")


        if not repository_files:
             logger.warning("No valid file sections found in the repository file.")

        logger.info(f"Successfully parsed {len(repository_files)} files from {file_path}")
        return repository_files

    except FileNotFoundError: # Catch specific error
        raise # Re-raise to be handled in main
    except Exception as e:
        logger.error(f"Error parsing repository file '{file_path}': {str(e)}", exc_info=True)
        raise # Re-raise to indicate failure

def generate_diff_content(repository_files: Dict[str, str]) -> str:
    """
    Generate a unified diff-like content from parsed repository files.
    Treats all content as added.

    Args:
        repository_files: Dictionary mapping file paths to their content

    Returns:
        A string containing a unified diff-like representation
    """
    logger.info(f"Generating pseudo-diff content from {len(repository_files)} files")
    try:
        if not repository_files:
            logger.warning("No files provided to generate diff content.")
            return ""

        diff_parts = []

        for file_path, content in repository_files.items():
            logger.debug(f"Processing file for diff generation: {file_path}")

            # Basic check for binary-like content (optional)
            # if '\0' in content:
            #     logger.warning(f"Skipping potentially binary file: {file_path}")
            #     continue

            # Create diff format header
            diff_parts.append(f"--- a/{file_path}") # Indicate original is empty
            diff_parts.append(f"+++ b/{file_path}") # Indicate new file path

            file_lines = content.split('\n')
            # Add hunk header (simplistic, assumes all lines added)
            diff_parts.append(f"@@ -0,0 +1,{len(file_lines)} @@")

            # Add each line with '+' prefix
            for line in file_lines:
                 # Ensure lines don't contain unexpected newlines that break format
                diff_parts.append(f"+{line.rstrip('\r\n')}")

            # Add a newline between file diffs for readability (optional)
            diff_parts.append("")

        full_diff_content = "\n".join(diff_parts)
        logger.info(f"Successfully generated pseudo-diff content (length: {len(full_diff_content)} chars)")

        # Truncation is now handled primarily within the analyzer/API call
        # but we can add a warning here if it's excessively large.
        # Limit check removed here, handled by analyzer

        return full_diff_content
    except Exception as e:
        logger.error(f"Error generating diff content: {str(e)}", exc_info=True)
        raise

# --- Main Logic ---

def validate_env_vars(use_github: bool):
    """Validate necessary environment variables."""
    if use_github:
        if not GITHUB_TOKEN:
            logger.error("GITHUB_TOKEN environment variable is missing.")
            sys.exit(1)
        # if not REPO_NAME: # REMOVED Check for REPO_NAME
        #     logger.error("GITHUB_REPO_NAME environment variable is missing.")
        #     sys.exit(1)
    # Analyzer checks its own variables internally

def run_github_fetch(args, repo_name: str) -> list:
    """Fetches PR data from GitHub."""
    logger.info(f"Fetching PR data for user '{args.github_user}' in repo '{repo_name}'")
    try:
        start_date = datetime.fromisoformat(args.start_date)
        end_date = datetime.fromisoformat(args.end_date)
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(1)

    try:
        fetcher = GithubFetcher(repo_name=repo_name, github_token=GITHUB_TOKEN)
        pr_data_list = fetcher.export_pr_data(args.github_user, start_date, end_date)
        logger.info(f"Fetched {len(pr_data_list)} pull requests from GitHub.")
        return pr_data_list
    except Exception as e:
        logger.error(f"Failed to fetch data from GitHub: {e}", exc_info=True)
        sys.exit(1)

def run_analysis_from_file(analyzer: MergeRequestAnalyzer, args) -> list:
    """Runs analysis based on input file type."""
    analysis_results = []
    if args.input_json:
        logger.info(f"Analyzing PR data from JSON file: {args.input_json}")
        try:
            with open(args.input_json, 'r', encoding='utf-8') as f:
                pr_data_list = json.load(f)
            if not isinstance(pr_data_list, list):
                logger.error("JSON file should contain a list of PR data objects.")
                return [] # Return empty list on error

            logger.info(f"Analyzing {len(pr_data_list)} pull requests from JSON file")
            for pr_data in pr_data_list:
                # Use analyze_pull_request for structured JSON input
                analysis = analyzer.analyze_pull_request(pr_data)
                analysis_results.append(analysis)
        except FileNotFoundError:
            logger.error(f"Error: Input JSON file '{args.input_json}' not found")
            # Optionally return specific error structure or re-raise
            analysis_results.append({"error": f"File not found: {args.input_json}"})
        except json.JSONDecodeError:
            logger.error(f"Error: '{args.input_json}' is not a valid JSON file")
            analysis_results.append({"error": f"Invalid JSON in file: {args.input_json}"})
        except Exception as e:
            logger.error(f"Error processing JSON file '{args.input_json}': {e}", exc_info=True)
            analysis_results.append({"error": f"Error processing JSON file '{args.input_json}': {str(e)}"})


    elif args.input_diff:
        logger.info(f"Analyzing diff file: {args.input_diff}")
        try:
            with open(args.input_diff, 'r', encoding='utf-8') as f:
                diff_content = f.read()
            # Use analyze_code_changes for raw diff input
            analysis = analyzer.analyze_code_changes(diff_content)
            analysis_results.append(analysis)
        except FileNotFoundError:
            logger.error(f"Error: Input diff file '{args.input_diff}' not found")
            analysis_results.append({"error": f"File not found: {args.input_diff}"})
        except Exception as e:
            logger.error(f"Error processing diff file '{args.input_diff}': {e}", exc_info=True)
            analysis_results.append({"error": f"Error processing diff file '{args.input_diff}': {str(e)}"})


    elif args.input_repo:
        logger.info(f"Analyzing repository file: {args.input_repo}")
        try:
            # 1. Parse the repo file using the moved function
            repository_files = parse_repository_file(args.input_repo)

            if not repository_files:
                 # parse_repository_file logs warnings, return empty result
                 analysis_results.append({
                    "error": f"No files parsed from repository file: {args.input_repo}",
                    "quality_issues": [], "good_practices": [], "patterns": [],
                    "anti_patterns": [], "overall_score": None, "raw_response": ""
                 })
            else:
                # 2. Generate the diff content using the moved function
                diff_content = generate_diff_content(repository_files)

                if not diff_content:
                    analysis_results.append({
                       "error": f"Generated empty diff from repository file: {args.input_repo}",
                       "quality_issues": [], "good_practices": [], "patterns": [],
                       "anti_patterns": [], "overall_score": None, "raw_response": ""
                    })
                else:
                     # 3. Analyze the generated diff content
                    analysis = analyzer.analyze_code_changes(diff_content)
                    analysis_results.append(analysis)

        except FileNotFoundError: # Already caught by parse_repository_file, but good practice
             logger.error(f"Error: Input repository file '{args.input_repo}' not found")
             analysis_results.append({"error": f"File not found: {args.input_repo}"})
        except Exception as e:
            # Catch potential errors from parsing or diff generation
            logger.error(f"Error processing repository file '{args.input_repo}': {e}", exc_info=True)
            analysis_results.append({"error": f"Error processing repository file '{args.input_repo}': {str(e)}"})

    return analysis_results

def run_analysis_from_github(analyzer: MergeRequestAnalyzer, pr_data_list: list) -> list:
    """Runs analysis on PR data fetched from GitHub."""
    analysis_results = []
    logger.info(f"Analyzing {len(pr_data_list)} pull requests fetched from GitHub")
    for pr_data in pr_data_list:
        try:
            # Analyze using the structured PR data method
            analysis = analyzer.analyze_pull_request(pr_data)
            analysis_results.append(analysis)
        except Exception as e:
            # Catch errors during analysis of a specific PR
            pr_url = pr_data.get('html_url', 'Unknown PR')
            logger.error(f"Error analyzing PR '{pr_url}': {e}", exc_info=True)
            analysis_results.append({"error": f"Error analyzing PR '{pr_url}': {str(e)}"})

    return analysis_results

def output_results(analysis_results: list, output_file: str | None):
    """Outputs analysis results to stdout or a file."""
    # Filter out potential null/empty results if needed, or keep them
    valid_results = [res for res in analysis_results if res] # Simple filter
    if not valid_results:
        logger.warning("No valid analysis results to output.")
        return

    output_json = json.dumps(valid_results, indent=2)

    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_json)
            logger.info(f"Analysis results saved to: {output_file}")
        except IOError as e:
            logger.error(f"Error writing output file '{output_file}': {e}")
            # Fallback to stdout if write fails
            print("\n--- Analysis Results (stdout due to file error) ---")
            print(output_json)
            print("----------------------------------------------------\n")
            sys.exit(1)
    else:
        print(output_json)

def main():
    parser = argparse.ArgumentParser(description="Analyze Pull Request data for quality.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input_json", help="JSON file containing PR data (list of PR objects). Multiple PRs analyzed.")
    input_group.add_argument("--input_diff", help="File containing raw git diff content. Single analysis performed.")
    input_group.add_argument("--input_repo", help="Repository file in specific text format. Single analysis performed.")
    input_group.add_argument("--github_user", help="Fetch PRs from GitHub for this user. Multiple PRs analyzed.")

    # Arguments required only if --github_user is provided
    parser.add_argument("--github_repo", help="GitHub repository name (e.g., 'owner/repo'). Required if --github_user is specified.")
    parser.add_argument("--start_date", help="Start date (YYYY-MM-DD) for GitHub fetch.")
    parser.add_argument("--end_date", help="End date (YYYY-MM-DD) for GitHub fetch.")

    parser.add_argument("--output", help="Output file for analysis results (JSON format, default: stdout).")

    args = parser.parse_args()

    # Validate arguments
    use_github = bool(args.github_user)
    if use_github and (not args.start_date or not args.end_date or not args.github_repo):
        parser.error("--start_date, --end_date, and --github_repo are required when using --github_user.")

    # Validate environment variables based on input mode
    validate_env_vars(use_github)

    try:
        # Initialize the analyzer (checks its own env vars)
        analyzer = MergeRequestAnalyzer()
        analysis_results = []

        if use_github:
            pr_data_list = run_github_fetch(args, args.github_repo)
            if pr_data_list:
                analysis_results = run_analysis_from_github(analyzer, pr_data_list)
            else:
                logger.info("No PRs found for the specified criteria on GitHub.")
        else:
            # Analysis from file (JSON, diff, or repo)
            # run_analysis_from_file now returns a list containing analysis result(s)
            analysis_results = run_analysis_from_file(analyzer, args)

        if analysis_results:
            # Check if any result actually contains an error reported by analyzer/parsing
            has_errors = any(res.get("error") for res in analysis_results if isinstance(res, dict))
            output_results(analysis_results, args.output)
            if has_errors:
                 logger.warning("Analysis completed, but one or more items encountered errors (see output JSON).")
            else:
                 logger.info("Analysis completed successfully.")
            # logger.info(f"Analysis results: {analysis_results}") # Avoid printing potentially large results to log
        else:
            logger.info("No analysis results were generated (input might be empty or invalid).")

    except Exception as e:
        # Catch-all for unexpected errors during setup or orchestration
        logger.critical(f"An unexpected critical error occurred in main execution: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
