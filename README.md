# merge-request-quality-validator

# Development
## Prerequisites
- Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
## Installation
- Run in terminal:
```
$ uv install --all-groups
```
- Done!

## Environment Setup
- Copy the example environment file:
```
$ cp .env.example .env
```
- Update the `.env` file with your specific configuration values.

## Running the Application

### Command Line Interface
The application analyzes merge/pull requests for a given GitHub repository within a specified date range.

#### Command Format
```
python main.py --github_repo <owner/repo> --github_user <username> --start_date <YYYY-MM-DD> --end_date <YYYY-MM-DD> --output <output_file.json>
```

#### Parameters
- `--github_repo`: The GitHub repository in format `owner/repo`
- `--github_user`: GitHub username for authentication
- `--start_date`: Start date for analysis (format: YYYY-MM-DD)
- `--end_date`: End date for analysis (format: YYYY-MM-DD)
- `--output`: Output JSON file path

#### Example
```
python main.py --github_repo maybe-finance/maybe --github_user the-spectator --start_date 2025-01-01 --end_date 2025-05-01 --output results.json
```

This command will:
1. Analyze merge requests in the maybe-finance/maybe repository
2. Look at contributions from January 1, 2025 to May 1, 2025
3. Save the results to results.json

### Web Interface (Gradio)
The application also provides a web interface using Gradio for easier interaction.

#### Running the Web Interface
```
python app/gradio_ui.py
```

This will start a local web server and open the interface in your default browser. The interface allows you to:
1. Enter the repository name (format: owner/repo)
2. Specify the GitHub username of the PR author
3. Set the start and end dates for analysis
4. View the analysis results in a formatted markdown display

The results will show:
- Overall quality score
- Quality issues found
- Good practices identified
- Design patterns used
- Anti-patterns detected

#### Example Usage
1. Enter repository name: `octocat/Hello-World`
2. Enter username: `octocat`
3. Set start date: `2024-01-01`
4. Set end date: `2024-03-31`
5. Click "Analyze Pull Requests"

The results will be displayed in the output section below the form.