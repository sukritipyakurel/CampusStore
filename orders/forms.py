import re

from django import forms

from .models import Order


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "email", "phone", "address", "city", "note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Size preferences, pickup time, etc."}),
            "phone": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "98XXXXXXXX"}),
        }
        labels = {"note": "Note (optional)"}

    def clean_phone(self):
        phone = re.sub(r"[\s-]", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"(\+977)?9\d{9}", phone):
            raise forms.ValidationError("Enter a 10-digit Nepali mobile number starting with 9.")
        return phone
