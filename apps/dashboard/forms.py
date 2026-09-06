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

    class Meta:
        model = Listing
        fields = ['title', 'category', 'price', 'condition', 'location', 'description', 'status']
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
