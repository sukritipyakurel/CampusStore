from django.db import models

from orders.models import Order


class Payment(models.Model):
    """One eSewa payment attempt. A retry after failure creates a new row,
    because eSewa requires a fresh transaction_uuid for every attempt."""

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        COMPLETE = "COMPLETE", "Complete"
        PENDING = "PENDING", "Pending"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"
        NOT_FOUND = "NOT_FOUND", "Not found"
        AMBIGUOUS = "AMBIGUOUS", "Ambiguous"
        FULL_REFUND = "FULL_REFUND", "Full refund"
        PARTIAL_REFUND = "PARTIAL_REFUND", "Partial refund"

    order = models.ForeignKey(Order, related_name="payments", on_delete=models.CASCADE)
    transaction_uuid = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    ref_id = models.CharField(max_length=64, blank=True, help_text="eSewa reference / transaction code")
    raw_response = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.transaction_uuid} ({self.status})"
