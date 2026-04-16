from decimal import Decimal
from django.db import models
from PIL import Image
import os
from django.core.validators import MinValueValidator,MaxValueValidator
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError
from django.utils.text import slugify
from django.db import models
from django.contrib.auth import get_user_model
from django.db import models,transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.db.models import F,CheckConstraint,Q
from django.utils.crypto import get_random_string




# Create your models here.
class CustomUser(AbstractUser):
    email=models.EmailField(unique=True)
    phone=models.CharField(max_length=15,blank=True,null=True)
    address=models.TextField(blank=True,null=True)
    def __str__(self):
        return self.username
class Userprofile(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='profile')
    image=models.ImageField(upload_to='product_image/')
    def __str__(self):
        return self.user.username

    
class Category(models.Model):
    name=models.CharField(max_length=100,unique=False)
    description=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    is_active=models.BooleanField(default=True)

    class Meta:
        ordering=['-created_at']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name=models.CharField(max_length=200)
    description=models.TextField()
    category=models.ForeignKey(Category,on_delete=models.CASCADE,null=True,blank=True,related_name='products')
    created_at=models.DateTimeField(auto_now_add=True)
    slug=models.SlugField(max_length=225,unique=True,null=True,blank=True)
    is_active=models.BooleanField(default=True)
    is_delete=models.BooleanField(default=False)
    _has_offer = None

    class Meta:
        ordering=['-created_at']
    
    def get_first_image(self):
        first_image = self.images.first()
        if first_image and first_image.image:
            return first_image.image.url
        return None

    def get_min_price(self):
        min_variant = self.variants.order_by("price").first()
        return min_variant.price if min_variant else None
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def get_active_product_offer(self):
        now = timezone.now()
        return self.product_offers.filter(
            active=True,
            valid_from__lte=now,
            valid_until__gte=now,
        ).order_by('-discount_percentage').first()

    def get_active_category_offer(self):
        now = timezone.now()
        if not self.category:
            return None
        return self.category.category_offers.filter(
            active=True,
            valid_from__lte=now,
            valid_until__gte=now,
        ).order_by('-discount_percentage').first()

    def get_best_active_offer(self):
          
        prod_offer = self.get_active_product_offer()
        cat_offer  = self.get_active_category_offer()

        if prod_offer and cat_offer:
            return prod_offer if prod_offer.discount_percentage > cat_offer.discount_percentage else cat_offer
        return prod_offer or cat_offer

    def get_best_offer_percentage(self):
        offer = self.get_best_active_offer()
        return offer.discount_percentage if offer else Decimal('0.00')

    def has_active_offer(self):
        return self.get_best_offer_percentage() > Decimal('0.00')

    def get_discounted_price(self, variant=None):
        base_price = variant.price if variant else self.get_min_price()
        if not base_price or base_price <= 0:
            return Decimal('0.00')

        discount_perc = self.get_best_offer_percentage()
        if discount_perc == 0:
            return base_price

        factor = Decimal('1') - (discount_perc / Decimal('100'))
        return (base_price * factor).quantize(Decimal('0.01'))

    # Remove or deprecate this — it's misleading
    def get_savings_percentage(self):
        # Option A: keep for backward compat, but fix it
        return self.get_best_offer_percentage()

        # Option B: delete it and update all usages to get_best_offer_percentage()
    
    @property
    def has_offer(self):
        return self._has_offer if self._has_offer is not None else (self.get_best_offer_percentage() > Decimal('0.00'))

    @has_offer.setter
    def has_offer(self, value):
        self._has_offer = value

    def __str__(self):
        return self.name
    
class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='product_image/')
    order=models.PositiveIntegerField(default=0)
    alt_text=models.CharField(max_length=200,blank=True,help_text='Alternative text for the image')

    class Meta:
        ordering=['order']
        constraints=[
            models.UniqueConstraint(fields=['product','order'],name='unique_product_image_order')
        ]
    
    def __str__(self):
        return f'image from {self.id}'
class ProductVariant(models.Model):
    SIZE_CHOICES=(
        ('500g','500g'),
        ('750g','750g'),     
        ('1kg','1kg'),
        ('2kg','2kg')
    )
    product=models.ForeignKey(Product, on_delete=models.CASCADE,related_name='variants')
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.PositiveIntegerField(default=0,validators=[MinValueValidator(0)])
    size=models.CharField(max_length=10,choices=SIZE_CHOICES,default='500g')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True, null=True , blank=True)
    is_active=models.BooleanField(default=True)

    

    def __str__(self):
        return f'variant {self.id} ({self.size})'
    
class ProductReview(models.Model):
    product=models.ForeignKey('Product',on_delete=models.CASCADE,related_name='reviews')
    user=models.CharField(max_length=100)
    rating=models.PositiveIntegerField(validators=[MinValueValidator(1) , MaxValueValidator(5)])
    comment=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'Review for {self.product.name},by {self.user}'
