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
            max_prompt_length = 32000
            if len(prompt) > max_prompt_length:
                logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to {max_prompt_length} chars")
                prompt = prompt[:max_prompt_length]
            
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
            return {"error": f"API request failed: {str(e)}"}
    
    def _build_analysis_prompt(self, diff_content: str) -> str:
        """Builds the prompt for the Yandex Cloud API."""
        return f"""You are a senior Python code reviewer. Analyze this code diff and respond with a single JSON object.

1. Code quality issues:
   • List each issue, explain why it’s problematic, and reference file:line ranges.
   • Classify severity:
     – Critical defect (crash, security, data loss): –2.0…–3.0
     – Serious anti-pattern (God Class, Spaghetti Code, Shotgun Surgery): –1.0
     – Medium anti-pattern (Duplicated Code, Primitive Obsession, Magic Numbers, Long Parameter List): –0.5
     – Minor code smell (PEP8 violations, long lines, poor naming): –0.1

2. Good practices & design patterns:
   • Identify patterns (Factory, Strategy, Observer, Singleton, Context Manager, etc.).
   • Explain how and where each is applied.

3. Overall quality score (0–10) with justification:
   • Start from 10.0  
   • Apply penalties Σ penalty_j and bonuses Σ bonus_i:
       – Penalties per severity above.
       + Bonuses:
         + Design patterns used: +0.3 each (max +1.0)
         + Refactored inherited anti-pattern: +1.0
         + Added or improved tests: +0.5
         + Docstrings & type hints: +0.2
   • Clamp raw_score = min(10.0, max(0.0, 10.0 + Σ bonus_i – Σ penalty_j))
   • Apply complexity multiplier K:
       – Low (≤50 lines & ≤2 files, trivial): K = 0.8
       – Medium (50–200 lines or mixed complexity): K = 1.0
       – High (≥200 lines & ≥10 files or deep logic/security): K = 1.2
   • Compute overall_score = round(raw_score_clamped × K, 1)

4. Anti-patterns:
   • List each anti-pattern name.
   • Explain why it’s bad.
   • Indicate status: “new” (introduced), “existing” (inherited), or “fixed” (removed).

5. Review comments:
   • Summarize reviewer feedback and note which comments were addressed or remain unresolved.

6. Few-shot example:

Findings                      | Category                    | Weight | MR Complexity | Δ
------------------------------|-----------------------------|--------|---------------|-----
Introduced God Class          | Serious anti-pattern        | –1.0   | Medium (1.0)  | –1.0
Added Factory for parser      | Design pattern              | +0.3   |               | +0.3
Duplicated code               | Medium anti-pattern         | –0.5   |               | –0.5
Added tests                   | Testing                     | +0.5   |               | +0.5
Subtotal before complexity**  |                             |        |               | **–0.7
Complexity multiplier (K=1.0) |                             |        |               | ×1.0
Final MR score                |                             |        |               | 9.3

Example output:
```json
{{
  "quality_issues": [
    "God Class in models/user.py:1–200 — class handles too many responsibilities",
    "Duplicated data formatting logic in utils.py:50–60 and report.py:120–130"
  ],
  "good_practices": [
    "Factory pattern used to instantiate parser based on file type",
    "Added unit tests for edge cases"
  ],
  "patterns": [
    "Factory"
  ],
  "anti_patterns": [
    "God Class",
    "Duplicated Code"
  ],
  "overall_score": 9.3
}}
```

Code diff:
{diff_content}
"""

    def analyze_code_changes(self, diff_content: str) -> Dict[str, Any]:
        """
        Analyze code changes provided as a diff string.
        
        Args:
            diff_content: Git diff content of the merge request or generated diff.
            
        Returns:
            Analysis results
        """
        logger.info("Starting code changes analysis using diff content")
        
        try:
            if not diff_content:
                logger.warning("Diff content is empty, returning empty analysis.")
                return {
                    "quality_issues": [],
                    "good_practices": [],
                    "patterns": [],
                    "anti_patterns": [],
                    "overall_score": None,
                    "raw_response": "Input diff content was empty.",
                    "error": "Input diff content was empty."
                }
            
            prompt = self._build_analysis_prompt(diff_content)
            
            response = self.call_yandex_cloud_api(prompt)
            
            return self._parse_analysis_response(response)
            
        except Exception as e:
            logger.error(f"Error during code changes analysis: {str(e)}", exc_info=True)
            return {"error": f"Error during code changes analysis: {str(e)}"}
    
    def analyze_pull_request(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a pull request from structured data (title, description, files with patches).
        
        Args:
            pr_data: Dictionary containing PR info ('title', 'description', 'files').
                     'files' is a list of dicts with 'filename' and 'patch'.
            
        Returns:
            Analysis results
        """
        logger.info("Starting pull request analysis using structured data")
        
        try:
            if not isinstance(pr_data, dict):
                logger.error("PR data must be a dictionary")
                return {"error": "PR data must be a dictionary"}
            
            title = pr_data.get('title', 'N/A')
            description = pr_data.get('description', 'No description provided.')
            files = pr_data.get('files', [])
            
            if not isinstance(files, list):
                logger.error("'files' must be a list")
                return {"error": "'files' must be a list"}
            
            if not files:
                logger.warning("No files found in the pull request data, returning empty analysis.")
                return {
                    "quality_issues": [], "good_practices": [], "patterns": [],
                    "anti_patterns": [], "overall_score": None,
                    "raw_response": "No files found in PR data.",
                    "error": "No files found in PR data."
                }
            
            diff_parts = []
            diff_parts.append(f"# Pull Request: {title}")
            diff_parts.append(f"\n## Description\n{description}\n")
            diff_parts.append("## Changes\n")
            
            for file_info in files:
                if not isinstance(file_info, dict):
                    logger.warning(f"Skipping invalid file entry in PR data: {file_info}")
                    continue
                
                filename = file_info.get('filename')
                patch = file_info.get('patch')
                
                if filename and patch:
                    diff_parts.append(f"--- a/{filename}")
                    diff_parts.append(f"+++ b/{filename}")
                    diff_parts.append("```diff")
                    diff_parts.append(patch.strip('\n'))
                    diff_parts.append("```\n")
                elif filename:
                    logger.warning(f"File '{filename}' in PR data has no patch content.")
                    diff_parts.append(f"--- a/{filename}")
                    diff_parts.append(f"+++ b/{filename}")
                    diff_parts.append("(No patch content provided)\n")
            
            diff_content = "\n".join(diff_parts)
            
            prompt = self._build_analysis_prompt(diff_content)
            response = self.call_yandex_cloud_api(prompt)
            
            return self._parse_analysis_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing pull request: {str(e)}", exc_info=True)
            return {"error": f"Error analyzing pull request: {str(e)}"}
    
    def _parse_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and structure the API response, handling JSON and fallbacks."""
        if "error" in response:
            logger.error(f"API call failed: {response['error']}")
            return {
                "quality_issues": [], "good_practices": [], "patterns": [],
                "anti_patterns": [], "overall_score": None,
                "raw_response": f"API Error: {response['error']}",
                "error": f"API Error: {response['error']}"
            }
        
        message = ""
        raw_api_response_data = response.get("result", {}).get("alternatives", [])
        
        if raw_api_response_data:
            first_alt = raw_api_response_data[0]
            if isinstance(first_alt, dict):
                if 'message' in first_alt and isinstance(first_alt['message'], dict) and 'text' in first_alt['message']:
                    message = first_alt['message']['text']
                elif 'text' in first_alt:
                    message = first_alt['text']
                else:
                    message = str(first_alt)
                    logger.warning(f"Unexpected dictionary structure in alternative: {message[:100]}...")
            elif hasattr(first_alt, 'text'):
                message = first_alt.text
            else:
                message = str(first_alt)
                logger.warning(f"Unexpected alternative type: {type(first_alt)}. Content: {message[:100]}...")
        else:
            logger.warning("API response contained no alternatives.")
            return {
                "quality_issues": [], "good_practices": [], "patterns": [],
                "anti_patterns": [], "overall_score": None,
                "raw_response": "API response contained no alternatives.",
                "error": "API response contained no alternatives."
            }
        
        analysis = {
            "quality_issues": [],
            "good_practices": [],
            "patterns": [],
            "anti_patterns": [],
            "overall_score": None,
            "raw_response": message
        }
        
        parsed_json = None
        try:
            cleaned_message = message.strip()
            if cleaned_message.startswith("```json"):
                cleaned_message = cleaned_message[7:]
                if cleaned_message.endswith("```"):
                    cleaned_message = cleaned_message[:-3]
                cleaned_message = cleaned_message.strip()
            if cleaned_message.startswith('{') and cleaned_message.endswith('}'):
                parsed_json = json.loads(cleaned_message)
                logger.info("Successfully parsed cleaned API response as JSON.")
            else:
                logger.warning("Cleaned message does not appear to be a JSON object. Trying regex.")

        except json.JSONDecodeError as json_err:
            logger.warning(f"Failed to parse cleaned response directly as JSON: {json_err}. Trying regex extraction.")
            parsed_json = None

        if parsed_json is None:
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", message, re.DOTALL)
            if json_match:
                json_block = json_match.group(1)
                try:
                    parsed_json = json.loads(json_block)
                    logger.info("Successfully parsed JSON block extracted via regex.")
                except json.JSONDecodeError as inner_json_err:
                    logger.warning(f"Failed to parse extracted JSON block: {inner_json_err}. Proceeding without parsed JSON.")
                    parsed_json = None
            else:
                logger.warning("Could not find JSON block via regex.")

        if parsed_json is not None and isinstance(parsed_json, dict):
            analysis["quality_issues"] = parsed_json.get("quality_issues", [])
            analysis["good_practices"] = parsed_json.get("good_practices", [])
            analysis["patterns"] = parsed_json.get("patterns", [])
            analysis["anti_patterns"] = parsed_json.get("anti_patterns", [])
            score_val = parsed_json.get("overall_score")

            if score_val is not None:
                try:
                    analysis["overall_score"] = float(score_val)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert overall_score '{score_val}' to float.")
                    analysis["overall_score"] = None
            for key in ["quality_issues", "good_practices", "patterns", "anti_patterns"]:
                if not isinstance(analysis[key], list):
                    logger.warning(f"Field '{key}' in parsed JSON is not a list, resetting to empty list.")
                    analysis[key] = []

        else:
            logger.warning("JSON parsing failed. Falling back to less reliable regex extraction for analysis fields.")

            quality_match = re.search(r"1\.\s*Code quality issues:?\s*\n(.*?)(?=\n\s*2\.|\Z)", message, re.DOTALL | re.IGNORECASE)
            if quality_match:
                quality_text = quality_match.group(1).strip()
                issues = re.findall(r"^\s*[-•*]\s+(.*)", quality_text, re.MULTILINE)
                if not issues: issues = re.findall(r"^\s*\d+\.\s+(.*)", quality_text, re.MULTILINE)
                analysis["quality_issues"] = [issue.strip() for issue in issues if issue.strip()]

            practices_match = re.search(r"2\.\s*Good practices:?\s*\n(.*?)(?=\n\s*3\.|\Z)", message, re.DOTALL | re.IGNORECASE)
            if practices_match:
                practices_text = practices_match.group(1).strip()
                practices = re.findall(r"^\s*[-•*]\s+(.*)", practices_text, re.MULTILINE)
                if not practices: practices = re.findall(r"^\s*\d+\.\s+(.*)", practices_text, re.MULTILINE)
                analysis["good_practices"] = [practice.strip() for practice in practices if practice.strip()]

            score_match = re.search(r"3\.\s*Overall quality score:?\s*.*?(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10", message, re.DOTALL | re.IGNORECASE)
            if score_match:
                try:
                    analysis["overall_score"] = float(score_match.group(1))
                except ValueError:
                    logger.warning(f"Could not parse score from regex match: {score_match.group(1)}")
                    analysis["overall_score"] = None

            logger.warning("Fallback regex extraction completed. Patterns and anti-patterns might be missing or inaccurate.")

        return analysis

if __name__ == "__main__":
    import argparse
    
    logger.info("Starting merge request analyzer (direct execution)")
    
    parser = argparse.ArgumentParser(description="Analyze code changes directly (for testing)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--diff", help="Path to a file containing git diff content")
    group.add_argument("--pr", help="Path to a JSON file containing pull request data (structured)")
    parser.add_argument("--output", help="Path to output file (optional)")
    
    args = parser.parse_args()
    
    try:
        analyzer = MergeRequestAnalyzer()
        analysis = {}
        
        if args.pr:
            try:
                with open(args.pr, 'r', encoding='utf-8') as f:
                    pr_data = json.load(f)
                logger.info(f"Analyzing pull request from: {args.pr}")
                analysis = analyzer.analyze_pull_request(pr_data)
            except FileNotFoundError:
                logger.error(f"Error: Input PR JSON file '{args.pr}' not found.")
                analysis = {"error": f"File not found: {args.pr}"}
            except json.JSONDecodeError:
                logger.error(f"Error: Could not decode JSON from '{args.pr}'.")
                analysis = {"error": f"Invalid JSON in file: {args.pr}"}
        
        elif args.diff:
            try:
                with open(args.diff, 'r', encoding='utf-8') as f:
                    diff_content = f.read()
                logger.info(f"Analyzing diff file: {args.diff}")
                analysis = analyzer.analyze_code_changes(diff_content)
            except FileNotFoundError:
                logger.error(f"Error: Input diff file '{args.diff}' not found.")
                analysis = {"error": f"File not found: {args.diff}"}
        
        output_json = json.dumps(analysis, indent=2)
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_json)
                logger.info(f"Analysis results saved to: {args.output}")
            except IOError as e:
                logger.error(f"Error writing output file '{args.output}': {e}")
                print("\n--- Analysis Results (stdout due to file error) ---")
                print(output_json)
                print("----------------------------------------------------\n")
        
        else:
            print(output_json)
        
        if "error" not in analysis:
            logger.info("Analysis completed successfully.")
        else:
            logger.warning(f"Analysis completed with an error: {analysis.get('error')}")
        
    except Exception as e:
        logger.critical(f"A critical error occurred during direct execution: {str(e)}", exc_info=True)