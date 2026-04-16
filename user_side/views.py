import decimal
import json
import os
from django.shortcuts import render, redirect,get_object_or_404
from django.urls import reverse
import razorpay
from razorpay.errors import SignatureVerificationError
from admin_panel.models import CustomUser,ProductVariant,Product,ProductImage,Category,Userprofile,CartItem,WishlistItem,Address,Order,OrderItem,Coupon,WalletTransaction,Wallet,ReferralUsage, ReferralCode,ProductOffer,CategoryOffer
from django.contrib import messages
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, ExpressionWrapper, Min, Max,Avg,Case, When, Value,DecimalField,OuterRef,Subquery
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.views.decorators.http import require_POST,require_GET  
from django.http import JsonResponse,Http404,HttpResponse
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from decimal import Decimal
from datetime import datetime
from io import BytesIO
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import update_session_auth_hash
import random
import hashlib
import time
from social_django.models import UserSocialAuth
from django import forms
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.db.models import Sum,F
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from .razorpay_client import razorpay_client
from django.views.decorators.http import require_http_methods
from decimal import Decimal,ROUND_HALF_UP
import logging
from django.db import transaction as db_transaction
from django.db.models import Min,Count
from django.db.models.functions import Coalesce
from django.db.models import Prefetch
from django.contrib.auth import get_user_model
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from django.utils import timezone
logger = logging.getLogger(__name__)



MAX_QUANTITY_PER_ITEM = 5
MAX_CART_QUANTITY=5
EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'
#User=CustomUser




