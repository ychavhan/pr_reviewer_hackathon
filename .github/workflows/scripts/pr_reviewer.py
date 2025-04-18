#!/usr/bin/env python3
import os
import logging
import sys
import time
from datetime import datetime

# Add the scripts directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from github_api import GitHubAPI
from ai_reviewer import AICodeReviewer
from utils import filter_files, parse_patch_for_line, setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Get environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PR_NUMBER = os.environ.get("PR_NUMBER")
REPO_NAME = os.environ.get("REPO_NAME")

# Load configuration from file if available
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config/reviewer_config.json")
config = {}
if os.path.exists(CONFIG_PATH):
    import json

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

# Default configuration values
MAX_FILES = config.get("max_files", 10)
MAX_CHANGES = config.get("max_changes", 500)
AI_MODEL = config.get("ai_model", "gpt-4-turbo")
REVIEW_EVENT = config.get("review_event", "COMMENT")  # COMMENT, APPROVE, REQUEST_CHANGES


def main():
    """Main entry point for the PR reviewer"""
    logger.info(f"Starting AI PR Review for PR #{PR_NUMBER} in {REPO_NAME}")

    # Validate required environment variables
    if not all([GITHUB_TOKEN, OPENAI_API_KEY, PR_NUMBER, REPO_NAME]):
        logger.error("Missing required environment variables")
        sys.exit(1)

    # Initialize API clients
    github = GitHubAPI(GITHUB_TOKEN)
    ai_reviewer = AICodeReviewer(OPENAI_API_KEY, model=AI_MODEL)

    try:
        # Get PR details
        pr_data = github.get_pull_request(REPO_NAME, PR_NUMBER)
        pr_files = github.get_pr_files(REPO_NAME, PR_NUMBER)

        commit_id = pr_data["head"]["sha"]
        pr_title = pr_data["title"]
        pr_description = pr_data.get("body", "") or "No description provided"
        base_branch = pr_data["base"]["ref"]
        head_branch = pr_data["head"]["ref"]

        logger.info(f"PR Title: {pr_title}")
        logger.info(f"Number of files changed: {len(pr_files)}")

        # Filter files to review
        files_to_review = filter_files(pr_files, MAX_CHANGES, config.get("file_exclusions", []))
        logger.info(f"Files to review after filtering: {len(files_to_review)}")

        # Process files
        review_comments = []
        file_names = []
        processed_files = 0

        for file_data in files_to_review[:MAX_FILES]:
            filename = file_data["filename"]
            file_names.append(filename)

            # Skip files without patches
            patch = file_data.get("patch")
            if not patch:
                logger.info(f"No patch available for {filename}")
                continue

            logger.info(f"Analyzing {filename}...")

            # Get AI analysis
            review = ai_reviewer.analyze_file_change(filename, patch)

            # Find the appropriate line for the comment
            line = parse_patch_for_line(patch)

            # Create comment object for batch review submission
            comment = {
                "path": filename,
                "line": line,
                "body": f"### AI Code Review\n\n{review}"
            }
            review_comments.append(comment)

            processed_files += 1

            # Add a small delay to avoid rate limits
            time.sleep(1)

        # Generate overall summary
        logger.info("Generating PR summary...")
        summary = ai_reviewer.generate_pr_summary(
            pr_title,
            pr_description,
            file_names,
            base_branch,
            head_branch
        )

        # Submit the review
        logger.info("Submitting review to GitHub...")

        # Add timestamp to summary
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        summary_with_footer = f"{summary}\n\n---\n*AI PR Review generated at {timestamp}*"

        # Post the review
        if review_comments:
            github.create_review(
                REPO_NAME,
                PR_NUMBER,
                commit_id,
                comments=review_comments,
                body=summary_with_footer,
                event=REVIEW_EVENT
            )
        else:
            # If no file comments, just post the summary as a regular comment
            github.create_issue_comment(REPO_NAME, PR_NUMBER, summary_with_footer)

        logger.info("PR review completed successfully!")

    except Exception as e:
        logger.exception(f"Error during PR review: {str(e)}")
        # Post error as comment if possible
        try:
            error_message = f"## ⚠️ AI PR Review Error\n\nThe automated PR review encountered an error:\n```\n{str(e)}\n```\n\nPlease check the GitHub Action logs for details."
            github.create_issue_comment(REPO_NAME, PR_NUMBER, error_message)
        except Exception as comment_error:
            logger.error(f"Failed to post error message to PR: {str(comment_error)}")


if __name__ == "__main__":
    main()