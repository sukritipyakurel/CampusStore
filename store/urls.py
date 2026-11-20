from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("search/", views.search, name="search"),
    path("category/<slug:slug>/", views.category, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
]