def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))
@never_cache
def UserSignup(request):
    errors={}
    form_data={'username':'','email':''}
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        username=request.POST.get('username','').strip()
        email=request.POST.get('email','').strip()
        password=request.POST.get('password','').strip()
        confirm_password=request.POST.get('confirm_password','').strip()
    
        form_data={'username':username,'email':email}
        if not username:
            errors['username']='User name is required'
        elif CustomUser.objects.filter(username=username).exists():
            errors['username']='Username already taken'
        elif not username.isalpha():
            errors['username']='Enter the Letter'


        if not email:
            errors['email']='Email is required'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email']='Email is already taken'
        elif not re.match(EMAIL_REGEX,email):
            errors['email']='Enter valid email address'
        
        if not password:
            errors['password']='Password is required'
        elif len(password)<6:
            errors['password']='Password must be at least 6 characters.'
        elif password.isdigit():
            errors['password']='Password can not contain only numbers'
        if not confirm_password:
            errors['confirm_password']='Confirm password is required'
        if password and confirm_password and password != confirm_password:
            errors['confirm_password']='Password do not match'
        
        if not errors:
            # Generate OTP and store user data temporarily
            otp = generate_otp()
            request.session['signup_data'] = {
                'username': username,
                'email': email,
                'password': password,
                'otp': otp,
                'otp_created_at': timezone.now().isoformat()
            }
            
            # Send OTP email
            try:
                send_mail(
                    subject='Your OTP for Signup',
                    message=f'Your OTP is {otp}. It is valid for 1 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                return redirect('verify_otp')
            except Exception as e:
                errors['email'] = 'Failed to send OTP. Please try again.'
    
    return render(request, 'user_side/user_signup.html', {'errors': errors, 'form_data': form_data})
@never_cache
def VerifyOTP(request):
    errors = {}
    if not request.session.get('signup_data'):
        return redirect('user_signup')

    signup_data = request.session.get('signup_data')

    # Parse otp_created_at from session and ensure it's timezone-aware
    try:
        otp_created_at = datetime.fromisoformat(signup_data['otp_created_at'])
    except Exception:
        # fallback: if parsing fails, treat as expired
        otp_created_at = None

    if otp_created_at is not None:
        # make timezone-aware if naive
        if timezone.is_naive(otp_created_at):
            otp_created_at = timezone.make_aware(otp_created_at, timezone.get_current_timezone())
    else:
        # If we couldn't parse created time, force expiry
        remaining_seconds = 0

    # compute expiry and remaining seconds (validity 1 minute here)
    if otp_created_at is not None:
        expiry_time = otp_created_at + timedelta(minutes=1)   # change minutes if you want different expiry
        remaining_seconds = max(0, int((expiry_time - timezone.now()).total_seconds()))

    if request.method == 'POST':
        # recompute remaining_seconds right before checking (in case time passed)
        if otp_created_at is not None:
            expiry_time = otp_created_at + timedelta(minutes=1)
            remaining_seconds = max(0, int((expiry_time - timezone.now()).total_seconds()))
        else:
            remaining_seconds = 0

        otp = request.POST.get('otp', '').strip()

        # If expired, show error and stay on the page (do NOT redirect)
        if remaining_seconds <= 0:
            errors['otp'] = 'OTP has expired. Please request a new one.'
            # messages.error(request, errors['otp'])
            # optionally: remove signup_data if you want to force re-signup
            # request.session.pop('signup_data', None)
            return render(request, 'user_side/verify_otp.html', {
                'errors': errors,
                'remaining_seconds': remaining_seconds
            })

        # normal validation
        if not otp:
            errors['otp'] = 'OTP is required'
            # messages.error(request, errors['otp'])
        elif otp != signup_data.get('otp'):
            errors['otp'] = 'Invalid OTP'
            # messages.error(request, errors['otp'])
        else:
            # Create user
            user = CustomUser.objects.create_user(
                username=signup_data['username'],
                email=signup_data['email'],
                password=signup_data['password']
            )
            user.save()
            Userprofile.objects.create(user=user)
            # clear signup data
            request.session.pop('signup_data', None)
            messages.success(request, 'Account created successfully.')
            return redirect('user_login')

    # GET or POST with errors -> render the same page with remaining_seconds and errors
    return render(request, 'user_side/verify_otp.html', {
        'errors': errors,
        'remaining_seconds': remaining_seconds
    })
@never_cache
def ResendOTP(request):
    if not request.session.get('signup_data'):
        return redirect('user_signup')
        
    signup_data = request.session.get('signup_data')
    
    # Check if enough time has passed since last OTP (30 seconds cooldown)
    otp_created_at = datetime.fromisoformat(signup_data['otp_created_at'])
    if timezone.now() < otp_created_at + timedelta(seconds=30):
        messages.error(request, 'Please wait before requesting a new OTP.')
        return redirect('verify_otp')
    
    # Generate and send new OTP
    new_otp = generate_otp()
    signup_data['otp'] = new_otp
    signup_data['otp_created_at'] = timezone.now().isoformat()
    request.session['signup_data'] = signup_data
    
    try:
        send_mail(
            subject='Your New OTP for Signup',
            message=f'Your new OTP is {new_otp}. It is valid for 1 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signup_data['email']],
            fail_silently=False,
        )
        messages.success(request, 'New OTP sent successfully.')
    except Exception:
        messages.error(request, 'Failed to send OTP. Please try again.')
    
    return redirect('verify_otp')
@never_cache
def ForgotPassword(request):
    errors = {}
    form_data = {'email': ''}
    
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        form_data = {'email': email}
        
        if not email:
            errors['email'] = 'Email is required'
        elif not re.match(EMAIL_REGEX, email):
            errors['email'] = 'Enter valid email address'
        elif not CustomUser.objects.filter(email=email).exists():
            errors['email'] = 'Email not registered'
        else:
            otp = generate_otp()
            request.session['reset_password_data'] = {
                'email': email,
                'otp': otp,
                'otp_created_at': timezone.now().isoformat()
            }
            
            try:
                send_mail(
                    subject='Your OTP for Password Reset',
                    message=f'Your OTP is {otp}. It is valid for 5 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                return redirect('verify_reset_otp')
            except Exception as e:
                print(f"Email sending failed: {str(e)}")  # Debug log
                errors['email'] = 'Failed to send OTP. Please try again.'
    
    return render(request, 'user_side/forgot_password.html', {'errors': errors, 'form_data': form_data})
@never_cache
def VerifyResetOTP(request):
    errors = {}
    if not request.session.get('reset_password_data'):
        return redirect('forgot_password')
        
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        reset_data = request.session.get('reset_password_data')
        
        otp_created_at = datetime.fromisoformat(reset_data['otp_created_at'])
        if timezone.now() > otp_created_at + timedelta(minutes=5):
            errors['otp'] = 'OTP has expired'
            request.session.pop('reset_password_data', None)
            return redirect('forgot_password')
            
        if not otp:
            errors['otp'] = 'OTP is required'
        elif otp != reset_data['otp']:
            errors['otp'] = 'Invalid OTP'
        else:
            return redirect('reset_password')
    
    return render(request, 'user_side/verify_reset_otp.html', {'errors': errors})
@never_cache
def ResendResetOTP(request):
    if not request.session.get('reset_password_data'):
        return redirect('forgot_password')
        
    reset_data = request.session.get('reset_password_data')
    
    otp_created_at = datetime.fromisoformat(reset_data['otp_created_at'])
    if timezone.now() < otp_created_at + timedelta(seconds=30):
        messages.error(request, 'Please wait before requesting a new OTP.')
        return redirect('verify_reset_otp')
    
    new_otp = generate_otp()
    reset_data['otp'] = new_otp
    reset_data['otp_created_at'] = timezone.now().isoformat()
    request.session['reset_password_data'] = reset_data
    
    try:
        send_mail(
            subject='Your New OTP for Password Reset',
            message=f'Your new OTP is {new_otp}. It is valid for 5 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reset_data['email']],
            fail_silently=False,
        )
        messages.success(request, 'New OTP sent successfully.')
    except Exception as e:
        print(f"Email sending failed: {str(e)}")  # Debug log
        messages.error(request, 'Failed to send OTP. Please try again.')
    
    return redirect('verify_reset_otp')
@never_cache
def ResetPassword(request):
    errors = {}
    if not request.session.get('reset_password_data'):
        return redirect('forgot_password')
        
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'
        elif password.isdigit():
            errors['password'] = 'Password cannot contain only numbers'
            
        if not confirm_password:
            errors['confirm_password'] = 'Confirm password is required'
        elif password and confirm_password and password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'
            
        if not errors:
            reset_data = request.session.get('reset_password_data')
            user = CustomUser.objects.get(email=reset_data['email'])
            user.set_password(password)
            user.save()
            request.session.pop('reset_password_data', None)
            messages.success(request, 'Password reset successfully.')
            return redirect('user_login')
    
    return render(request, 'user_side/reset_password.html', {'errors': errors})

@never_cache
def UserLogin(request):
    errors={}
    form_data={'username':''}
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        username=request.POST.get('username','').strip()
        password=request.POST.get('password','').strip()

        form_data={'username':username}
        if not username:
            errors['username']='Username is  required'
            print('email')
        if not password:
            errors['password']='Password is  required'
            print('password')
        print(errors)
        if not errors:
            try:
                user_obj = CustomUser.objects.get(email=username)  # look up by email
                user = authenticate(request, username=user_obj.username, password=password)
                print('user login')
            except CustomUser.DoesNotExist:
                print('not login')
                user = None
            if user is None:
                errors['non_field_errors'] = 'Invalid username or password'
            elif user.is_staff:
                errors['non_field_errors'] = 'Please log in using the admin login page'
                return redirect('/admin/login/')
            else:
                print('try to login')
                login(request, user)
                messages.success(request, 'Login successfully completed')
                return redirect('user_dashboard')
            
    return render(request,'user_side/user_login.html',{'errors':errors,'form_data':form_data})
@never_cache
@login_required(login_url='/login/')
def user_dashboard(request):   
    # Fetch 4 latest products for "Best Selling" (by created_at, newest first)
    best_selling = Product.objects.filter(is_active=True).order_by('-created_at').prefetch_related('images', 'variants')[:4]
    
    image_url='images/image1dashboard.jpg'
    
    return render(request, 'user_side/user_dashboard.html', {'best_selling':best_selling,'image_url':image_url})
@never_cache
@login_required(login_url='/login/')
def user_logout(request):
    if request.method == 'POST' and request.user.is_authenticated:
        logout(request)
        messages.success(request,'Logged out successfuly')

    return redirect('user_login')
@never_cache
@login_required
def product_list(request):
    queryset = Product.objects.filter(is_active=True)

    # Wishlist IDs
    wishlisted_product_ids = set()
    if request.user.is_authenticated:
        wishlisted_product_ids = set(
            WishlistItem.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    # Category filter
    category_ids = request.GET.getlist('category')
    selected_categories = category_ids
    if category_ids:
        queryset = queryset.filter(category__id__in=category_ids)

    # Price range input
    min_price_str = request.GET.get('min_price', '').strip()
    max_price_str = request.GET.get('max_price', '').strip()

    min_price = None
    max_price = None
    try:
        if min_price_str:
            min_price = float(min_price_str)
        if max_price_str:
            max_price = float(max_price_str)
    except ValueError:
        pass

    now = timezone.now()

    # Annotate minimum original price from variants
    product_offer_discount = ProductOffer.objects.filter(
        product=OuterRef('pk'),
        active=True,).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_until__isnull=True) | Q(valid_until__gte=now),
        ).order_by('-discount_percentage').values('discount_percentage')[:1]

    # Subquery to get the active category-level discount (highest)
    category_offer_discount = CategoryOffer.objects.filter(
        category=OuterRef('category_id'),
        active=True,).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_until__isnull=True) | Q(valid_until__gte=now),
    ).order_by('-discount_percentage').values('discount_percentage')[:1]

    # Main annotation
    queryset = queryset.annotate(
        product_discount=Coalesce(Subquery(product_offer_discount), Value(Decimal('0.00'))),
        category_discount=Coalesce(Subquery(category_offer_discount), Value(Decimal('0.00'))),
        
        # Take the highest discount available for this product
        max_discount=Case(
            When(product_discount__gt=F('category_discount'), then=F('product_discount')),
            default=F('category_discount'),
            output_field=DecimalField(max_digits=5, decimal_places=2)
        ),

        # Calculate minimum effective (discounted) price across all variants
        min_variant_price=Coalesce(
            Min(
                ExpressionWrapper(
                    F('variants__price') * (Value(1) - F('max_discount') / Value(100)),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            Decimal('0.00')
        ),

        variant_count=Count('variants', distinct=True)
    )
    if min_price is not None:
        queryset = queryset.filter(min_variant_price__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(min_variant_price__lte=max_price)

    # Sorting
    sort = request.GET.get('sort', '')
    if sort == 'price_low_high':
        queryset = queryset.order_by('min_variant_price')
    elif sort == 'price_high_low':
        queryset = queryset.order_by('-min_variant_price')
    elif sort == 'popularity':
        queryset = queryset.order_by('-sales_count')
    else:
        queryset = queryset.order_by('-id')

    # Pagination
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Prefetch related data safely for the current page
    if page_obj:
        product_ids = [p.id for p in page_obj]
        prefetched = Product.objects.filter(id__in=product_ids).prefetch_related('variants', 'images')
        prefetched_dict = {p.id: p for p in prefetched}

        for product in page_obj:
            if product.id in prefetched_dict:
                full_product = prefetched_dict[product.id]
                # No manual assignment needed

    for product in page_obj:
        product.discounted_min_price = getattr(product, 'get_discounted_price', lambda: Decimal('0.00'))()
        savings = getattr(product, 'get_savings_percentage', lambda: None)()
        product.savings_perc = savings if savings is not None else Decimal('0.00')
        product.has_offer = product.savings_perc > 0

    # Clear all filters
    if request.GET.get('clear'):
        return redirect('product_list')

    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'search_query': search_query,
        'selected_categories': selected_categories,
        'min_price': min_price_str,
        'max_price': max_price_str,
        'sort': sort,
        'wishlisted_product_ids': wishlisted_product_ids,
    }

    return render(request, 'user_side/product_list.html', context)
@never_cache
@login_required
def product_details(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)  
    if not product:
        return redirect('product_list')

     
    variants = product.variants.filter(is_active=True, stock__gt=0).select_related('product')
    if not variants.exists():
        messages.warning(request, 'This product is currently unavailable.')
        return redirect('product_list')

    # Wishlisted products 
    wishlisted_product_ids = set()
    if request.user.is_authenticated:
        wishlisted_product_ids = set(
            WishlistItem.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )

    selected_variant = None
    variant_id = request.GET.get('variant')
    print(variant_id,'hello')

    if variant_id:
            try:
                variant_id = int(variant_id)  # Coerce to int safely
                selected_variant = variants.filter(id=variant_id).first()
                if not selected_variant:
                    messages.info(request, "Selected size not available. Showing default.")
            except (ValueError, TypeError):
                print(f"Invalid variant ID: {variant_id}")  # Log bad input
                messages.warning(request, "Invalid size selected.")
            

    if not selected_variant:
        selected_variant = variants.order_by('price').first()

    base_url = f"{reverse('product_details', args=[product.slug])}?variant={selected_variant.id}" if selected_variant.id != variants.first().id else reverse('product_details', args=[product.slug])
    
    # Handle add-to-cart
    if request.method == 'POST':
        if selected_variant and selected_variant.stock <= 0:
            messages.error(request, "This size is out of stock.")
            return redirect('product_details', slug=product.slug)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return add_to_cart(request)
        if 'add_to_cart' in request.POST:
            return add_to_cart(request)

    # Related products
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id).prefetch_related('variants', 'images')[:4]

    # Cart item for this variant
    cart_item_in_context = None
    if request.user.is_authenticated and selected_variant:
        cart_item_in_context = request.user.cart_items.filter(variant=selected_variant).first()

    # Reviews
    reviews = product.reviews.all()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_count = reviews.count()

    # ────────────────────────────────────────────────
    # Offer & discount logic
    # ────────────────────────────────────────────────
    best_offer_perc = product.get_best_offer_percentage()  # should return Decimal or 0
    has_offer = best_offer_perc > Decimal('0.00')

    # Apply discount to every variant
    for variant in variants:
        original_price = variant.price
        discounted_price = original_price

        if has_offer:
            discount_factor = Decimal('1') - (best_offer_perc / Decimal('100'))
            discounted_price = (original_price * discount_factor).quantize(Decimal('0.01'))

        variant.original_price = original_price
        variant.discounted_price = discounted_price
        variant.savings_amount = original_price - discounted_price
        variant.savings_perc = best_offer_perc

    # Also set for the selected variant (consistent with others)
    selected_original_price = selected_variant.price
    selected_discounted_price = selected_original_price

    if has_offer:
        discount_factor = Decimal('1') - (best_offer_perc / Decimal('100'))
        selected_discounted_price = (selected_original_price * discount_factor).quantize(Decimal('0.01'))

    selected_variant.original_price = selected_original_price
    selected_variant.discounted_price = selected_discounted_price
    selected_variant.savings_amount = selected_original_price - selected_discounted_price
    selected_variant.savings_perc = best_offer_perc if has_offer else Decimal('0.00')

    # Add to product object for easy template access
    product.best_offer_perc = best_offer_perc
    product.has_offer = has_offer
    

    context = {
        'product': product,
        'variants': variants,
        'selected_variant': selected_variant,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'rating_count': rating_count,
        'cart_item': cart_item_in_context,
        'wishlisted_product_ids': wishlisted_product_ids,
    }

    return render(request, 'user_side/product_details.html', context)

@login_required
def profile_detail(request):
    user = request.user
    try:
        profile = user.profile.first()
    except Userprofile.DoesNotExist:
        profile = None

    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'user_side/user_profile.html', context)

