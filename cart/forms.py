from django import forms


class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

    def __init__(self, *args, max_qty=None, **kwargs):
        super().__init__(*args, **kwargs)
        if max_qty:
            self.fields["quantity"].max_value = max_qty
            self.fields["quantity"].widget.attrs["max"] = max_qty
