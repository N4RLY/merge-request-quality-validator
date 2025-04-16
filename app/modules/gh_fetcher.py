# Check notebooks/gh_fetcher_example.ipynb

from github import Github, Auth
from github.Issue import Issue
from datetime import datetime


class GithubFetcher:
    _github_token: str
    _repo_name: str

    _auth: Auth
    _g: Github

    def __init__(
        self,
        repo_name: str,
        github_token: str,
    ):
        self._repo_name = repo_name
        self._github_token = github_token

        self._authorize()

        self._g = Github(auth=self._auth)

    def _authorize(self):
        self._auth = Auth.Token(self._github_token)

    def _prep_issue(self, issue: Issue):
        pr_number = issue.number
        pull = self._g.get_repo(self._repo_name).get_pull(pr_number)
        files = pull.get_files()

        return {
            "title": pull.title,
            "description": pull.body,
            "files": [{"filename": f.filename, "patch": f.patch} for f in files],
            "commits_messages": [c.commit.message for c in pull.get_commits()],
            "comments": [c.body_text for c in pull.get_comments()],
            "url": pull.url, # Optional
        }

    def export_pr_data(self, username: str, start_date: datetime, end_date: datetime):
        query = (
            f"is:pr repo:{self._repo_name} author:{username} is:closed "
            f"closed:{start_date.isoformat()}..{end_date.isoformat()}"
        )

        issues = self._g.search_issues(query)

        return [self._prep_issue(i) for i in issues]