@login_required
def _send_otp_email(request, email, otp):
    domain = request.META.get('HTTP_HOST', 'localhost:8000')
    subject = 'Verify your new email'
    message = render_to_string('profiles/email_otp.html', {
        'otp': otp,
        'domain': domain,
    })
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


def _make_token(user):
    return hashlib.sha256(f"{user.id}{time.time()}".encode()).hexdigest()[:20]


# ------------------------------------------------------------------
# PROFILE EDIT VIEW – NO FORM CLASS!
# ------------------------------------------------------------------
@login_required
def profile_edit(request):
    user = request.user
    profile = get_object_or_404(Userprofile, user=user)

    if request.method == 'POST':
        # --- MANUAL DATA EXTRACTION ---
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        image = request.FILES.get('image')

        # --- VALIDATION ---
        errors = {}

        if not email:
            errors['email'] = "Email is required."
        elif '@' not in email:
            errors['email'] = "Enter a valid email."

        if username and len(username) > 150:
            errors['username'] = "Username too long."

        # --- AUTO-SET USERNAME ---
        if not username:
            username = email  # fallback

        # --- EMAIL CHANGE → OTP ---
        if email != user.email:
            if errors:
                # show errors + keep form data
                return render(request, 'user_side/profile_edit.html', {
                    'user': user,
                    'profile': profile,
                    'input': request.POST,
                    'errors': errors,
                })

            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            request.session['pending_email'] = email
            request.session['pending_otp'] = otp
            request.session['pending_user_id'] = user.id

            _send_otp_email(request, email, otp)
            messages.info(request, 'OTP sent to new email.')
            return redirect('email_verify',
                            uidb64=urlsafe_base64_encode(force_bytes(user.pk)),
                            token=_make_token(user))

        # --- SAVE DATA ---
        if errors:
            return render(request, 'user_side/profile_edit.html', {
                'user': user,
                'profile': profile,
                'input': request.POST,
                'errors': errors,
            })

        # Update user
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone = phone
        user.address = address
        user.save()

        # Update image
        if image:
            profile.image = image
            profile.save()

        messages.success(request, 'Profile updated!')
        return redirect('profile_detail')

    # --- GET: Show form ---
    return render(request, 'user_side/profile_edit.html', {
        'user': user,
        'profile': profile,
        'input': {},  # no errors on load
        'errors': {},
    })


@login_required
def email_verify(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is None or user != request.user:
        messages.error(request, 'Invalid verification link.')
        return redirect('profiles:profile_detail')

    # Check OTP
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        session_otp = request.session.get('pending_otp')
        pending_email = request.session.get('pending_email')
        pending_user_id = request.session.get('pending_user_id')

        if (session_otp and pending_email and str(pending_user_id) == str(user.id) and entered_otp == session_otp):
            # OTP correct → update email
            user.email = pending_email
            user.save()

            # Clear session
            for key in ['pending_email', 'pending_otp', 'pending_user_id']:
                request.session.pop(key, None)

            messages.success(request, 'Email updated successfully!')
            return redirect('profiles:profile_detail')
        else:
            messages.error(request, 'Invalid or expired OTP.')

    # Show OTP form
    return render(request, 'user_side/profile_emailverify.html', {
        'user': user,
    })


@login_required
@login_required
def password_change(request):
    user = request.user

    # --- BLOCK GOOGLE / SOCIAL LOGIN USERS ---
    try:
        is_google_user = UserSocialAuth.objects.filter(
            user=user,
            provider='google-oauth2'
        ).exists()
    except Exception:
        is_google_user = False

    if is_google_user:
        messages.error(
            request,
            "You signed in with Google. Please use Google account settings to change your password."
        )
        return redirect('profile_detail')  # or your profile URL

    # --- NORMAL PASSWORD CHANGE ---
    if request.method == 'POST':
        form = PasswordChangeForm(user=user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Prevent logout
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile_detail')
    else:
        form = PasswordChangeForm(user=user)

    return render(request, 'user_side/profile_passwordchange.html', {
        'form': form
    })


def _send_otp_email(request, email, otp):
    current_site = get_current_site(request)
    mail_subject = 'Verify your new e-mail address'
    message = render_to_string('user_side/profile_emailotp.html', {
        'otp': otp,
        'domain': current_site.domain,
    })
    send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [email])


def _make_token(user):
    salt = str(time.time())
    return hashlib.sha256(f"{user.id}{salt}".encode()).hexdigest()[:20]



#  constants

MAX_CART_QUANTITY = 4        # you can move this to settings if you like



#  helper

def _is_purchasable(variant):
    if not variant or not variant.product or not variant.product.category:
        return False
    return (
        variant.is_active and
        variant.product.is_active and
        variant.product.category.is_active and
        variant.stock > 1
    )


# 1. add_to_cart

@login_required
@require_POST
def add_to_cart(request):
    variant_id = request.POST.get('variant_id')
    qty = int(request.POST.get('quantity', 1))

    if not variant_id:
        messages.error(request, "Please select a size.")
        return redirect('product_details')

    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    # 1. Purchasable check
    if not _is_purchasable(variant):
        messages.error(request, "This item cannot be added to the cart.")
        return redirect('product_details', slug=product.slug)

    # 2. Stock & max quantity check
    if qty > variant.stock:
        messages.error(request, f"Only {variant.stock} unit(s) available.")
        return redirect('product_details', slug=product.slug)

    if qty > 5:  # Replace with MAX_CART_QUANTITY constant if you have it
        messages.error(request, "Maximum 5 units allowed per item.")
        return redirect('product_details', slug=product.slug)

    # 3. Capture discounted price at add time (critical for consistency)
    discounted_unit_price = product.get_discounted_price(variant=variant)
    original_unit_price = variant.price

    # 4. Add / update cart
    with transaction.atomic():
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            variant=variant,
            defaults={
                'quantity': qty,
                'unit_price_at_add': original_unit_price,
                'discounted_price_at_add': discounted_unit_price,
            }
        )

        if not created:
            new_qty = cart_item.quantity + qty
            if new_qty > variant.stock:
                messages.error(request, "Not enough stock for the requested amount.")
                return redirect('product_details', slug=product.slug)
            if new_qty > 5:
                messages.error(request, "Maximum 5 units allowed per item.")
                return redirect('product_details', slug=product.slug)

            cart_item.quantity = new_qty
            cart_item.save()

    # 5. Response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'msg': f"Added {qty} × {variant.get_size_display()}",
            'cart_count': request.user.cart_items.count(),
            'cart_url': reverse('cart_detail')
        })

    messages.success(request, "Added to cart!")
    return redirect('cart_detail')


# cart_detail 

