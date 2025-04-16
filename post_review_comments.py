post_review_code = ''
import os
import requests
import json

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
PR_NUMBER = os.environ.get("GITHUB_REF", "/pull/0").split("/")[-1]

with open("suggestions.txt") as f:
    body = f.read()

url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

response = requests.post(url, headers=headers, data=json.dumps({"body": body}))
print("GitHub comment response:", response.status_code, response.text)
