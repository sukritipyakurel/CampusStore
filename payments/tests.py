import base64
import json
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order
from store.models import Category, Product

from . import esewa
from .models import Payment

SECRET = "8gBm/:&EnhH.1/q"


@override_settings(ESEWA_SECRET_KEY=SECRET, ESEWA_PRODUCT_CODE="EPAYTEST", ESEWA_ENV="uat", DELIVERY_CHARGE="0.00")
class EsewaTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Apparel")
        self.product = Product.objects.create(category=cat, name="Campus Tee", price=Decimal("15.00"), stock=5)

    def test_signature_is_base64_hmac_sha256(self):
        # RFC 4231 test case 2 (known HMAC-SHA256 vector), base64-encoded.
        expected = base64.b64encode(bytes.fromhex(
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843")).decode()
        self.assertEqual(esewa.generate_signature("Jefe", "what do ya want for nothing?"), expected)

    def test_canonical_message_order(self):
        msg = esewa.build_message(
            {"product_code": "EPAYTEST", "total_amount": "100.00", "transaction_uuid": "11-201-13"},
            "total_amount,transaction_uuid,product_code")
        self.assertEqual(msg, "total_amount=100.00,transaction_uuid=11-201-13,product_code=EPAYTEST")

    def test_form_fields_are_two_decimal(self):
        f = esewa.build_payment_form(amount=100, transaction_uuid="1-abc", success_url="s", failure_url="f")
        self.assertEqual(f["total_amount"], "100.00")
        self.assertEqual(f["signed_field_names"], "total_amount,transaction_uuid,product_code")

    def _callback(self, payment, status="COMPLETE", tamper=False):
        body = {
            "transaction_code": "000AWEO",
            "status": status,
            "total_amount": f"{payment.amount:.1f}",
            "transaction_uuid": payment.transaction_uuid,
            "product_code": "EPAYTEST",
            "signed_field_names": "transaction_code,status,total_amount,transaction_uuid,product_code,signed_field_names",
        }
        body["signature"] = esewa.generate_signature(SECRET, esewa.build_message(body, body["signed_field_names"]))
        if tamper:
            body["total_amount"] = "1.0"
        return base64.b64encode(json.dumps(body).encode()).decode()

    def _checkout(self):
        self.client.post(reverse("cart:cart_add", args=[self.product.id]), {"quantity": 2})
        resp = self.client.post(reverse("orders:checkout"), {
            "full_name": "Sita Sharma", "email": "sita@example.com", "phone": "9812345678",
            "address": "Hostel B", "city": "Kathmandu",
        })
        order = Order.objects.get()
        self.assertRedirects(resp, reverse("payments:pay", args=[order.id]), fetch_redirect_response=False)
        resp = self.client.get(reverse("payments:pay", args=[order.id]))
        self.assertContains(resp, "rc-epay.esewa.com.np")
        return order, Payment.objects.get(order=order)

    @mock.patch("payments.esewa.requests.get")
    def test_full_flow_marks_order_paid_and_reduces_stock(self, mock_get):
        order, payment = self._checkout()
        self.assertEqual(payment.amount, Decimal("30.00"))
        mock_get.return_value.json.return_value = {
            "product_code": "EPAYTEST", "transaction_uuid": payment.transaction_uuid,
            "total_amount": 30.0, "status": "COMPLETE", "ref_id": "0001TS9",
        }
        mock_get.return_value.raise_for_status.return_value = None
        resp = self.client.get(reverse("payments:success"), {"data": self._callback(payment)})
        self.assertContains(resp, "0001TS9")
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(self.product.stock, 3)
        # Replaying the same callback must not reduce stock again.
        self.client.get(reverse("payments:success"), {"data": self._callback(payment)})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(mock_get.call_count, 1)

    @mock.patch("payments.esewa.requests.get")
    def test_tampered_callback_rejected(self, mock_get):
        order, payment = self._checkout()
        resp = self.client.get(reverse("payments:success"), {"data": self._callback(payment, tamper=True)})
        self.assertEqual(resp.status_code, 400)
        mock_get.assert_not_called()
        order.refresh_from_db()
        self.assertFalse(order.paid)

    @mock.patch("payments.esewa.requests.get")
    def test_status_api_disagreement_does_not_fulfil(self, mock_get):
        order, payment = self._checkout()
        mock_get.return_value.json.return_value = {"status": "PENDING", "total_amount": 30.0}
        mock_get.return_value.raise_for_status.return_value = None
        self.client.get(reverse("payments:success"), {"data": self._callback(payment)})
        order.refresh_from_db()
        self.assertFalse(order.paid)


class StorePagesTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Mugs")
        self.p = Product.objects.create(category=cat, name="Ceramic Mug", price=Decimal("8.00"), stock=3)

    def test_pages_render(self):
        for url in ["/", "/search/?q=mug", self.p.get_absolute_url(), "/category/mugs/", "/cart/", "/sitemap.xml", "/robots.txt",
                    "/accounts/login/", "/accounts/register/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_ajax_add(self):
        r = self.client.post(f"/cart/add/{self.p.id}/", {"quantity": 10}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.json()["quantity"], 3)  # capped at stock
