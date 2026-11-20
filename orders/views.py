from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from cart.cart import Cart

from .forms import OrderCreateForm
from .models import Order, OrderItem

SESSION_ORDERS = "guest_order_ids"


def _remember_order(request, order):
    ids = request.session.get(SESSION_ORDERS, [])
    ids.append(order.id)
    request.session[SESSION_ORDERS] = ids[-20:]


def user_can_view(request, order):
    if request.user.is_authenticated and (order.user_id == request.user.id or request.user.is_staff):
        return True
    return order.id in request.session.get(SESSION_ORDERS, [])


def checkout(request):
    cart = Cart(request)
    items = list(cart)
    if not items:
        messages.info(request, "Your cart is empty. Add something before checking out.")
        return redirect("store:product_list")

    delivery = Decimal(settings.DELIVERY_CHARGE)

    if request.method == "POST":
        form = OrderCreateForm(request.POST)
        problems = [i["product"].name for i in items if i["quantity"] > i["product"].stock or not i["product"].available]
        if problems:
            messages.error(request, "Not enough stock for: " + ", ".join(problems) + ". Update your cart and try again.")
            return redirect("cart:cart_detail")
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                order.delivery_charge = delivery
                order.save()
                OrderItem.objects.bulk_create([
                    OrderItem(order=order, product=i["product"], price=i["product"].price, quantity=i["quantity"])
                    for i in items
                ])
            _remember_order(request, order)
            return redirect("payments:pay", order_id=order.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            u = request.user
            initial = {"full_name": u.get_full_name(), "email": u.email}
        form = OrderCreateForm(initial=initial)

    subtotal = cart.get_total_price()
    return render(request, "orders/checkout.html", {
        "form": form,
        "items": items,
        "subtotal": subtotal,
        "delivery": delivery,
        "total": subtotal + delivery,
    })


def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items__product", "payments"), id=order_id)
    if not user_can_view(request, order):
        raise Http404
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_history(request):
    orders = request.user.orders.prefetch_related("items__product")
    return render(request, "orders/order_history.html", {"orders": orders})