@login_required
def cart_detail(request):
    # Valid items only
    cart_items = CartItem.objects.filter(
        user=request.user,
        variant__is_active=True,
        variant__product__is_active=True,
        variant__product__category__is_active=True,
        variant__stock__gte=F('quantity')
    ).select_related('variant__product__category').order_by('-updated_at')

    # Invalid items
    invalid_items = CartItem.objects.filter(
        user=request.user
    ).exclude(id__in=cart_items.values_list('id', flat=True)
    ).select_related('variant__product')

    all_items=[]
    # Attach dynamic data
    for item in cart_items:
        item.is_valid = True
        item.disabled = False
        
        variant = item.variant
        product = variant.product
        
        item.original_unit_price = variant.price
        item.discounted_unit_price = product.get_discounted_price(variant=variant)
        item.discounted_total = item.discounted_unit_price * item.quantity
        item.total_savings = (item.original_unit_price - item.discounted_unit_price) * item.quantity

        all_items.append(item)

    for item in invalid_items:
        item.is_valid = False
        item.disabled = True
        item.discounted_total = 0
        item.total_savings = 0
        item.reason = []

        if not _is_purchasable(item.variant):
            if not item.variant.is_active:
                item.reason.append("Variant no longer available")
            if not item.variant.product.is_active:
                item.reason.append("Product unlisted")
            if not item.variant.product.category.is_active:
                item.reason.append("Category unlisted")
            if item.variant.stock < item.quantity:
                item.reason.append(f"Only {item.variant.stock} in stock")
        item.reason = ", ".join(item.reason) or "Item no longer available"

    #all_items = list(cart_items) + list(invalid_items)
    all_items.sort(key=lambda x: x.updated_at or timezone.now(), reverse=True)

    # Total using discounted prices
    cart_total = sum(item.discounted_total for item in cart_items)

    context = {
        'cart_items': all_items,
        'cart_total': cart_total,
        'has_valid_items': cart_items.exists(),
    }
    return render(request, 'user_side/cart_detail.html', context)


# 3. increment_quantity 
@require_POST
def increment_quantity(request, item_id):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    variant = cart_item.variant

    if not _is_purchasable(variant):
        return JsonResponse({'status': 'warning', 'message': 'This item is no longer available.'})

    if cart_item.quantity >= 5:  # MAX_QUANTITY_PER_ITEM
        return JsonResponse({'status': 'warning', 'message': 'Maximum 5 items allowed.'})

    if cart_item.quantity + 1 > variant.stock:
        return JsonResponse({'status': 'warning', 'message': f'Only {variant.stock} left in stock.'})

    cart_item.quantity += 1
    cart_item.save(update_fields=['quantity', 'updated_at'])

    # Recalculate valid total with discounted prices
    valid_total = CartItem.objects.filter(
        user=request.user,
        variant__is_active=True,
        variant__product__is_active=True,
        variant__product__category__is_active=True,
        variant__stock__gte=F('quantity')
    ).aggregate(total=Sum(F('quantity') * F('discounted_price_at_add')))['total'] or Decimal('0.00')

    item_count = CartItem.objects.filter(user=request.user).count()

    return JsonResponse({
        'status': 'success',
        'new_quantity': cart_item.quantity,
        'item_total': float(cart_item.discounted_price_at_add * cart_item.quantity),
        'grand_total': float(valid_total),
        'item_count': item_count,
        'available_stock': variant.stock,
    })


#  decrement_quantity 

@login_required
@require_POST
def decrement_quantity(request, item_id):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if cart_item.quantity <= 1:  # MAX_QUANTITY_PER_ITEM
        return JsonResponse({'status': 'warning', 'message': 'Minimum 1 items allowed.'})


    if cart_item.quantity <1:
        # Delete item
        cart_item.delete()

        # Recalculate total
        valid_total = CartItem.objects.filter(
            user=request.user,
            variant__is_active=True,
            variant__product__is_active=True,
            variant__product__category__is_active=True,
            variant__stock__gte=F('quantity')
        ).aggregate(total=Sum(F('quantity') * F('discounted_price_at_add')))['total'] or Decimal('0.00')

        item_count = CartItem.objects.filter(user=request.user).count()

        return JsonResponse({
            'status': 'success',
            'action': 'remove',
            'new_quantity': 0,
            'item_total': 0.0,
            'grand_total': float(valid_total),
            'item_count': item_count,
        })

    cart_item.quantity -= 1
    cart_item.save(update_fields=['quantity', 'updated_at'])

    valid_total = CartItem.objects.filter(
        user=request.user,
        variant__is_active=True,
        variant__product__is_active=True,
        variant__product__category__is_active=True,
        variant__stock__gte=F('quantity')
    ).aggregate(total=Sum(F('quantity') * F('discounted_price_at_add')))['total'] or Decimal('0.00')

    item_count = CartItem.objects.filter(user=request.user).count()

    return JsonResponse({
        'status': 'success',
        'new_quantity': cart_item.quantity,
        'item_total': float(cart_item.discounted_price_at_add * cart_item.quantity),
        'grand_total': float(valid_total),
        'item_count': item_count,
    })
@login_required
@require_POST
def remove_from_cart(request, item_id):  # ← ADD item_id here
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    
    with transaction.atomic():
        cart_item.delete()
        
        # Recalculate totals (optional – if you want fresh data)
        valid_total = CartItem.objects.filter(
            user=request.user,
            variant__is_active=True,
            variant__product__is_active=True,
            variant__product__category__is_active=True,
            variant__stock__gte=F('quantity')
        ).aggregate(total=Sum(F('quantity') * F('discounted_price_at_add')))['total'] or Decimal('0.00')
        
        item_count = CartItem.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'action': 'remove',
            'item_count': item_count,
            'grand_total': float(valid_total),
            'message': 'Item removed from cart'
        })

    messages.success(request, "Item removed from cart.")
    return redirect('cart_detail')

