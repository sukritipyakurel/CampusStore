from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from store.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting payment"
        PAID = "paid", "Paid"
        FAILED = "failed", "Payment failed"
        SHIPPED = "shipped", "Ready / shipped"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="orders", on_delete=models.SET_NULL
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=250, help_text="Hostel / department / delivery address")
    city = models.CharField(max_length=100, default="Kathmandu")
    note = models.TextField(blank=True)

    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Order #{self.id}"

    def get_absolute_url(self):
        return reverse("orders:order_detail", args=[self.id])

    def get_subtotal(self):
        return sum((item.get_cost() for item in self.items.all()), Decimal("0.00"))

    def get_total(self):
        return self.get_subtotal() + self.delivery_charge


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    def get_cost(self):
        return self.price * self.quantity
