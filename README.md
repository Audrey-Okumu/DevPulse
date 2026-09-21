# DevPulse Reviewer

An automated code review bot for GitHub pull requests, powered by AI.

DevPulse listens for pull request activity on a GitHub repository, fetches the diff, sends it to an LLM for review, and posts the results back as a single summary comment on the PR — flagging bugs, style issues, and risks before a human reviewer even looks at it.

## How it works

1. A GitHub App installed on a repo sends a webhook to this app whenever a PR is opened or updated.
2. The webhook handler verifies the request, deduplicates it, and hands it off to a Celery background task.
3. The task authenticates as the GitHub App installation and fetches the PR's changed files.
4. Each changed Python file's diff is sent to an LLM (Gemini) with a review prompt.
5. The per-file reviews are combined into a single Markdown comment and posted back to the PR via the GitHub API.

## Tech stack

- **Django** + **PostgreSQL** — backend, tracks installations and reviewed PRs
- **Celery** + **Redis** — asynchronous background processing
- **GitHub App** — webhooks, diff fetching, comment posting
- **Gemini API** — code review generation

## Architecture

```
GitHub PR event
      │
      ▼
Webhook endpoint (Django) ── verifies signature, dedupes, responds 200
      │
      ▼
Celery task (background)
      │
      ├─► GitHub API — fetch PR diff
      ├─► Gemini API — generate review
      └─► GitHub API — post comment
```

## v1 scope

This is a first version, deliberately narrow:

- Single GitHub App, single owner — no multi-user or multi-org support
- One summary comment per PR — no inline line comments
- Python files only — no other languages
- No custom per-repo rules, no dashboard or UI

**Not built yet:** RBAC/multi-tenancy, inline diff comments, multi-language support, a configuration system, a frontend.

## Setup

### Prerequisites

- Python 3.13+
- PostgreSQL
- Redis
- A GitHub account with permission to create a GitHub App
- A Gemini API key ([aistudio.google.com](https://aistudio.google.com/apikey))

### 1. Clone and install

```bash
git clone https://github.com/Audrey-Okumu/DevPulse.git
cd DevPulse
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Create a GitHub App

1. Go to **Settings → Developer settings → GitHub Apps → New GitHub App**
2. Set repository permissions: **Pull requests** → Read & write, **Contents** → Read-only
3. Subscribe to the **Pull request** event
4. Set the webhook URL to `https://<your-domain>/webhooks/github/`
5. Generate a webhook secret and a private key (`.pem` file)
6. Install the app on the repo(s) you want reviewed

### 3. Configure environment variables

Create a `.env` file in the project root:

```dotenv
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_APP_ID=your-app-id
GITHUB_APP_PRIVATE_KEY_PATH=keys/your-private-key.pem
LLM_API_KEY=your-gemini-api-key

DB_NAME=devpulse
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Place your GitHub App's private key at the path referenced above (e.g. `keys/your-private-key.pem`) — this file is gitignored and must never be committed.

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Start the services

You'll need three processes running simultaneously:

```bash
# Terminal 1 — Django
python manage.py runserver

# Terminal 2 — Celery worker (Windows requires --pool=solo)
celery -A devpulse worker --loglevel=info --pool=solo

# Terminal 3 — Redis (if not already running)
docker run -d --name devpulse-redis -p 6379:6379 redis:7
```

### 6. Expose your local server (for local testing)

Use [ngrok](https://ngrok.com/) to tunnel your local Django server so GitHub's webhooks can reach it:

```bash
ngrok http 8000
```

Update your GitHub App's webhook URL and Django's `ALLOWED_HOSTS` with the ngrok URL it gives you.

## Project structure

```
devpulse/
├── devpulse/            # Django project config (settings, urls, celery.py)
└── reviewer/
    ├── models.py          # Installation, ReviewedPR
    ├── views.py           # Webhook endpoint
    ├── github_client.py   # GitHub App auth, diff fetching, comment posting
    ├── llm_client.py      # AI review generation
    └── tasks.py           # Celery task tying it all together
```

## License

Personal project — license TBD.