@login_required
@never_cache
def checkout(request):
    cart_items = request.user.cart_items.select_related('variant__product').all()
    if not cart_items.exists():
        return redirect('cart_detail')

    addresses = request.user.addresses.all()
    default_address = addresses.filter(is_default=True).first()


    # CALCULATE SUBTOTAL WITH OFFERS
    subtotal = Decimal('0.00')
    for item in cart_items:
        variant = item.variant
        product = variant.product
        
        # Get discounted unit price
        discounted_unit_price = product.get_discounted_price(variant=variant)
        
        # Total for this item
        item_total = discounted_unit_price * item.quantity
        subtotal += item_total
        
        # Attach to item for template (no assignment to properties)
        item.discounted_total = item_total
        item.discounted_unit_price = discounted_unit_price
        item.original_unit_price = variant.price
        # NO: item.has_offer = ...  ← DELETED – use product.has_offer in template

    # Tax & Shipping
    tax = subtotal * Decimal('0.05')
    shipping = Decimal('50') if subtotal < Decimal('500') else Decimal('0')
    total_before_coupon = subtotal + tax + shipping

    # ────────────────────────────────────────────────────────────────
    # COUPON LOGIC (on discounted subtotal)
    # ────────────────────────────────────────────────────────────────
    applied_coupon = None
    coupon_discount = Decimal('0')
    coupon_message = None

    applied_coupon_id = request.session.get('applied_coupon_id')
    if applied_coupon_id:
        try:
            coupon = Coupon.objects.get(id=applied_coupon_id, active=True)
            is_valid, msg = coupon.is_valid_for_user(request.user)
            if is_valid and coupon.min_purchase_amount <= subtotal:
                coupon_discount = coupon.calculate_discount(subtotal)
                applied_coupon = coupon
            else:
                request.session.pop('applied_coupon_id', None)
                coupon_message = msg or "This coupon is no longer valid"
        except Coupon.DoesNotExist:
            request.session.pop('applied_coupon_id', None)
            coupon_message = "Selected coupon no longer exists"

    grand_total = total_before_coupon - coupon_discount
    if grand_total < 0:
        grand_total = Decimal('0.00')

    # ────────────────────────────────────────────────────────────────
    # POST Actions
    # ────────────────────────────────────────────────────────────────
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'apply_coupon':
            code = request.POST.get('coupon_code', '').strip().upper()
            if not code:
                coupon_message = "Please enter a coupon code"
            else:
                try:
                    coupon_obj = Coupon.objects.get(code=code, active=True)
                    is_valid, msg = coupon_obj.is_valid_for_user(request.user)
                    if not is_valid:
                        coupon_message = msg
                    elif coupon_obj.min_purchase_amount > subtotal:
                        coupon_message = f"Minimum order amount ₹{coupon_obj.min_purchase_amount} required"
                    else:
                        with transaction.atomic():
                            discount = coupon_obj.calculate_discount(subtotal)
                            request.session['applied_coupon_id'] = coupon_obj.id
                            messages.success(request, f"₹{discount} discount applied using {code}!")
                            return redirect('checkout')
                except Coupon.DoesNotExist:
                    coupon_message = "Invalid or expired coupon code"

        elif action == 'remove_coupon':
            request.session.pop('applied_coupon_id', None)
            messages.info(request, "Coupon removed")
            return redirect('checkout')

        # Address actions (unchanged – add your code here if needed)


        # ================= ADD NEW ADDRESS =================
        if action == 'add_address':
            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            address_line_1 = request.POST.get('address_line_1')
            address_line_2 = request.POST.get('address_line_2', '')
            city = request.POST.get('city')
            state = request.POST.get('state')
            pincode = request.POST.get('pincode')
            is_default = request.POST.get('is_default') == 'on'

            # Validation
            if not all([full_name, phone, address_line_1, city, state, pincode]):
                messages.error(request, "Please fill all required fields.")
            elif len(phone) != 10 or not phone.isdigit():
                messages.error(request, "Enter valid 10-digit phone number.")
            elif len(pincode) != 6 or not pincode.isdigit():
                messages.error(request, "Enter valid 6-digit pincode.")
            else:
                if is_default:
                    request.user.addresses.update(is_default=False)

                Address.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=phone,
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    city=city,
                    state=state,
                    pincode=pincode,
                    is_default=is_default
                )
                messages.success(request, "Address added successfully!")
                return redirect('checkout')

        # ================= EDIT EXISTING ADDRESS =================
        elif action == 'edit_address':
            addr_id = request.POST.get('address_id')
            addr = get_object_or_404(Address, id=addr_id, user=request.user)

            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            address_line_1 = request.POST.get('address_line_1')
            address_line_2 = request.POST.get('address_line_2', '')
            city = request.POST.get('city')
            state = request.POST.get('state')
            pincode = request.POST.get('pincode')
            is_default = request.POST.get('is_default') == 'on'

            if not all([full_name, phone, address_line_1, city, state, pincode]):
                messages.error(request, "Please fill all required fields.")
            elif len(phone) != 10 or not phone.isdigit():
                messages.error(request, "Enter valid 10-digit phone number.")
            elif len(pincode) != 6 or not pincode.isdigit():
                messages.error(request, "Enter valid 6-digit pincode.")
            else:
                if is_default:
                    request.user.addresses.exclude(id=addr.id).update(is_default=False)

                addr.full_name = full_name
                addr.phone = phone
                addr.address_line_1 = address_line_1
                addr.address_line_2 = address_line_2
                addr.city = city
                addr.state = state
                addr.pincode = pincode
                addr.is_default = is_default
                addr.save()

                messages.success(request, "Address updated successfully!")
                return redirect('checkout')


        elif action == 'place_order':
            address_id = request.POST.get('address')
            if not address_id:
                messages.error(request, "Please select a delivery address.")
                return redirect('checkout')

            try:
                address = Address.objects.get(id=address_id, user=request.user)
            except Address.DoesNotExist:
                messages.error(request, "Invalid address selected.")
                return redirect('checkout')

            # ─── WALLET PROCESSING ────────────────────────────────
            use_wallet = request.POST.get('use_wallet') == '1'
            wallet_used_amount = Decimal('0.00')
            final_payable = grand_total

            wallet = Wallet.objects.filter(user=request.user).first()
            if use_wallet and wallet and wallet.balance > 0:
                wallet_used_amount = min(wallet.balance, grand_total)
                final_payable = grand_total - wallet_used_amount

            # Optional: prevent negative / zero payable if you want full wallet usage
            # if final_payable <= 0:
            #     final_payable = Decimal('0.00')

            # Save to session for payment page
            request.session['selected_address_id'] = address.id
            request.session['wallet_used_amount'] = float(wallet_used_amount)  # convert to float for session
            request.session['final_payable'] = float(final_payable)

            # Also keep coupon if applied
            if 'applied_coupon_id' in request.session:
                request.session['applied_coupon_id_temp'] = request.session['applied_coupon_id']

            # Prepare cart snapshot
            request.session['checkout_cart'] = [
                {
                    'variant_id': item.variant.id,
                    'quantity': item.quantity,
                    'price': float(item.discounted_unit_price),
                    'original_price': float(item.original_unit_price),
                    'product_name': item.variant.product.name,
                    'size': item.variant.get_size_display(),
                }
                for item in cart_items
            ]

            messages.success(request, f"Address confirmed! Pay ₹{final_payable:.2f} {'(using wallet)' if wallet_used_amount > 0 else ''}")
            return redirect('payment_page')

    # Wallet info
    wallet = Wallet.objects.filter(user=request.user).first()
    wallet_balance = wallet.balance if wallet else Decimal('0.00')

    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total_before_coupon': total_before_coupon,
        'coupon_discount': coupon_discount,
        'grand_total': grand_total,
        'applied_coupon': applied_coupon,
        'coupon_message': coupon_message,
        'wallet_balance': wallet_balance,
        'can_use_wallet': wallet_balance > 0,
    }

    return render(request, 'user_side/checkout.html', context)

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'user_side/order_success.html', {'order': order,'title': 'Order Placed Successfully!',})

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).select_related('address').prefetch_related('items__variant__product').order_by('-created_at')
    
    # Search
    query = request.GET.get('q')
    if query:
        orders = orders.filter(
            models.Q(order_id__icontains=query) |
            models.Q(created_at__date__icontains=query) |
            models.Q(status__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    context = {'orders': orders, 'query': query}
    return render(request, 'user_side/order_list.html', context)


@login_required
def order_detail(request, order_id):
    
    if order_id.isdigit():
        query_filter = Q(pk=order_id)
    else:
        query_filter = Q(order_id=order_id)

     
    if not request.user.is_staff:
        query_filter &= Q(user=request.user)


    order = get_object_or_404(Order, query_filter)

    
    items = order.items.select_related('variant__product').all()
    item_subtotal = sum(item.total for item in items)
    print(order.items.count())          
    

    context = {
        'order': order,
        'items': items,
        'item_subtotal': item_subtotal,
        'is_delivered': order.status == 'delivered',
        'has_delivery_date': order.delivered_at is not None,
    }
    return render(request, 'user_side/order_detail.html', context)
   
@login_required
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status__in=['pending', 'confirmed']
    )

    if order.status in ['delivered', 'cancelled', 'returned']:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('order_detail', order_id=order_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()

        with transaction.atomic():
            # 1. Mark as cancelled
            order.status = 'cancelled'
            order.cancel_reason = reason or None
            order.refund_status = 'completed'
            order.refund_amount = order.grand_total  # full refund
            order.save(update_fields=['status', 'cancel_reason', 'refund_status', 'refund_amount'])

            # 2. Refund to wallet
            # wallet, _ = Wallet.objects.get_or_create(user=request.user)
            # wallet.credit(
            #     amount=order.grand_total,
            #     description=f"Refund for cancelled order #{order.order_id}",
                
            # )

            # 3. Restore stock
            for item in order.items.select_related('variant'):
                ProductVariant.objects.filter(id=item.variant.id).update(
                    stock=F('stock') + item.quantity
                )

        messages.success(request, 'Order cancelled successfully. Full amount refunded to wallet.')
        return redirect('order_list')

    return render(request, 'user_side/cancel_order.html', {'order': order})
@login_required
@transaction.atomic
def cancel_item(request, order_id, item_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status__in=['pending', 'confirmed']
    )
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    # Block if order is already final
    if order.status in ['delivered', 'cancelled', 'returned']:
        messages.error(request, 'This order cannot be modified.')
        return redirect('order_detail', order_id=order_id)

    # Already requested?
    if item.cancel_requested:
        messages.info(request, 'Cancellation request already submitted.')
        return redirect('order_detail', order_id=order_id)
    

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for cancellation.')
        else:
            item.cancel_reason = reason
            item.cancel_requested = True
            item.cancel_requested_at = timezone.now()
            item.cancel_status = 'pending'
            item.save()

            messages.success(request, 'Cancellation request sent! Admin will review it soon.')
            return redirect('order_detail', order_id=order_id)
        
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()

        with transaction.atomic():
            order.status = 'cancelled'
            order.cancel_reason = reason or None
            order.refund_status = 'completed'
            order.refund_amount = order.grand_total  
            order.save(update_fields=['status', 'cancel_reason', 'refund_status', 'refund_amount'])

            # 2. Refund to wallet
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.credit(
                amount=order.grand_total,
                description=f"Refund for cancelled order #{order.order_id}",
                
            )
            for item in order.items.select_related('variant'):
                ProductVariant.objects.filter(id=item.variant.id).update(
                    stock=F('stock') + item.quantity
                )

    return render(request, 'user_side/cancel_item.html', {
        'order': order,
        'item': item,
    })

@login_required
def return_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if request.method == 'POST':
        reason = request.POST.get('reason')
        if item.can_request_return():
            item.return_requested = True
            item.return_requested_at = timezone.now()
            item.return_reason = reason
            item.save()
            order.status = 'return_requested'
            order.save()
            messages.success(request, "Return request submitted for this item.")
            return redirect('order_detail', order_id=order.order_id)
        else:
            messages.error(request, "Return not allowed for this item.")
    return render(request, 'user_side/return_item_form.html', {
        'item': item,
        'order': order
    })
@login_required
def cancel_order_item(request, order_id, item_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Not specified')
        if item.can_cancel():
            item.is_cancelled = True
            item.cancelled_at = timezone.now()
            item.cancel_reason = reason
            item.save()

    
            order.total_amount = sum(i.total for i in order.items.filter(is_cancelled=False))
            order.save()

            messages.success(request, f"Item cancelled successfully.")
        else:
            messages.error(request, "This item cannot be cancelled.")
        return redirect('order_detail', order_id=order.order_id)

    return render(request, 'user_side/cancel_item_form.html', {'item': item, 'order': order})
@login_required
@transaction.atomic
def return_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.status != 'delivered':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('order_detail', order_id=order_id)

    if order.status in ['return_requested', 'returned', 'cancelled']:
        messages.info(request, 'Return request already processed or order cancelled.')
        return redirect('order_detail', order_id=order_id)

    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for return.')
            return render(request, 'user_side/return_order.html', {'order': order})

        with transaction.atomic():
            order.return_reason = reason
            order.return_requested_at = timezone.now()
            order.status = 'return_requested'
            order.refund_status = 'pending'
            order.refund_amount = order.grand_total 
            order.save()

            
            order.items.update(return_requested=True)

        messages.success(request, 'Return request submitted. Refund will be processed after admin approval.')
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.credit(
            amount=order.grand_total,
            description=f"Refund for cancelled order #{order.order_id}",
                
            )
        return redirect('order_detail', order_id=order.order_id)

    return render(request, 'user_side/return_order.html', {'order': order})

def register_fonts():
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts')
    regular = os.path.join(font_path, 'DejaVuSans.ttf')
    bold = os.path.join(font_path, 'DejaVuSans-Bold.ttf')

    if os.path.exists(regular):
        pdfmetrics.registerFont(TTFont('DejaVuSans', regular))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold))

# Call this once at startup (add to apps.py or here)
register_fonts()
@login_required 
def download_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Block pending orders
    # if order.status == 'pending':
    #     return HttpResponse("Invoice will be available after order confirmation.", status=403)

    # Get only non-cancelled items
    items = order.items.select_related('variant__product').filter(is_cancelled=False)
    if not items.exists():
        return HttpResponse("No valid items in this order.", status=400)

    # Safe address handling
    address = order.address
    address_text = "No address recorded" if not address else (
        f"{address.full_name}\n"
        f"Phone: {address.phone or 'N/A'}\n"
        f"{address.address_line_1}\n"
        f"{address.address_line_2 or ''}\n"
        f"{address.city}, {address.state} - {address.pincode}"
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.fontSize = 10

    title = styles['Heading1']
    title.fontSize = 18
    title.alignment = 1  # center

    story = []

    # Header
    story.append(Paragraph("MR CAKE - TAX INVOICE", title))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Order ID: {order.order_id}", normal))
    story.append(Spacer(1, 12))

    # Customer & Order Info (simple table)
    customer_info = f"Bill To:\n{address_text}"
    order_info = f"""
        Order Date: {order.created_at.strftime('%d %b %Y')}
        Status: {order.get_status_display()}
        Payment: {order.payment_method.upper() if order.payment_method else 'N/A'}
        """

    info_table = Table(
        [[customer_info, order_info]],
        colWidths=[3.5*inch, 3.5*inch]
    )
    info_table.setStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
    ])
    story.append(info_table)
    story.append(Spacer(1, 24))

    # Items table – very simple
    data = [['No', 'Product', 'Size', 'Qty', 'Price', 'Total']]
    for idx, item in enumerate(items, 1):
        total = item.price * item.quantity
        data.append([
            str(idx),
            item.variant.product.name,
            item.variant.get_size_display() or '-',
            str(item.quantity),
            f" &#{item.price:,.2f}",
            f"{total:,.2f}",
        ])

    items_table = Table(data, colWidths=[0.5*inch, 2.5*inch, 0.8*inch, 0.6*inch, 1*inch, 1.1*inch])
    items_table.setStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('ALIGN', (4,1), (-1,-1), 'RIGHT'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ])
    story.append(items_table)

    # Grand Total
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"<b>Grand Total: ₹ {order.total_amount:,.2f}</b>", normal))

    story.append(Spacer(1, 40))
    story.append(Paragraph("Thank you for shopping with MR CAKE!", normal))

    # Build and return PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order.order_id}.pdf"'
    response.write(pdf)
    return response


