from django.contrib import admin

from payments.models import Payment

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ["product"]
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = ["transaction_uuid", "amount", "status", "ref_id", "created"]
    fields = readonly_fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "email", "phone", "status", "paid", "total", "created"]
    list_filter = ["status", "paid", "created"]
    search_fields = ["id", "full_name", "email", "phone"]
    inlines = [OrderItemInline, PaymentInline]
    actions = ["mark_shipped"]

    @admin.display(description="Total (Rs.)")
    def total(self, obj):
        return obj.get_total()

    @admin.action(description="Mark selected paid orders as ready / shipped")
    def mark_shipped(self, request, queryset):
        updated = queryset.filter(paid=True).update(status=Order.Status.SHIPPED)
        self.message_user(request, f"{updated} order(s) marked as shipped.")