class CartItem(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='cart_items')
    variant=models.ForeignKey(ProductVariant,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)
    create_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    unit_price_at_add = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # original price
    discounted_price_at_add = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # with offer
    offer_percentage_at_add = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # % discount applied


    class Meta:
        unique_together=('user','variant')
        verbose_name='Cart Item'
        verbose_name_plural='Cart Item'

    @property
    def total_price(self):
 
        price = self.discounted_price_at_add or self.unit_price_at_add
        return self.quantity * (price or Decimal('0.00'))
    @total_price.setter
    def total_price(self, value):
        # Optional: store in a new field if you want persistence
        self._custom_total = value  # temporary attribute

    @property
    def has_offer(self):
        """Returns True if there's any active offer (product or category)"""
        return self.get_best_offer_percentage() > Decimal('0.00')
    @property
    def savings(self):
        """How much the customer saved compared to original price"""
        if self.discounted_price_at_add > 0:
            return self.quantity * (self.unit_price_at_add - self.discounted_price_at_add)
        return Decimal('0.00')

    @property
    def display_price(self):
        """For template: show discounted if exists, else original"""
        return self.discounted_price_at_add if self.discounted_price_at_add > 0 else self.unit_price_at_add
    def __str__(self):
        return f'{self.user.username} - {self.variant} * {self.quantity})' 

    
      