@login_required
def address(request):
    # All addresses (default first)
    addresses = request.user.addresses.all().order_by('-is_default', '-id')

    # For Edit: Check if ?edit=5 in URL
    edit_addr = None
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            edit_addr = Address.objects.get(id=edit_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Address not found.")
            return redirect('address')

    if request.method == 'POST':
        action = request.POST.get('action')

        # ================= ADD NEW ADDRESS =================
        if action == 'add_address':
            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            address_line_1 = request.POST.get('address_line_1')
            address_line_2 = request.POST.get('address_line_2', '')
            city = request.POST.get('city')
            state = request.POST.get('state')
            pincode = request.POST.get('pincode')
            is_default = request.POST.get('is_default') == 'on'

            # Validation
            if not all([full_name, phone, address_line_1, city, state, pincode]):
                messages.error(request, "Please fill all required fields.")
            elif len(phone) != 10 or not phone.isdigit():
                messages.error(request, "Enter valid 10-digit phone number.")
            elif len(pincode) != 6 or not pincode.isdigit():
                messages.error(request, "Enter valid 6-digit pincode.")
            else:
                if is_default:
                    request.user.addresses.update(is_default=False)

                Address.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=phone,
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    city=city,
                    state=state,
                    pincode=pincode,
                    is_default=is_default
                )
                messages.success(request, "Address added successfully!")
                return redirect('address')

        # ================= EDIT EXISTING ADDRESS =================
        elif action == 'edit_address':
            addr_id = request.POST.get('address_id')
            addr = get_object_or_404(Address, id=addr_id, user=request.user)

            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            address_line_1 = request.POST.get('address_line_1')
            address_line_2 = request.POST.get('address_line_2', '')
            city = request.POST.get('city')
            state = request.POST.get('state')
            pincode = request.POST.get('pincode')
            is_default = request.POST.get('is_default') == 'on'

            if not all([full_name, phone, address_line_1, city, state, pincode]):
                messages.error(request, "Please fill all required fields.")
            elif len(phone) != 10 or not phone.isdigit():
                messages.error(request, "Enter valid 10-digit phone number.")
            elif len(pincode) != 6 or not pincode.isdigit():
                messages.error(request, "Enter valid 6-digit pincode.")
            else:
                if is_default:
                    request.user.addresses.exclude(id=addr.id).update(is_default=False)

                addr.full_name = full_name
                addr.phone = phone
                addr.address_line_1 = address_line_1
                addr.address_line_2 = address_line_2
                addr.city = city
                addr.state = state
                addr.pincode = pincode
                addr.is_default = is_default
                addr.save()

                messages.success(request, "Address updated successfully!")
                return redirect('address')

        # ================= DELETE ADDRESS =================
        elif action == 'delete_address':
            addr_id = request.POST.get('address_id')
            addr = get_object_or_404(Address, id=addr_id, user=request.user)
            addr.delete()
            messages.success(request, "Address deleted successfully.")
            return redirect('address')

    # Final context for template
    context = {
        'addresses': addresses,
        'edit_addr': edit_addr,   # This makes form auto-fill for edit
    }
    return render(request, 'user_side/address.html', context)


client = razorpay.Client(auth=(
    settings.RAZORPAY_KEY_ID,
    settings.RAZORPAY_KEY_SECRET
))


def rupees_to_paise(amount_rupees: float) -> int:
    """Safe conversion from rupees to paise using Decimal"""
    decimal_amount = Decimal(str(amount_rupees))  # str() avoids float precision issues
    paise = (decimal_amount * Decimal('100')).to_integral_value(rounding=ROUND_HALF_UP)
    return int(paise)


