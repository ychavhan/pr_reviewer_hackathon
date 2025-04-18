#!/usr/bin/env python3
import requests
import time
import logging

logger = logging.getLogger(__name__)


class GitHubAPI:
    """
    Handles all GitHub API interactions for the PR reviewer
    """

    def __init__(self, token, base_url="https://api.github.com"):
        """
        Initialize the GitHub API client

        Args:
            token (str): GitHub API token
            base_url (str): GitHub API base URL
        """
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        # Initialize rate limit tracking
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0

    def _make_request(self, method, url, data=None, params=None):
        """
        Make a request to the GitHub API with rate limit handling

        Args:
            method (str): HTTP method (GET, POST, etc.)
            url (str): API endpoint URL
            data (dict, optional): Request body for POST/PUT
            params (dict, optional): Query parameters

        Returns:
            dict: API response as JSON
        """
        # Check if we're near the rate limit
        if self.rate_limit_remaining < 10:
            current_time = time.time()
            if current_time < self.rate_limit_reset:
                sleep_time = self.rate_limit_reset - current_time + 1
                logger.warning(f"Rate limit near, sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)

        full_url = url if url.startswith("http") else f"{self.base_url}{url}"
        response = requests.request(
            method=method,
            url=full_url,
            headers=self.headers,
            json=data,
            params=params
        )

        # Update rate limit information
        if 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        if 'X-RateLimit-Reset' in response.headers:
            self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])

        # Handle errors
        if response.status_code >= 400:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            response.raise_for_status()

        return response.json() if response.text else {}

    def get_pull_request(self, repo, pr_number):
        """
        Fetch PR information

        Args:
            repo (str): Repository in format "owner/repo"
            pr_number (int/str): PR number

        Returns:
            dict: PR information
        """
        url = f"/repos/{repo}/pulls/{pr_number}"
        return self._make_request("GET", url)

    def get_pr_files(self, repo, pr_number, per_page=100):
        """
        Fetch files changed in the PR with pagination support

        Args:
            repo (str): Repository in format "owner/repo"
            pr_number (int/str): PR number
            per_page (int): Items per page (max 100)

        Returns:
            list: Files changed in the PR
        """
        url = f"/repos/{repo}/pulls/{pr_number}/files"
        page = 1
        all_files = []

        while True:
            files_page = self._make_request(
                "GET",
                url,
                params={"per_page": per_page, "page": page}
            )

            all_files.extend(files_page)

            # Stop if we got fewer items than the max per page
            if len(files_page) < per_page:
                break

            page += 1

        return all_files

    def create_review_comment(self, repo, pr_number, commit_id, path, line, body):
        """
        Create a review comment on a specific line of code

        Args:
            repo (str): Repository in format "owner/repo"
            pr_number (int/str): PR number
            commit_id (str): Commit SHA
            path (str): File path
            line (int): Line number
            body (str): Comment text

        Returns:
            dict: Created comment
        """
        url = f"/repos/{repo}/pulls/{pr_number}/comments"
        data = {
            "commit_id": commit_id,
            "path": path,
            "line": line,
            "body": body
        }
        return self._make_request("POST", url, data=data)

    def create_issue_comment(self, repo, pr_number, body):
        """
        Create a comment on the PR (not tied to a specific line)

        Args:
            repo (str): Repository in format "owner/repo"
            pr_number (int/str): PR number
            body (str): Comment text

        Returns:
            dict: Created comment
        """
        url = f"/repos/{repo}/issues/{pr_number}/comments"
        data = {"body": body}
        return self._make_request("POST", url, data=data)

    def create_review(self, repo, pr_number, commit_id, comments=None, body="", event="COMMENT"):
        """
        Create a full review with optional inline comments

        Args:
            repo (str): Repository in format "owner/repo"
            pr_number (int/str): PR number
            commit_id (str): Commit SHA
            comments (list, optional): List of comment objects
            body (str): Review body text
            event (str): Review event type (COMMENT, APPROVE, REQUEST_CHANGES)

        Returns:
            dict: Created review
        """
        url = f"/repos/{repo}/pulls/{pr_number}/reviews"
        data = {
            "commit_id": commit_id,
            "body": body,
            "event": event
        }
        if comments:
            data["comments"] = comments

        return self._make_request("POST", url, data=data)

    def get_commit(self, repo, commit_sha):
        """
        Get commit details

        Args:
            repo (str): Repository in format "owner/repo"
            commit_sha (str): Commit SHA

        Returns:
            dict: Commit information
        """
        url = f"/repos/{repo}/commits/{commit_sha}"
        return self._make_request("GET", url)

    def get_file_content(self, repo, path, ref):
        """
        Get file content from repository

        Args:
            repo (str): Repository in format "owner/repo"
            path (str): File path
            ref (str): Branch name or commit SHA

        Returns:
            dict: File content information
        """
        url = f"/repos/{repo}/contents/{path}"
        return self._make_request("GET", url, params={"ref": ref})