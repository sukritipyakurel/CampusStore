"""Session-based shopping cart.

The session stores {product_id: {"quantity": int, "price": "12.00"}}.
Prices are stored as strings because sessions are JSON-serialised.
"""
from decimal import Decimal

from django.conf import settings

from store.models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if cart is None:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        pid = str(product.id)
        if pid not in self.cart:
            self.cart[pid] = {"quantity": 0, "price": str(product.price)}
        if override_quantity:
            self.cart[pid]["quantity"] = quantity
        else:
            self.cart[pid]["quantity"] += quantity
        # never allow more than what's in stock
        self.cart[pid]["quantity"] = max(1, min(self.cart[pid]["quantity"], product.stock))
        self.save()

    def remove(self, product):
        pid = str(product.id)
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def save(self):
        self.session.modified = True

    def clear(self):
        self.session.pop(settings.CART_SESSION_ID, None)
        self.session.modified = True

    def __iter__(self):
        products = Product.objects.filter(id__in=self.cart.keys())
        cart = {pid: dict(item) for pid, item in self.cart.items()}
        for product in products:
            cart[str(product.id)]["product"] = product
        for item in cart.values():
            if "product" not in item:
                continue  # product was deleted since it was added
            item["price"] = Decimal(item["price"])
            item["total_price"] = item["price"] * item["quantity"]
            yield item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def product_ids(self):
        return [int(pid) for pid in self.cart.keys()]

    def get_total_price(self):
        return sum(Decimal(item["price"]) * item["quantity"] for item in self.cart.values())
