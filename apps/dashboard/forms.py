import re
from decimal import Decimal, InvalidOperation

from django import forms

from .models import Listing, Message


class ListingForm(forms.ModelForm):
    price = forms.CharField(
        max_length=20,
        widget=forms.NumberInput(attrs={
            'inputmode': 'decimal',
            'pattern': r'^[0-9]+(?:\.[0-9]{1,2})?$',
        }),
    )
    stock_quantity = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'min': 0,
            'step': 1,
            'inputmode': 'numeric',
            'pattern': r'^[0-9]+$',
        }),
    )

    class Meta:
        model = Listing
        fields = ['title', 'category', 'price', 'condition', 'location', 'description', 'status', 'stock_quantity']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'status': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].required = False
        self.fields['status'].initial = Listing.Status.ACTIVE
        self.fields['status'].choices = [
            (Listing.Status.DRAFT, 'Draft'),
            (Listing.Status.ACTIVE, 'Active'),
            (Listing.Status.SOLD, 'Sold'),
            (Listing.Status.ARCHIVED, 'Archived'),
        ]
        if self.instance and self.instance.pk and self.instance.is_service_listing:
            self.fields['stock_quantity'].required = False
            self.fields['stock_quantity'].widget.attrs['readonly'] = 'readonly'
        self.fields['stock_quantity'].initial = self.instance.stock_quantity if self.instance and self.instance.pk else 0

    def clean_price(self):
        raw_price = str(self.cleaned_data.get('price', '')).strip().replace(',', '')
        if not re.fullmatch(r'\d+(?:\.\d{1,2})?', raw_price):
            raise forms.ValidationError('Enter a valid non-negative price, such as 1000 or 1000.50.')
        try:
            price = Decimal(raw_price)
        except InvalidOperation as error:
            raise forms.ValidationError('Enter a valid price.') from error
        if price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price

    def clean_stock_quantity(self):
        value = self.cleaned_data.get('stock_quantity')
        category = self.cleaned_data.get('category')
        if category and getattr(category, 'slug', '').lower() == 'services':
            return 0
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError('Stock cannot be negative.')
        return int(value)

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        if category and getattr(category, 'slug', '').lower() == 'services':
            cleaned_data['stock_quantity'] = 0
        return cleaned_data


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ask the seller about this listing...',
            }),
        }
