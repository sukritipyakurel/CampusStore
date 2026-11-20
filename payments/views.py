import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from cart.cart import Cart
from orders.models import Order
from orders.views import user_can_view
from store.models import Product

from . import esewa
from .models import Payment

log = logging.getLogger(__name__)


def pay(request, order_id):
    """Create a payment attempt and render the auto-submitting eSewa form."""
    order = get_object_or_404(Order, id=order_id)
    if not user_can_view(request, order):
        raise Http404
    if order.paid:
        return redirect(order.get_absolute_url())

    subtotal = order.get_subtotal()
    payment = Payment.objects.create(
        order=order,
        transaction_uuid=esewa.new_transaction_uuid(order.id),
        amount=order.get_total(),
    )
    fields = esewa.build_payment_form(
        amount=subtotal,
        delivery_charge=order.delivery_charge,
        transaction_uuid=payment.transaction_uuid,
        success_url=request.build_absolute_uri(reverse("payments:success")),
        failure_url=request.build_absolute_uri(reverse("payments:failure", args=[payment.transaction_uuid])),
    )
    return render(request, "payments/pay.html", {
        "order": order,
        "fields": fields,
        "action": esewa.urls()["form"],
    })


def _fulfil(payment, status_data):
    """Mark the order paid and reduce stock. Idempotent and race-safe."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == Payment.Status.COMPLETE:
            return payment  # already processed (e.g. user refreshed the page)
        payment.status = Payment.Status.COMPLETE
        payment.ref_id = status_data.get("ref_id") or ""
        payment.raw_response = status_data
        payment.save()

        order = payment.order
        order.paid = True
        order.status = Order.Status.PAID
        order.save(update_fields=["paid", "status", "updated"])
        for item in order.items.all():
            Product.objects.filter(pk=item.product_id).update(stock=F("stock") - item.quantity)
        Product.objects.filter(stock__lt=0).update(stock=0)
    return payment


def success(request):
    try:
        data = esewa.decode_callback(request.GET.get("data", ""))
    except esewa.EsewaError as exc:
        log.warning("Rejected eSewa callback: %s", exc)
        return render(request, "payments/failure.html", {"reason": "We couldn't verify the response from eSewa."}, status=400)

    payment = get_object_or_404(Payment.objects.select_related("order"), transaction_uuid=data.get("transaction_uuid"))
    order = payment.order

    if payment.status == Payment.Status.COMPLETE:
        return render(request, "payments/success.html", {"order": order, "payment": payment})

    # Never trust the redirect alone: ask eSewa directly.
    try:
        status_data = esewa.check_status(payment.transaction_uuid, payment.amount)
    except esewa.EsewaError as exc:
        log.error("Status check error for %s: %s", payment.transaction_uuid, exc)
        payment.status = Payment.Status.PENDING
        payment.save(update_fields=["status", "updated"])
        return render(request, "payments/failure.html", {
            "order": order,
            "reason": "eSewa didn't confirm the payment yet. If money left your account, contact us with your order number.",
        })

    status = status_data.get("status")
    amount_ok = esewa.parse_amount(status_data.get("total_amount", 0)) == payment.amount
    if status == "COMPLETE" and amount_ok:
        payment = _fulfil(payment, status_data)
        Cart(request).clear()
        return render(request, "payments/success.html", {"order": order, "payment": payment})

    payment.status = status if status in Payment.Status.values else Payment.Status.FAILED
    if status == "COMPLETE" and not amount_ok:
        payment.status = Payment.Status.AMBIGUOUS
    payment.raw_response = status_data
    payment.save(update_fields=["status", "raw_response", "updated"])
    return render(request, "payments/failure.html", {
        "order": order,
        "reason": f"eSewa reported the payment as {status or 'unknown'}.",
    })


def failure(request, transaction_uuid):
    payment = get_object_or_404(Payment.objects.select_related("order"), transaction_uuid=transaction_uuid)
    if payment.status != Payment.Status.COMPLETE:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated"])
        if not payment.order.paid:
            payment.order.status = Order.Status.FAILED
            payment.order.save(update_fields=["status", "updated"])
    messages.error(request, "The payment was cancelled or failed. Your cart is still saved.")
    return render(request, "payments/failure.html", {"order": payment.order, "reason": "The payment was cancelled or didn't go through."})
