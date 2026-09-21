import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .tasks import review_pr_task

from .models import Installation, ReviewedPR

logger = logging.getLogger(__name__)

TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}


def _verify_signature(request) -> bool:
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        key=settings.GITHUB_WEBHOOK_SECRET.encode(),
        msg=request.body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)

@csrf_exempt
@require_POST
def github_webhook(request):
    if not _verify_signature(request):
        logger.warning("Rejected webhook: bad signature")
        return HttpResponseForbidden("bad signature")

    event = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    logger.info("Received event=%s delivery=%s", event, delivery_id)

    if event != "pull_request":
        return JsonResponse({"status": "ignored", "reason": "not a pull_request event"})

    action = payload.get("action")
    if action not in TRIGGER_ACTIONS:
        return JsonResponse({"status": "ignored", "reason": f"action={action}"})

    pr = payload["pull_request"]
    repo_full_name = payload["repository"]["full_name"]
    pr_number = pr["number"]
    head_sha = pr["head"]["sha"]
    installation_id = payload["installation"]["id"]

    installation, _ = Installation.objects.get_or_create(
        installation_id=installation_id,
        defaults={"account_login": payload["repository"]["owner"]["login"]},
    )

    reviewed_pr, created = ReviewedPR.objects.get_or_create(
        installation=installation,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        head_sha=head_sha,
        defaults={"status": ReviewedPR.STATUS_PENDING},
    )

    if not created:
        logger.info("Skipping duplicate: %s", reviewed_pr)
        return JsonResponse({"status": "skipped", "reason": "already processed"})

    review_pr_task.delay(reviewed_pr.id)
    logger.info("Queued Celery task for: %s", reviewed_pr)

    return JsonResponse({"status": "queued", "pr": f"{repo_full_name}#{pr_number}"})