class WishlistItem(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    create_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('user','product')
        ordering=['-create_at']
    
    def __str__(self):
        return f'{self.user.username}"s wishlist: {self.product.name}'
    

class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure only one default
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name}, {self.city}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('return_requested', 'Return Requested'),   
        ('returned', 'Returned'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partial_refunded', 'Partially Refunded'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12,decimal_places=2,default=0.00,help_text="Amount before discount, tax, shipping")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=30, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    cancel_reason = models.TextField(blank=True, null=True)  # Optional for cancel
    return_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updates_at=models.DateTimeField(auto_now=True)
    order_id = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    return_reason = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)
    return_approved_at = models.DateTimeField(null=True, blank=True)
    return_rejected_at = models.DateTimeField(null=True, blank=True)
    return_rejection_reason = models.TextField(blank=True, null=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True,related_name='orders')
    coupon_code = models.CharField(max_length=20, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    wallet_amount_used = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_paid_online = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Amount refunded to wallet")
    refund_status = models.CharField(max_length=20, default='none', choices=[
        ('none', 'No Refund'),
        ('pending', 'Refund Pending'),
        ('completed', 'Refund Completed'),
        ('failed', 'Refund Failed'),
    ])
    # 
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    cancellation_status = models.CharField(
        max_length=20,
        default='none',
        choices=[
            ('none', 'No Request'),
            ('requested', 'Cancellation Requested'),
            ('approved', 'Cancellation Approved'),
            ('rejected', 'Cancellation Rejected'),
        ]
    )
    cancellation_rejected_reason = models.TextField(blank=True, null=True)
    

    def __str__(self):
        return f"Order #{self.id} - {self.user}"
    def save(self, *args, **kwargs):
        # 1. Existing Order ID logic
        if not self.order_id:
            pass

        # 2. FIX: Auto-set delivered_at when status becomes 'delivered'
        if self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        
        # 3. Reset if moved back from delivered (Optional but good for testing)
        elif self.status != 'delivered':
            self.delivered_at = None

        super().save(*args, **kwargs)
    @property
    def can_request_return(self):
        if self.status != 'delivered':
            return False
            
        if not self.delivered_at:
            return False
            
        # Already acted on return (requested / rejected / completed)
        if self.return_requested_at or self.return_rejected_at or self.status == 'returned':
            return False
            
        # The real deadline: exactly 7 full days after delivery
        deadline = self.delivered_at + timedelta(days=7)
        
        return timezone.now() <= deadline
    
    @property
    def grand_total(self):
        subtotal = self.total_amount  # before discount
        return max(Decimal('0'), subtotal - self.coupon_discount)
    
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of order
    total = models.DecimalField(max_digits=10, decimal_places=2)
    cancel_reason = models.TextField(blank=True, null=True)  # Per-item cancel reason
    is_returned = models.BooleanField(default=False)
    return_requested = models.BooleanField(default=False)
    return_requested = models.BooleanField(default=False)
    return_requested_at = models.DateTimeField(null=True, blank=True)
    return_reason = models.TextField(blank=True, null=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True, null=True)
    cancellation_requested = models.BooleanField(default=False)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    cancellation_status = models.CharField(
        max_length=20,
        default='none',
        choices=[
            ('none', 'No Request'),
            ('requested', 'Requested'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]
    )
    cancellation_rejected_reason = models.TextField(blank=True, null=True)

    def can_cancel(self):
        if self.is_cancelled:
            return False
        if self.order.status not in ['pending', 'confirmed']:
            return False
        return True

    def can_request_return(self):
        if self.is_cancelled:
            return False
        if self.order.status != 'delivered':
            return False
        if self.return_requested:
            return False
        if not self.order.delivered_at:
            return False
        deadline = self.order.delivered_at + timedelta(days=7)
        return timezone.now() <= deadline
    
    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.PositiveIntegerField(default=0)  # 0-100
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=0)  # 0 = unlimited
    used_count = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    is_one_time_per_user = models.BooleanField(default=True)  # most common

    class Meta:
        ordering = ['-valid_from']

    def __str__(self):
        return self.code

    def clean(self):
        if self.discount_percentage > 0 and self.discount_amount > 0:
            raise ValidationError("Use either percentage OR fixed amount, not both!")
        if self.discount_percentage > 100:
            raise ValidationError("Discount percentage cannot exceed 100%")

    def is_valid_for_user(self, user):
        if not self.active:
            return False, "Coupon is inactive"
            
        if timezone.now() < self.valid_from:
            return False, "Coupon not yet active"
            
        if self.valid_until and timezone.now() > self.valid_until:
            return False, "Coupon expired"
            
        if self.used_count >= self.usage_limit > 0:
            return False, "Coupon usage limit reached"

        if self.is_one_time_per_user and self.orders.filter(user=user).exists():
            return False, "You have already used this coupon"

        return True, ""
    

    def calculate_discount(self, subtotal):
        discount = Decimal('0.00')
        
        if self.discount_percentage > 0:
            rate = Decimal(str(self.discount_percentage)) / Decimal('100')
            discount = subtotal * rate
            
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        
        elif self.discount_amount > 0:
            discount = self.discount_amount
        
        return discount.quantize(Decimal('0.01'))
    @property
    def is_valid_now(self):
        now = timezone.now()
        if not self.active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True
    

class Wallet(models.Model):
    user = models.OneToOneField(
        CustomUser,  # ← use string if app_label is needed
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=12,          # ← increased limit
        decimal_places=2,
        default=0,
        # Optional but nice in India / many markets
        # validators=[MinValueValidator(0)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(balance__gte=0),
                name='wallet_balance_non_negative'
            )
        ]

    def __str__(self):
        return f"Wallet {self.user.username} — ₹{self.balance:,.2f}"

    @transaction.atomic
    def credit(self, amount: Decimal | int | float, description: str, order=None):
        amount = Decimal(amount)
        if amount <= -1:
            raise ValueError("Credit amount must be positive")

        # Lock row + atomic update
        wallet = Wallet.objects.select_for_update().get(pk=self.pk)

        wallet.balance = F('balance') + amount
        wallet.updated_at = timezone.now()
        wallet.save(update_fields=['balance', 'updated_at'])

        # Refresh object
        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,              # positive
            transaction_type='credit',
            description=description,
            order=order,
        )

        return wallet.balance

    @transaction.atomic
    def debit(self, amount: Decimal | int | float, description: str, order=None):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        wallet = Wallet.objects.select_for_update().get(pk=self.pk)

        if wallet.balance < amount:
            raise ValueError(f"Insufficient balance. Available: {wallet.balance}, Requested: {amount}")

        wallet.balance = F('balance') - amount
        wallet.updated_at = timezone.now()
        wallet.save(update_fields=['balance', 'updated_at'])

        wallet.refresh_from_db()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=-amount,             # negative = debit
            transaction_type='debit',
            description=description,
            order=order,
        )

        return wallet.balance

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit',  'Debit'),
    ]

    wallet         = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount         = models.DecimalField(max_digits=12, decimal_places=2)   # + = credit, - = debit
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description    = models.CharField(max_length=200, blank=True)           # ← very important field
    order          = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
        ]

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f"{sign}{self.amount:,.2f} | {self.transaction_type} | {self.description[:40]}…"



class BaseOffer(models.Model):
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount in percent (0–100)"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def is_active_now(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True
    
    def __str__(self):
        return f"{self.discount_percentage}% - {self.__class__.__name__}"

class ProductOffer(BaseOffer):
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='product_offers'
    )
    
    class Meta:
        verbose_name = "Product Offer"
        verbose_name_plural = "Product Offers"
        unique_together = ['product']   # one active offer per product (or remove if you allow stacking)

   

class CategoryOffer(BaseOffer):
    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
        related_name='category_offers'
    )
    
    class Meta:
        verbose_name = "Category Offer"
        verbose_name_plural = "Category Offers"
        unique_together = ['category']  # one active offer per category


class ReferralCode(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_code')
    code = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = get_random_string(length=8, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.code}"

class ReferralUsage(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred_by')
    used_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)  # Link to first order if you want reward on purchase

    class Meta:
        unique_together = ('referrer', 'referred_user')

    def __str__(self):
        return f"{self.referrer} referred {self.referred_user}"