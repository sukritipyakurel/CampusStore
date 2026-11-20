"""eSewa ePay v2 helpers.

Flow:
 1. build_payment_form()   -> signed fields for the auto-submitting POST form
 2. decode_callback()      -> decode + verify the ?data= blob eSewa redirects back with
 3. check_status()         -> server-to-server status check (the source of truth)
"""
import base64
import binascii
import hashlib
import hmac
import json
import uuid
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings

REQUEST_SIGNED_FIELDS = "total_amount,transaction_uuid,product_code"


class EsewaError(Exception):
    pass


def urls():
    return settings.ESEWA_URLS[settings.ESEWA_ENV]


def money(value):
    """Format to exactly 2 decimals: 100 -> '100.00'."""
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def generate_signature(secret_key, message):
    h = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(h.digest()).decode()


def build_message(fields, signed_field_names):
    """Canonical string: 'a=1,b=2,c=3' in the exact order given, no spaces."""
    return ",".join(f"{name}={fields[name]}" for name in signed_field_names.split(","))


def new_transaction_uuid(order_id):
    # eSewa allows alphanumerics and hyphens only.
    return f"{order_id}-{uuid.uuid4().hex[:12]}"


def build_payment_form(*, amount, transaction_uuid, success_url, failure_url,
                       tax_amount=0, service_charge=0, delivery_charge=0):
    total = Decimal(amount) + Decimal(tax_amount) + Decimal(service_charge) + Decimal(delivery_charge)
    fields = {
        "amount": money(amount),
        "tax_amount": money(tax_amount),
        "total_amount": money(total),
        "transaction_uuid": transaction_uuid,
        "product_code": settings.ESEWA_PRODUCT_CODE,
        "product_service_charge": money(service_charge),
        "product_delivery_charge": money(delivery_charge),
        "success_url": success_url,
        "failure_url": failure_url,
        "signed_field_names": REQUEST_SIGNED_FIELDS,
    }
    fields["signature"] = generate_signature(
        settings.ESEWA_SECRET_KEY, build_message(fields, REQUEST_SIGNED_FIELDS)
    )
    return fields


def decode_callback(data_param):
    """Decode the base64 JSON eSewa sends to success_url and verify its signature.

    A valid signature proves the message came from eSewa, but NOT that it is
    fresh: always follow up with check_status() before fulfilling the order.
    """
    if not data_param:
        raise EsewaError("Missing data parameter.")
    try:
        padded = data_param + "=" * (-len(data_param) % 4)
        payload = json.loads(base64.b64decode(padded).decode())
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise EsewaError("Could not decode eSewa response.") from exc

    signed_names = payload.get("signed_field_names", "")
    received_sig = payload.get("signature", "")
    try:
        message = build_message(payload, signed_names)
    except KeyError as exc:
        raise EsewaError(f"Signed field missing from response: {exc}") from exc

    expected = generate_signature(settings.ESEWA_SECRET_KEY, message)
    if not hmac.compare_digest(expected, received_sig):
        raise EsewaError("Signature mismatch — response was not signed by eSewa.")
    return payload


def check_status(transaction_uuid, total_amount, timeout=10):
    """Ask eSewa directly what happened to this transaction.

    Returns the parsed JSON, e.g.
    {"product_code": "EPAYTEST", "transaction_uuid": "...", "total_amount": 100.0,
     "status": "COMPLETE", "ref_id": "0001TS9"}
    """
    params = {
        "product_code": settings.ESEWA_PRODUCT_CODE,
        "total_amount": money(total_amount),
        "transaction_uuid": transaction_uuid,
    }
    try:
        resp = requests.get(urls()["status"], params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise EsewaError(f"Status check failed: {exc}") from exc


def parse_amount(value):
    """eSewa may return amounts like '1,000.0' or 100.0 — normalise to Decimal."""
    return Decimal(str(value).replace(",", "")).quantize(Decimal("0.01"))
