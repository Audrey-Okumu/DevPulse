import logging

from celery import shared_task

from .github_client import get_installation_token, get_pr_files, post_comment
from .llm_client import get_ai_review
from .models import ReviewedPR

logger = logging.getLogger(__name__)


@shared_task
def review_pr_task(reviewed_pr_id):
    reviewed_pr = ReviewedPR.objects.get(id=reviewed_pr_id)
    reviewed_pr.status = ReviewedPR.STATUS_PROCESSING
    reviewed_pr.save()

    try:
        installation_id = reviewed_pr.installation.installation_id
        repo_full_name = reviewed_pr.repo_full_name
        pr_number = reviewed_pr.pr_number

        installation_token = get_installation_token(installation_id)
        files = get_pr_files(installation_token, repo_full_name, pr_number)

        review_sections = []
        for f in files:
            if not f["filename"].endswith(".py"):
                continue
            if "patch" not in f:
                continue

            review = get_ai_review(f["filename"], f["patch"])
            review_sections.append(f"### `{f['filename']}`\n\n{review}")

        if review_sections:
            comment_body = "## 🤖 AI Code Review\n\n" + "\n\n---\n\n".join(review_sections)
            result = post_comment(installation_token, repo_full_name, pr_number, comment_body)
            reviewed_pr.comment_id = result["id"]
            logger.info("Posted review comment: %s", result["html_url"])
        else:
            logger.info("No Python files to review for %s", reviewed_pr)

        reviewed_pr.status = ReviewedPR.STATUS_DONE
        reviewed_pr.save()

    except Exception:
        reviewed_pr.status = ReviewedPR.STATUS_FAILED
        reviewed_pr.save()
        logger.exception("Failed to review %s", reviewed_pr)
        raise