@csrf_exempt
@require_POST
@login_required
def create_razorpay_order(request):
    try:
        data = json.loads(request.body)

        amount_rupees = Decimal(str(data.get('amount', 0)))
        if amount_rupees <= 0:
            return JsonResponse({"error": "Invalid amount"}, status=400)

        amount_paise = rupees_to_paise(amount_rupees)

        print(f"Creating Razorpay order for {amount_rupees} INR = {amount_paise} paise")

        # Optional: Check for existing pending order for this user to avoid duplicates
        # (you can add a simple check in DB if you want)

        razorpay_order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"rcpt_{request.user.id}_{int(time.time())}",
            "notes": {
                "user_id": str(request.user.id),
                "source": "django_checkout"
            },
        })

        # Store only necessary data in session
        pending_data = {
            'total': float(amount_rupees),           # store as float for simplicity, or use str(Decimal)
            'discount': float(data.get('discount', 0)),
            'tax': float(data.get('tax', 0)),
            'shipping': float(data.get('shipping', 0)),
            'address_id': data.get('address_id'),
            'cart_items': data.get('cart_items', []),   # list of dicts
            'razorpay_amount_paise': amount_paise,      # important for verification
            'created_at': time.time(),
        }

        session_key = f"pending_order_{razorpay_order['id']}"
        request.session[session_key] = pending_data
        request.session.modified = True

        return JsonResponse({
            "status": True,
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],   # this is in paise
            "currency": razorpay_order["currency"],
            "key": settings.RAZORPAY_KEY_ID,
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except (ValueError, TypeError, decimal.InvalidOperation):
        return JsonResponse({"error": "Invalid amount format"}, status=400)
    except Exception as e:
        print(f"Razorpay order creation failed: {str(e)}")
        return JsonResponse({"error": "Failed to create Razorpay order"}, status=500)


@csrf_exempt
@require_POST
@login_required
def verify_razorpay_payment(request):
    try:
        data = json.loads(request.body)
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return JsonResponse({"success": False, "message": "Missing payment details"}, status=400)

        # Verify signature first (most important security step)
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        }
        client.utility.verify_payment_signature(params_dict)

        session_key = f"pending_order_{razorpay_order_id}"
        pending = request.session.get(session_key)

        if not pending:
            return JsonResponse({
                "success": False,
                "message": "Order session expired or not found. Please try again."
            }, status=400)

        # Extra safety: check if order was already processed
        if Order.objects.filter(razorpay_order_id=razorpay_order_id).exists():
            existing = Order.objects.get(razorpay_order_id=razorpay_order_id)
            return JsonResponse({
                "success": True,
                "order_id": existing.order_id,
                "message": "Order already created"
            })

        # Fetch address
        try:
            address = Address.objects.get(id=pending['address_id'], user=request.user)
        except Address.DoesNotExist:
            return JsonResponse({"success": False, "message": "Invalid address"}, status=400)

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                address=address,
                subtotal=Decimal(pending.get('total', 0)),   # adjust logic if subtotal != total
                discount=Decimal(pending.get('discount', 0)),
                tax=Decimal(pending.get('tax', 0)),
                shipping=Decimal(pending.get('shipping', 0)),
                total_amount=Decimal(pending.get('total', 0)),
                wallet_amount_used=Decimal(pending.get('wallet_amount_used', 0)),
                payment_method='razorpay',
                payment_status='paid',
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
                order_id=f"ORD-{request.user.id}-{get_random_string(8).upper()}"
            )

            for item_data in pending.get('cart_items', []):
                variant = ProductVariant.objects.select_for_update().get(
                    id=item_data['variant_id']
                )
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item_data['quantity'],
                    price=Decimal(item_data['price']),
                    total=Decimal(item_data['price']) * item_data['quantity']
                )
                variant.stock -= item_data['quantity']
                variant.save()

            # Clear cart
            request.user.cart_items.all().delete()

            # Cleanup session
            if session_key in request.session:
                del request.session[session_key]
            request.session.modified = True

        return JsonResponse({
            "success": True,
            "order_id": order.order_id,
            "message": "Payment successful! Order placed."
        })

    except SignatureVerificationError:
        return JsonResponse({"success": False, "message": "Invalid payment signature"}, status=400)
    except Exception as e:
        print(f"Payment verification error: {str(e)}")
        return JsonResponse({"success": False, "message": "Payment verification failed"}, status=500)




def rupees_to_paise(amount: Decimal) -> int:
    """Safe conversion to paise"""
    return int((amount * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def payment_page(request):
    if request.method == 'GET':
        selected_address_id = request.session.get('selected_address_id')
        if not selected_address_id:
            messages.error(request, "Please select an address.")
            return redirect('checkout')

        cart_items = request.user.cart_items.select_related('variant__product').all()
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect('cart_detail')

        try:
            address = Address.objects.get(id=selected_address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Invalid address.")
            return redirect('checkout')

        # ====================== CALCULATIONS ======================
        subtotal = Decimal('0.00')
        for item in cart_items:
            variant = item.variant
            product = variant.product

            discounted_unit_price = product.get_discounted_price(variant=variant)
            item_total = discounted_unit_price * item.quantity

            subtotal += item_total

            # Attach for template
            item.discounted_unit_price = discounted_unit_price
            item.discounted_total = item_total
            item.original_unit_price = variant.price

        # Coupon
        discount = Decimal('0.00')
        applied_coupon = None
        coupon_id = request.session.get('applied_coupon_id')

        if coupon_id:
            try:
                coupon = Coupon.objects.get(id=coupon_id, active=True)
                is_valid, _ = coupon.is_valid_for_user(request.user)
                if is_valid and subtotal >= coupon.min_purchase_amount:
                    discount = coupon.calculate_discount(subtotal)
                    applied_coupon = coupon
                else:
                    request.session.pop('applied_coupon_id', None)
            except Coupon.DoesNotExist:
                request.session.pop('applied_coupon_id', None)

        taxable_amount = max(Decimal('0.00'), subtotal - discount)
        tax = (taxable_amount * Decimal('0.05')).quantize(Decimal('0.01'))
        shipping = Decimal('0.00') if taxable_amount >= Decimal('500') else Decimal('50.00')
        grand_total = taxable_amount + tax + shipping

        # Wallet
        try:
            wallet_balance = Wallet.objects.get(user=request.user).balance
        except Wallet.DoesNotExist:
            wallet_balance = Decimal('0.00')

        context = {
            'cart_items': cart_items,
            'address': address,
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'discount': discount,
            'grand_total': grand_total,
            'applied_coupon': applied_coupon,
            'wallet_balance': wallet_balance,
            'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID,
            'amount_in_paise': rupees_to_paise(grand_total),   # Safe conversion
        }

        return render(request, 'user_side/payment_page.html', context)

    return redirect('checkout')

@csrf_exempt
@require_POST
@transaction.atomic
def place_order_final(request):
    payment_method = request.POST.get('payment_method', 'cod')
    address_id = request.session.get('selected_address_id')
    # Do NOT rely on 'checkout_cart' snapshot if possible — recalculate from DB for safety

    if not address_id:
        messages.error(request, "Session expired. Please select address again.")
        return redirect('checkout')

    address = get_object_or_404(Address, id=address_id, user=request.user)

    # Recalculate everything from live cart (safer than session snapshot)
    cart_items = request.user.cart_items.select_related('variant__product').all()
    if not cart_items:
        messages.error(request, "Cart is empty.")
        return redirect('cart_detail')

    subtotal = Decimal('0.00')
    for item in cart_items:
        discounted_price = item.variant.product.get_discounted_price(variant=item.variant)
        subtotal += discounted_price * item.quantity

    # Re-apply coupon safely
    discount_amount = Decimal('0.00')
    applied_coupon = None
    coupon_id = request.session.get('applied_coupon_id')
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, active=True)
            is_valid, _ = coupon.is_valid_for_user(request.user)
            if is_valid and subtotal >= coupon.min_purchase_amount:
                discount_amount = coupon.calculate_discount(subtotal)
                applied_coupon = coupon
        except Coupon.DoesNotExist:
            pass

    taxable_amount = max(Decimal('0.00'), subtotal - discount_amount)
    tax = (taxable_amount * Decimal('0.05')).quantize(Decimal('0.01'))
    shipping = Decimal('0.00') if taxable_amount >= 500 else Decimal('50.00')
    final_grand_total = taxable_amount + tax + shipping

    wallet_amount_used = Decimal('0.00')

    # ====================== WALLET LOGIC ======================
    if payment_method == 'wallet':
        try:
            wallet = Wallet.objects.select_for_update().get(user=request.user)
            if wallet.balance < final_grand_total:
                messages.error(request, "Insufficient wallet balance!")
                return redirect('payment_page')
            wallet_amount_used = final_grand_total
            wallet.debit(amount=wallet_amount_used, description=f"Order payment #{final_grand_total}")
        except Wallet.DoesNotExist:
            messages.error(request, "Wallet not found!")
            return redirect('payment_page')

    # ====================== STOCK VALIDATION ======================
    for item in cart_items:
        variant = ProductVariant.objects.select_for_update().get(id=item.variant_id)
        if variant.stock < item.quantity:
            messages.error(request, f"{item.variant.product.name} is out of stock!")
            return redirect('cart_detail')

    # ====================== CREATE ORDER ======================
    year = timezone.now().strftime('%Y')
    while True:
        random_part = get_random_string(6).upper()
        new_order_id = f"ORD-{year}-{random_part}"
        if not Order.objects.filter(order_id=new_order_id).exists():
            break

    order = Order.objects.create(
        user=request.user,
        address=address,
        subtotal=subtotal,
        discount=discount_amount,
        tax=tax,
        shipping=shipping,
        total_amount=final_grand_total,
        coupon=applied_coupon,
        coupon_code=applied_coupon.code if applied_coupon else '',
        coupon_discount=discount_amount,
        payment_method=payment_method,
        payment_status='paid' if payment_method in ['wallet', 'cod'] else 'pending',  # COD can be 'pending'
        wallet_amount_used=wallet_amount_used,
        order_id=new_order_id,
    )

    # ====================== ORDER ITEMS + STOCK ======================
    for item in cart_items:
        variant = ProductVariant.objects.select_for_update().get(id=item.variant_id)
        OrderItem.objects.create(
            order=order,
            variant=variant,
            quantity=item.quantity,
            price=item.variant.product.get_discounted_price(variant=variant),
        )
        variant.stock -= item.quantity
        variant.save()

    # ====================== CLEANUP ======================
    request.user.cart_items.all().delete()
    for key in ['selected_address_id', 'applied_coupon_id']:
        request.session.pop(key, None)

    messages.success(request, f"Order #{order.order_id} placed successfully!")

    if payment_method == 'razorpay':
        # This should NOT happen anymore — redirect to payment_page with Razorpay option
        return redirect('payment_page')

    return redirect('order_success', order_id=order.order_id)



@login_required
def toggle_wishlist(request, product_id):
    if not product_id:
        return JsonResponse({'status': 'error', 'message': 'Product ID required'}, status=400)

    try:
        product = Product.objects.get(id=product_id, is_delete=False)
        
        # Use get_or_create - returns (object, created) tuple
        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            wishlist_item.delete()
            return JsonResponse({'status': 'removed'})
        else:
            return JsonResponse({'status': 'added'})
            
    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)


@login_required
@login_required
def wishlist_view(request):
    
    wishlist_items = WishlistItem.objects.filter(
        user=request.user
    ).select_related(
        'product'
    ).prefetch_related(
        Prefetch(
            'product__variants',
            queryset=ProductVariant.objects.filter(
                is_active=True,
                stock__gt=0
            ).order_by('size'),  # sort variants logically
            to_attr='available_variants'  # attach as product.available_variants
        )
    ) # newest first

    context = {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
    }

    return render(request, 'user_side/wishlist.html', context)

@login_required
def move_to_cart_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method != 'POST':
        messages.error(request, "Invalid request.")
        return redirect('wishlist')

    variant_id = request.POST.get('variant_id')
    if not variant_id:
        messages.error(request, "Please select a size/variant.")
        return redirect('wishlist')

    variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    if not variant.is_active:
        messages.error(request, "This variant is no longer available.")
        return redirect('wishlist')

    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1

    if quantity < 1:
        quantity = 1
    if quantity > 5:
        messages.error(request, "Maximum 5 items allowed.")
        return redirect('wishlist')

    if quantity > variant.stock:
        messages.error(request,
            f"Only {variant.stock} item(s) available for {variant.get_size_display()}.")
        return redirect('wishlist')

    # ─── Capture prices at this moment (THIS WAS MISSING) ────────────────────
    original_unit_price = variant.price
    discounted_unit_price = product.get_discounted_price(variant=variant)

   
    with transaction.atomic():
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            variant=variant,
            defaults={
                'quantity': quantity,
                'unit_price_at_add': original_unit_price,
                'discounted_price_at_add': discounted_unit_price,
            }
        )

        if not created:
            new_quantity = cart_item.quantity + quantity

            if new_quantity > variant.stock:
                messages.error(request,
                    f"Only {variant.stock} available (you already have {cart_item.quantity}).")
                return redirect('wishlist')

            if new_quantity > 5:
                messages.error(request,
                    f"You already have {cart_item.quantity} in cart. Max is 5.")
                return redirect('wishlist')

            cart_item.quantity = new_quantity
            cart_item.save()

        # Remove from wishlist
        WishlistItem.objects.filter(
            user=request.user,
            product=product
        ).delete()

    messages.success(request,
        f"{product.name} ({variant.get_size_display()}) × {quantity} moved to cart!"
    )

    return redirect('cart_detail')
