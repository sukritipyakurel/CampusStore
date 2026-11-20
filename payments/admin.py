from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_uuid", "order", "amount", "status", "ref_id", "created"]
    list_filter = ["status", "created"]
    search_fields = ["transaction_uuid", "ref_id", "order__id"]
    readonly_fields = ["order", "transaction_uuid", "amount", "status", "ref_id", "raw_response", "created", "updated"]
