from django import forms
from .models import Product,ProductVariant

class ProductForm(forms.models):
    class Meta:
        model=Product
        fields=['name','description','category']
class ProductVariantForm(forms.models):
    class Meta:
        model=ProductVariant
        fields=['product','price','stock','size']