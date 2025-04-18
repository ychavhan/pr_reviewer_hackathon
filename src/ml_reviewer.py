# Simple AI-based PR Reviewer (Backend Only)
# Tech: Flask + OpenAI + GitHub API

from flask import Flask, request, jsonify
from github import Github
import openai
import os

app = Flask(__name__)

# Set your tokens here
GITHUB_TOKEN = "your_github_token"
OPENAI_API_KEY = "your_openai_key"
openai.api_key = OPENAI_API_KEY
g = Github(GITHUB_TOKEN)

@app.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.json
    if "pull_request" in data:
        pr_url = data["pull_request"]["url"]
        repo_full = data["repository"]["full_name"]
        pr_number = data["number"]

        repo = g.get_repo(repo_full)
        pr = repo.get_pull(pr_number)
        diff = pr.diff_url  # You can also use pr.get_files() for better granularity

        # Generate a review using OpenAI
        review_text = generate_ai_review(pr.title, pr.body)

        # Post a comment to the PR
        pr.create_issue_comment(f"🤖 AI Review:\n{review_text}")
        return jsonify({"msg": "Review posted"}), 200
    return jsonify({"msg": "No PR found"}), 400

def generate_ai_review(title, body):
    prompt = f"Review this pull request for code quality, bugs, and suggestions.\nTitle: {title}\nDescription: {body}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful code reviewer."},
            {"role": "user", "content": prompt}
        ]
    )
    return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    app.run(port=5000)
