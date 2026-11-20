from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from cart.forms import CartAddProductForm

from .models import Category, Product
from .recommendations import (
    add_recently_viewed,
    frequently_bought_with,
    recently_viewed,
    related_products,
)

SORTS = {
    "new": "-created",
    "price_low": "price",
    "price_high": "-price",
    "name": "name",
}


def _filtered(request, queryset):
    sort = request.GET.get("sort", "new")
    queryset = queryset.order_by(SORTS.get(sort, "-created"))
    page = Paginator(queryset, 12).get_page(request.GET.get("page"))
    return page, sort


def product_list(request):
    products = Product.objects.filter(available=True).select_related("category")
    page, sort = _filtered(request, products)
    return render(request, "store/product_list.html", {
        "page": page,
        "sort": sort,
        "recent": recently_viewed(request),
    })


def category(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    products = cat.products.filter(available=True)
    page, sort = _filtered(request, products)
    return render(request, "store/category.html", {"category": cat, "page": page, "sort": sort})


def search(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.none()
    if q:
        products = Product.objects.filter(available=True).filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q)
        )
    page, sort = _filtered(request, products)
    return render(request, "store/search.html", {"q": q, "page": page, "sort": sort})


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    context = {
        "product": product,
        "cart_form": CartAddProductForm(max_qty=product.stock),
        "related": related_products(product),
        "bought_with": frequently_bought_with([product.pk]),
        "recent": recently_viewed(request, exclude=product),
    }
    add_recently_viewed(request, product)
    return render(request, "store/product_detail.html", context)


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /orders/",
        "Disallow: /payments/",
        "Disallow: /accounts/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
