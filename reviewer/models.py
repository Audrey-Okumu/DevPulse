from django.db import models


class Installation(models.Model):
    """One row per GitHub App installation."""
    installation_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_login} ({self.installation_id})"


class ReviewedPR(models.Model):
    """One row per PR review attempt. head_sha is the dedup key —
    a PR can be reviewed again after a new push (new head_sha)."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    installation = models.ForeignKey(Installation, on_delete=models.CASCADE)
    repo_full_name = models.CharField(max_length=255)  # e.g. "owner/repo"
    pr_number = models.IntegerField()
    head_sha = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    comment_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("repo_full_name", "pr_number", "head_sha")

    def __str__(self):
        return f"{self.repo_full_name}#{self.pr_number}@{self.head_sha[:7]} [{self.status}]"