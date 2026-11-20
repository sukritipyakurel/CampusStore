from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from store.models import Product
from store.recommendations import frequently_bought_with

from .cart import Cart
from .forms import CartAddProductForm


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", "")


def _cart_payload(cart, product=None):
    data = {"cart_count": len(cart), "cart_total": f"{cart.get_total_price():.2f}"}
    if product is not None:
        item = cart.cart.get(str(product.id))
        if item:
            data["quantity"] = item["quantity"]
            data["line_total"] = f"{float(item['price']) * item['quantity']:.2f}"
        else:
            data["quantity"] = 0
    return data


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    form = CartAddProductForm(request.POST)
    if not product.in_stock:
        msg = f"{product.name} is out of stock."
        if _wants_json(request):
            return JsonResponse({"error": msg}, status=400)
        messages.error(request, msg)
        return redirect(product.get_absolute_url())
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product, quantity=cd["quantity"], override_quantity=cd["override"])
    if _wants_json(request):
        return JsonResponse(_cart_payload(cart, product))
    if not form.cleaned_data.get("override"):
        messages.success(request, f"Added {product.name} to your cart.")
    return redirect("cart:cart_detail")


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    if _wants_json(request):
        return JsonResponse(_cart_payload(cart, product))
    return redirect("cart:cart_detail")


def cart_detail(request):
    cart = Cart(request)
    items = list(cart)
    for item in items:
        item["update_form"] = CartAddProductForm(
            initial={"quantity": item["quantity"], "override": True},
            max_qty=item["product"].stock,
        )
    return render(request, "cart/cart_detail.html", {
        "items": items,
        "suggestions": frequently_bought_with(cart.product_ids()),
    })