@login_required
@require_POST
def remove_from_wishlist(request, product_id):
    deleted_count = WishlistItem.objects.filter(
        user=request.user,
        product_id=product_id   # ← can use product_id directly — avoids extra query
    )

    if deleted_count.exists():
        deleted_count.delete()
        return JsonResponse({
            "success": True,
            "message": "Item removed",
            "count": WishlistItem.objects.filter(user=request.user).count()
        })
    
    return JsonResponse({
        "success": False, 
        "message": "Item not found"
    }, status=404) # 404 is more accurate than 400 here
@login_required
def my_wallet(request):
  
    # Get or create wallet (safe even if signal is missing)
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    # Recent transactions (newest first)
    recent_transactions = WalletTransaction.objects.filter(
        wallet=wallet
    ).select_related('order').order_by('-created_at')[:15]

    # Optional: quick summary stats
    total_credited = WalletTransaction.objects.filter(
        wallet=wallet,
        amount__gt=0
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    total_debited = WalletTransaction.objects.filter(
        wallet=wallet,
        amount__lt=0
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    context = {
        'wallet': wallet,
        'recent_transactions': recent_transactions,
        'total_credited': total_credited,
        'total_debited': abs(total_debited),  # show positive number
        'page_title': 'My Wallet',
        'current_balance': wallet.balance,
        'now':timezone.now(),
    }

    return render(request, 'user_side/my_wallet.html', context)


login_required
def wallet_history(request):
    
    wallet = get_object_or_404(Wallet, user=request.user)

    # GET filters (optional – user friendly)
    q_type     = request.GET.get('type')          # 'refund_cancel', 'refund_return', 'payment'
    q_search   = request.GET.get('q', '').strip() # search in description/order_id
    date_start = request.GET.get('start')
    date_end   = request.GET.get('end')

    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')

    if q_type and q_type in dict(WalletTransaction.TRANSACTION_TYPES):
        transactions = transactions.filter(transaction_type=q_type)

    if q_search:
        transactions = transactions.filter(
            Q(description__icontains=q_search) |
            Q(order__order_id__icontains=q_search)
        )

    if date_start:
        try:
            transactions = transactions.filter(created_at__gte=date_start)
        except:
            pass

    if date_end:
        try:
            transactions = transactions.filter(created_at__lte=f"{date_end} 23:59:59")
        except:
            pass

    # Limit for performance (pagination can be added later)
    transactions = transactions[:150]

    context = {
        'wallet': wallet,
        'transactions': transactions,
        'page_title': 'Wallet Transaction History',
        'filters': {
            'type': q_type,
            'q': q_search,
            'start': date_start,
            'end': date_end,
        }
    }

    return render(request, 'user_side/history.html', context)


def all_coupons(request):
    # Get all coupons, newest first
    coupons = Coupon.objects.all().order_by('-valid_from')
    
    # Optional: add current time to context so template can compare easily
    now = timezone.now()
    
    context = {
        'coupons': coupons,
        'now': now,
    }
    
    return render(request,'user_side/coupon_list.html', context)

  

@login_required
def my_referrals(request):
    referral_code,created = ReferralCode.objects.get_or_create(user=request.user)
    
    my_referrals = ReferralUsage.objects.filter(referrer=request.user).select_related('referred_user')

    context = {
        'referral_code': referral_code,
        'referral_link': request.build_absolute_uri(f"/register/?ref={referral_code.code}"),
        'my_referrals': my_referrals,
        'total_referred': my_referrals.count(),
    }
    return render(request, 'user_side/my_referrals.html', context)



@login_required
@login_required
def apply_referral(request):
    if request.method == 'POST':
        referral_code_input = request.POST.get('referral_code', '').strip().upper()

        if not referral_code_input:
            messages.error(request, 'Please enter a referral code.')
            return redirect('user_dashboard')

        user = request.user

        try:
            with transaction.atomic():
                # Find the referral code
                referral_code_obj = ReferralCode.objects.get(code=referral_code_input)
                referrer = referral_code_obj.user

                # Prevent self-referral
                if referrer == user:
                    messages.error(request, 'You cannot use your own referral code.')
                    return redirect('user_dashboard')

                # Prevent duplicate referral
                if ReferralUsage.objects.filter(referred_user=user).exists():
                    messages.error(request, 'You have already used a referral code.')
                    return redirect('user_dashboard')

                # Create ReferralUsage record
                ReferralUsage.objects.create(
                    referrer=referrer,
                    referred_user=user
                )

                # Credit ₹100 to New User (You)
                referee_wallet = Wallet.objects.get_or_create(user=user)[0]
                referee_wallet.credit(
                    amount=Decimal('100.00'),
                    description=f"Welcome Reward - Referred by {referrer.username}"
                )

                # Credit ₹100 to Referrer
                referrer_wallet = Wallet.objects.get_or_create(user=referrer)[0]
                referrer_wallet.credit(
                    amount=Decimal('100.00'),
                    description=f"Referral Reward - For inviting {user.username}"
                )

                messages.success(request, '✅ Referral applied successfully! ₹100 credited to both wallets.')
                return redirect('user_dashboard')

        except ReferralCode.DoesNotExist:
            messages.error(request, 'Invalid referral code. Please check and try again.')
            return redirect('user_dashboard')

        except Exception as e:
            messages.error(request, f'Something went wrong: {str(e)}')
            return redirect('user_dashboard')

    # GET request
    messages.error(request, 'Invalid request.')
    return redirect('user_dashboard')