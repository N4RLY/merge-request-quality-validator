import os
import gradio as gr
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any

from app.modules.analyzer import MergeRequestAnalyzer
from app.modules.gh_fetcher import GithubFetcher

# Load environment variables
load_dotenv()

# Get GitHub token from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is missing. Please check your .env file.")

def format_analysis_result(analysis: Dict[str, Any]) -> str:
    """Format the analysis results into a markdown string."""
    if "error" in analysis:
        return f"## Error\n{analysis['error']}"
    
    markdown = []
    
    # PR Link
    pr_url = analysis.get("pr_url")
    if pr_url:
        pr_url = pr_url.replace("api.", "").replace("/repos", "").replace("pulls", "pull")
        markdown.append(f"[🔗 View Pull Request]({pr_url})\n")
    
    # Overall Score
    score = analysis.get("overall_score", "N/A")
    markdown.append(f"## Overall Score: {score}/10\n")
    
    # Quality Issues
    if analysis.get("quality_issues"):
        markdown.append("### Quality Issues")
        for issue in analysis["quality_issues"]:
            markdown.append(f"- {issue}")
        markdown.append("")
    
    # Good Practices
    if analysis.get("good_practices"):
        markdown.append("### Good Practices")
        for practice in analysis["good_practices"]:
            markdown.append(f"- {practice}")
        markdown.append("")
    
    # Design Patterns
    if analysis.get("patterns"):
        markdown.append("### Design Patterns Used")
        for pattern in analysis["patterns"]:
            markdown.append(f"- {pattern}")
        markdown.append("")
    
    # Anti-patterns
    if analysis.get("anti_patterns"):
        markdown.append("### Anti-patterns")
        for anti_pattern in analysis["anti_patterns"]:
            markdown.append(f"- {anti_pattern}")
        markdown.append("")
    
    return "\n".join(markdown)

def analyze_prs(
    repo_name: str,
    username: str,
    start_date: str,
    end_date: str
) -> str:
    """Analyze pull requests and return formatted results."""
    try:
        # Initialize components
        analyzer = MergeRequestAnalyzer()
        fetcher = GithubFetcher(repo_name=repo_name, github_token=GITHUB_TOKEN)
        
        # Parse dates
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        # Fetch PR data
        pr_data_list = fetcher.export_pr_data(username, start, end)
        
        if not pr_data_list:
            return "No pull requests found for the specified criteria."
        
        # Analyze each PR
        results = []
        for pr_data in pr_data_list:
            analysis = analyzer.analyze_pull_request(pr_data)
            results.append(format_analysis_result(analysis))
        
        return "\n\n---\n\n".join(results)
    
    except Exception as e:
        return f"Error during analysis: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="Merge Request Quality Analyzer") as demo:
    gr.Markdown("# Merge Request Quality Analyzer")
    gr.Markdown("Analyze the quality of pull requests in a GitHub repository.")
    
    with gr.Row():
        with gr.Column():
            repo_name = gr.Textbox(
                label="Repository Name",
                placeholder="owner/repo",
                info="Format: owner/repo (e.g., octocat/Hello-World)"
            )
            username = gr.Textbox(
                label="GitHub Username",
                placeholder="username",
                info="The username of the PR author"
            )
            start_date = gr.Textbox(
                label="Start Date",
                placeholder="YYYY-MM-DD",
                info="Format: YYYY-MM-DD"
            )
            end_date = gr.Textbox(
                label="End Date",
                placeholder="YYYY-MM-DD",
                info="Format: YYYY-MM-DD"
            )
            analyze_btn = gr.Button("Analyze Pull Requests")
    
    with gr.Row():
        output = gr.Markdown(label="Analysis Results")
    
    analyze_btn.click(
        fn=analyze_prs,
        inputs=[repo_name, username, start_date, end_date],
        outputs=output
    )

if __name__ == "__main__":
    demo.launch() 