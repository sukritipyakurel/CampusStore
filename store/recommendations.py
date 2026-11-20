"""Simple recommendation logic for the store.

Three strategies:
1. related_products        - same category, excluding the product itself
2. frequently_bought_with  - co-occurrence counts from past *paid* orders
3. recently viewed         - product ids kept in the session (see helpers below)
"""
from django.conf import settings
from django.db.models import Count

from .models import Product

RECENT_KEY = settings.RECENTLY_VIEWED_SESSION_ID
RECENT_MAX = 8


def related_products(product, limit=4):
    return (
        Product.objects.filter(category=product.category, available=True)
        .exclude(pk=product.pk)
        .order_by("?")[:limit]
    )


def frequently_bought_with(product_ids, limit=4):
    """Products that appear in the same paid orders as any of `product_ids`,
    ranked by how many orders they share."""
    from orders.models import OrderItem  # local import avoids circular dependency

    product_ids = list(product_ids)
    if not product_ids:
        return Product.objects.none()

    order_ids = OrderItem.objects.filter(
        product_id__in=product_ids, order__paid=True
    ).values_list("order_id", flat=True)

    ranked = (
        OrderItem.objects.filter(order_id__in=order_ids)
        .exclude(product_id__in=product_ids)
        .values("product_id")
        .annotate(times=Count("order_id", distinct=True))
        .order_by("-times")[:limit]
    )
    ids = [row["product_id"] for row in ranked]
    products = Product.objects.in_bulk(ids)
    return [products[i] for i in ids if i in products and products[i].available]


def add_recently_viewed(request, product):
    ids = request.session.get(RECENT_KEY, [])
    if product.pk in ids:
        ids.remove(product.pk)
    ids.insert(0, product.pk)
    request.session[RECENT_KEY] = ids[:RECENT_MAX]


def recently_viewed(request, exclude=None, limit=4):
    ids = [i for i in request.session.get(RECENT_KEY, []) if i != getattr(exclude, "pk", None)]
    products = Product.objects.in_bulk(ids)
    return [products[i] for i in ids if i in products][:limit]
