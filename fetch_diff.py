import time
from dotenv import load_dotenv
import jwt  # from PyJWT
import os
load_dotenv()
import requests
from google import genai

APP_ID = os.environ.get("GITHUB_APP_ID", "")
PRIVATE_KEY_PATH = "keys/devpulse-private-key.pem"
INSTALLATION_ID = "162424050"

OWNER = "Audrey-Okumu"
REPO = "DevPulse"
PR_NUMBER = 1 

def get_pr_files(installation_token):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/files"
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers, params={"per_page": 100})
    response.raise_for_status()
    return response.json()

def post_comment(installation_token, body):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.post(url, headers=headers, json={"body": body})
    response.raise_for_status()
    return response.json()

def generate_jwt():
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()

    now = int(time.time())
    payload = {
        "iat": now - 60,       # issued at (60s in the past, to allow for clock drift)
        "exp": now + 600,      # expires in 10 minutes (GitHub's max)
        "iss": APP_ID,         # issuer = your App ID
    }
    return jwt.encode(payload, private_key, algorithm="RS256")



def get_installation_token(jwt_token):
    url = f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["token"]


def get_ai_review(filename, patch):
    client = genai.Client(api_key=os.environ.get("LLM_API_KEY"))

    prompt = f"""You are a senior Python code reviewer. Review the following diff from the file `{filename}`.

Focus on:
- Bugs or correctness issues
- Style issues (PEP 8, naming, readability)
- Risks (security, performance, edge cases)

Be concise. If there's nothing significant to flag, say so briefly rather than inventing issues.

Diff:
{patch}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return response.text

if __name__ == "__main__":
    jwt_token = generate_jwt()
    print("JWT generated.")

    installation_token = get_installation_token(jwt_token)
    print("Installation token acquired.")

    files = get_pr_files(installation_token)
    print(f"Found {len(files)} changed file(s):\n")

    review_sections = []

    for f in files:
        if not f["filename"].endswith(".py"):
            print(f"Skipping {f['filename']} (not a Python file)")
            continue

        if "patch" not in f:
            print(f"Skipping {f['filename']} (no patch available)")
            continue

        print("=" * 60)
        print(f"Reviewing: {f['filename']}")
        review = get_ai_review(f["filename"], f["patch"])
        print(review)
        review_sections.append(f"### `{f['filename']}`\n\n{review}")

    if review_sections:
        comment_body = "## 🤖 AI Code Review\n\n" + "\n\n---\n\n".join(review_sections)
        result = post_comment(installation_token, comment_body)
        print(f"\nComment posted: {result['html_url']}")
    else:
        print("\nNo Python files to review — no comment posted.")