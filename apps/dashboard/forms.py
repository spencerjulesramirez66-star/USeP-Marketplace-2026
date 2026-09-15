import re
from decimal import Decimal, InvalidOperation

from django import forms

from .models import Category, Listing, Message

PRODUCT_CONDITIONS = [
    'Like new',
    'Barely used',
    'Good condition',
    'For parts',
]
SERVICE_CONDITIONS = [
    'Available by appointment',
    'On-site service',
]
CONDITION_CHOICES = [(value, value) for value in PRODUCT_CONDITIONS + SERVICE_CONDITIONS]


class ListingForm(forms.ModelForm):
    title = forms.CharField(
        max_length=180,
        label='Item name',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Engineering textbook (3rd Edition)',
        }),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label='Category',
        empty_label='Choose a category',
        help_text="Selecting \u201cServices\u201d hides stock, since services aren't sold in units.",
    )
    price = forms.CharField(
        max_length=20,
        label='Price (\u20b1)',
        help_text='Numbers only, e.g. 250 or 250.50.',
        widget=forms.NumberInput(attrs={
            'inputmode': 'decimal',
            'pattern': r'^[0-9]+(?:\.[0-9]{1,2})?$',
            'placeholder': '0.00',
        }),
    )
    condition = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        label='Condition or availability',
    )
    location = forms.CharField(
        max_length=180,
        required=False,
        label='Meetup location',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. USeP campus library',
        }),
    )
    description = forms.CharField(
        label='Description',
        help_text='Mention what buyers should know: condition details, inclusions, or how the service works.',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Tell buyers what they should know...',
        }),
    )
    stock_quantity = forms.IntegerField(
        min_value=0,
        required=False,
        label='Stock quantity',
        help_text='For service listings, stock stays at 0.',
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
        labels = {
            'status': 'Listing status',
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
        self.fields['stock_quantity'].initial = (
            self.instance.stock_quantity if self.instance and self.instance.pk else 0
        )

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
        if self._is_service_category(category):
            return 0
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError('Stock cannot be negative.')
        return int(value)

    def clean(self):
        cleaned_data = super().clean()
        if self._is_service_category(cleaned_data.get('category')):
            cleaned_data['stock_quantity'] = 0
        return cleaned_data

    @staticmethod
    def _is_service_category(category):
        return bool(category) and getattr(category, 'slug', '').lower() == 'services'


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