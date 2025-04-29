# 🧠 merge-request-quality-validator

This project was developed as part of the **LLM Coding Challenge 2025** — a case study provided by [AlfaStrakhovanie](https://llm-challenge.com/).

## 📌 Case Description

**Goal:**  
Create an AI-powered tool that analyzes a developer's pull/merge requests over a specified period and generates a **code quality report**.

**The challenge focuses on:**
- Automated **code quality assessment**
- Detection of **anti-patterns** and architectural issues
- Highlighting **strengths** and **growth areas**
- Tracking **code authorship** and historical changes

**Why is this important for the company?**
- To objectively evaluate the effectiveness of technical teams
- To improve the accuracy and transparency of developer assessments (regrading)
- To provide developers with actionable, fact-based feedback for professional growth

## 👥 Team

- **Arthur Babkin** — Product Management, Machine Learning Engineer  
- **Alexander Maly** — Machine Learning Engineer, DevOps  
- **Alexey Tkachenko** — Backend Development, DevOps

# Development
## Prerequisites
- Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
## Installation
- Run in terminal:
```
$ uv sync --all-groups
```
- Done!

## Environment Setup
- Copy the example environment file:
```
$ cp .env.example .env
```
- Create a classic GitHub personal access token:
  1. Go to your GitHub account settings
  2. Navigate to Developer Settings > Personal access tokens > Tokens (classic)
  3. Click "Generate new token (classic)"
  4. Give your token a name and select at least the `repo` scope
  5. Click "Generate token" and copy the generated token
- Update the `.env` file with your configuration values:
  ```
  GITHUB_TOKEN=your_github_token_here
  YANDEX_CLOUD_API_KEY=your_api_key_here
  YANDEX_CLOUD_FOLDER_ID=your_folder_id_here
  YANDEX_CLOUD_MODEL_NAME=your_model_name_here
  ```

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
python -m app.gradio_ui
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
1. Enter repository name: `run-llama/llama_index`
2. Enter username: `bmax`
3. Set start date: `2024-01-01`
4. Set end date: `2025-12-31`
5. Click "Analyze Pull Requests"

The results will be displayed in the output section below the form.

### Docker
The application can also be run using Docker, which provides an isolated environment with all dependencies pre-installed.

#### Prerequisites
- Docker installed on your system
- Docker Compose (optional, but recommended)

#### Using Docker Compose (Recommended)
1. Make sure you have a `.env` file with your API keys:
```
$ cp .env.example .env
```
2. Edit the `.env` file with your actual API keys

3. Build and start the container:
```
$ docker-compose up
```

4. Access the Gradio interface at http://localhost:7860

#### Using Docker Directly
1. Build the Docker image:
```
$ docker build -t merge-request-validator .
```

2. Run the container:
```
$ docker run -p 7860:7860 -v $(pwd)/.env:/app/.env -e GRADIO_SERVER_NAME=0.0.0.0 merge-request-validator
```

3. Access the Gradio interface at http://localhost:7860

#### Environment Variables
When running with Docker, you can either:
- Mount your `.env` file as shown above
- Pass environment variables directly to the container:
```
$ docker run -p 7860:7860 -e GITHUB_TOKEN=your_token -e YANDEX_CLOUD_API_KEY=your_key -e GRADIO_SERVER_NAME=0.0.0.0 merge-request-validator
```
