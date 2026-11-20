from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("pay/<int:order_id>/", views.pay, name="pay"),
    path("esewa/success/", views.success, name="success"),
    path("esewa/failure/<str:transaction_uuid>/", views.failure, name="failure"),
]
