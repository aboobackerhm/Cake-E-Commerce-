from datetime import timezone
from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout,get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.generic import View
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q,Max
from .models import Category, Coupon
from django.shortcuts import get_object_or_404
from .models import Product,ProductImage,ProductVariant,CustomUser,Order,OrderItem,ProductOffer,CategoryOffer,Wallet,WalletTransaction
import os
from django.db import transaction,IntegrityError
from decimal import Decimal
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_http_methods  
# Create your views here.

class AdminLoginView(View):
    def get(self,request):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect('admin_dashboard')
        return render(request,'admin_panel/login.html')
    def post(self,request):
        username=request.POST.get('username')
        password=request.POST.get('password')
        user=authenticate(request,username=username,password=password)
        if user is not None and user.is_superuser:
            login(request,user)
            return redirect('admin_dashboard')
        else:
            messages.error(request,'Invalied credentials or not an admin')
            return render(request,'admin_panel/login.html')
@never_cache 
@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')
@never_cache
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('admin_login')
    return render(request,'admin_panel/admin_dashboard.html')
@never_cache
@login_required
def user_management(request):
    if not request.user.is_superuser:
        return redirect('admin_login')
    
    query=request.GET.get('q','')
    users=CustomUser.objects.all().order_by('-date_joined')

    if query:
        users=users.filter(
            Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query)
        )
    
    paginator=Paginator(users,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    return render(request,'admin_panel/user_management.html',{'page_obj':page_obj,'query':query})
@never_cache
@login_required
def block_user(request,user_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    user=get_object_or_404(CustomUser,id=user_id)
    if user.is_superuser:
        messages.error(request,'You cannot block a superuser')
        return redirect('user_management')
    user.is_active = False
    user.save()
    messages.success(request,f'User {user.username} blocked')
    return redirect('user_management')
@never_cache
@login_required
def unblock_user(request,user_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    user=get_object_or_404(CustomUser,id=user_id)
    user.is_active=True
    user.save()
    messages.success(request,f'User {user.username} unblocked.')
    return redirect('user_management')

@never_cache
@login_required
def category_management(request):
    if not request.user.is_superuser:
        return redirect('admin_login')
    
    query=request.GET.get('q','')
    categories=Category.objects.all().order_by('-created_at')

    if query:
        categories=categories.filter(name__icontains=query)
    
    paginator=Paginator(categories,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    return render(request,'admin_panel/category_management.html',{'page_obj':page_obj,'query':query})
@never_cache
@login_required
def add_category(request):
    if not request.user.is_superuser:
        return redirect('admin_login')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        # 1) Check empty fields
        if not name :
            messages.error(request, "Name  cannot be empty.")
            return render(request, 'admin_panel/add_category.html', {
                'name': name,
                'description': description,
            })
        if  not description:
            messages.error(request, "Description cannot be empty.")
            return render(request, 'admin_panel/add_category.html', {
                'name': name,
                'description': description,
            })

        # 2) Check duplicate category name (case insensitive)
        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Category '{name}' already exists.")
            return render(request, 'admin_panel/add_category.html', {
                'name': name,
                'description': description,
            })

        # ✅ If all good → save
        Category.objects.create(name=name, description=description)
        messages.success(request, f"Category '{name}' added successfully.")
        return redirect('category_management')

    return render(request, 'admin_panel/add_category.html')

@never_cache
@login_required
def edit_category(request,cat_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    category=Category.objects.get(id=cat_id)
    if request.method == 'POST':
        name=request.POST.get('name')
        description=request.POST.get('description')
        if not name  :
            messages.error(request,'you will enter the correct category name')
            return redirect('category_management')
        if not description :
            messages.error(request,'you will fill the discription')
            return redirect('category_management')
        category.name=name
        category.description=description
        category.save()
        messages.success(request,'Succes fully created')
        return redirect('category_management')
        # messages.success(request,'Category updated')
        
    return render(request,'admin_panel/edit_category.html',{'category':category})
@never_cache
@login_required
def softdelete_category(request,cat_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    category=Category.objects.get(id=cat_id)
    category.is_active=False
    category.save()
    #messages.success(request,'Category is deleted')
    return redirect('category_management')
@login_required
def softreturn_category(request,cat_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    category=Category.objects.get(id=cat_id)
    category.is_active=True
    category.save()
    return redirect('category_management')
@login_required
def delete_category(request,cat_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    catergory=Category.objects.get(id=cat_id)
    catergory.delete()
    return redirect('category_management')
@never_cache
@login_required
def product_management(request):
    if not request.user.is_superuser:
        return redirect('admin_login')
    
    query=request.GET.get('q', '')
    products=Product.objects.filter(category__is_active=True).order_by('-created_at')
    # productvariant=ProductVariant.objects.filter(product__is_active=True).order_by('-created_at')

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query)
        )
    paginator=Paginator(products,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    return render(request,'admin_panel/product_management.html',{'page_obj':page_obj ,'query':query})
@never_cache
@login_required
def add_product(request):
    if not request.user.is_superuser:
        return redirect('admin_login')
    product=Product.objects.all()
    categories = Category.objects.filter(is_active=True)
    if not categories.exists():
        messages.error(request, 'No active categories available. Please add a category first.')
        return redirect('category_management')
    
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price_500g = request.POST.get('price_500g')
        price_750g = request.POST.get('price_750g')
        price_1kg = request.POST.get('price_1kg')
        price_2kg = request.POST.get('price_2kg')
        stock_500g = request.POST.get('stock_500g')
        stock_750g = request.POST.get('stock_750g')
        stock_1kg = request.POST.get('stock_1kg')
        stock_2kg = request.POST.get('stock_2kg')
        category_id = request.POST.get('category')
        images = request.FILES.getlist('images')

        errors = []
        if not name:
            errors.append('Name is required and cannot be just whitespace')
        elif Product.objects.filter(name__iexact=name).exists():
            errors.append('A product with this name already exists')

        if not description:
            errors.append('Description is required and cannot be just whitespace')
        if not category_id:
            errors.append('Please select a valid category')
        if len(images) < 3:
            errors.append('At least 3 images are required')
        
        # Validate images
        for img in images:
            if not img.content_type.startswith('image/'):
                errors.append(f'{img.name} is not a valid image file')
            if img.size > 5 * 1024 * 1024:  # 5MB limit
                errors.append(f'Image {img.name} exceeds 5MB size limit')
        
        size_data = [
            ('500g', price_500g, stock_500g),
            ('750g', price_750g, stock_750g),
            ('1kg', price_1kg, stock_1kg),
            ('2kg', price_2kg, stock_2kg),
        ]
        valid_sizes = []
        for size, price, stock in size_data:
            if not price and not stock:
                continue
            if not price or not price.strip():
                errors.append(f'Price for {size} is required when stock is provided')
                continue
            try:
                price = Decimal(price.strip())
                if price <= 0:
                    errors.append(f'Valid price for {size} is required (e.g., 29.99)')
                    continue
            except (ValueError, TypeError):
                errors.append(f'Valid price for {size} is required (e.g., 29.99)')
                continue
            if not stock or not stock.strip():
                errors.append(f'Stock for {size} is required when price is provided')
                continue
            try:
                stock = int(stock.strip())
                if stock < 0:
                    errors.append(f'Valid non-negative stock for {size} is required')
                    continue
            except (ValueError, TypeError):
                errors.append(f'Valid non-negative stock for {size} is required')
                continue
            valid_sizes.append((size, price, stock))

        if not valid_sizes:
            errors.append('At least one size with valid price and stock is required')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'admin_panel/add_product.html', {
                'categories': categories,
                'form_data': request.POST,
                'images_count': len(images),
            })
        
        try:
            category = Category.objects.get(id=category_id, is_active=True)
            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    description=description,
                    category=category,
                )
                for size, price, stock in valid_sizes:
                    ProductVariant.objects.create(
                        product=product,
                        size=size,
                        price=price,
                        stock=stock,
                    )
                for idx, img in enumerate(images):
                    ProductImage.objects.create(product=product, image=img, order=idx+1)
            
            messages.success(request, 'Product added successfully')
            return redirect('product_management')
        except Category.DoesNotExist:
            messages.error(request, 'Invalid category selected')
        except IntegrityError as e:
            messages.error(request, f'Database error: {str(e)}')
        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')
        
        return render(request, 'admin_panel/add_product.html', {
            'categories': categories,
            'form_data': request.POST,
            'images_count': len(images),
        })
    
    return render(request, 'admin_panel/add_product.html', {'categories': categories})
@never_cache
@login_required
def edit_product(request, prod_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    
    try:
        product = Product.objects.get(id=prod_id)
        categories = Category.objects.filter(is_active=True)
        variants = {v.size: v for v in ProductVariant.objects.filter(product=product)}
        sizes = ['500g', '750g', '1kg', '2kg']
        variant_list = []
        for size in sizes:
            variant = variants.get(size)
            variant_list.append({
                'size': size,
                'price': variant.price if variant else None,
                'stock': variant.stock if variant else None
            })

        if not categories.exists():
            messages.error(request, 'No active categories available. Please add a category first.')
            return redirect('category_management')

        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            price_500g = request.POST.get('price_500g')
            price_750g = request.POST.get('price_750g')
            price_1kg = request.POST.get('price_1kg')
            price_2kg = request.POST.get('price_2kg')
            stock_500g = request.POST.get('stock_500g')
            stock_750g = request.POST.get('stock_750g')
            stock_1kg = request.POST.get('stock_1kg')
            stock_2kg = request.POST.get('stock_2kg')
            category_id = request.POST.get('category')
            new_images = request.FILES.getlist('images')
            delete_ids = request.POST.getlist('delete_images')

            errors = []
            if not name:
                errors.append('Name is required and cannot be just whitespace')
            if not description:
                errors.append('Description is required and cannot be just whitespace')
            if not category_id:
                errors.append('Please select a valid category')

            # Validate images
            for img in new_images:
                if not img.content_type.startswith('image/'):
                    errors.append(f'{img.name} is not a valid image file')
                if img.size > 5 * 1024 * 1024:  # 5MB limit
                    errors.append(f'Image {img.name} exceeds 5MB size limit')

            size_data = [
                ('500g', price_500g, stock_500g),
                ('750g', price_750g, stock_750g),
                ('1kg', price_1kg, stock_1kg),
                ('2kg', price_2kg, stock_2kg),
            ]
            valid_sizes = []
            for size, price, stock in size_data:
                if not price and not stock:
                    continue
                if not price or not price.strip():
                    errors.append(f'Price for {size} is required when stock is provided')
                    continue
                try:
                    price = Decimal(price.strip())
                    if price <= 0:
                        errors.append(f'Valid positive price for {size} is required (e.g., 29.99)')
                        continue
                except (ValueError, TypeError):
                    errors.append(f'Valid price for {size} is required (e.g., 29.99)')
                    continue
                if not stock or not stock.strip():
                    errors.append(f'Stock for {size} is required when price is provided')
                    continue
                try:
                    stock = int(stock.strip())
                    if stock < 0:
                        errors.append(f'Valid non-negative stock for {size} is required')
                        continue
                except (ValueError, TypeError):
                    errors.append(f'Valid non-negative stock for {size} is required')
                    continue
                valid_sizes.append((size, price, stock))

            remaining_images = ProductImage.objects.filter(product=product).exclude(id__in=delete_ids)
            if remaining_images.count() + len(new_images) < 3:
                errors.append('At least 3 images are required after deletions and new uploads')
            if not valid_sizes:
                errors.append('At least one size with valid price and stock is required')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'admin_panel/edit_product.html', {
                    'product': product,
                    'categories': categories,
                    'variant_list': variant_list,
                    'form_data': request.POST,
                    'images_count': len(new_images)
                })

            try:
                category = Category.objects.get(id=category_id, is_active=True)
                with transaction.atomic():
                    # Update product details
                    product.name = name
                    product.description = description
                    product.category = category
                    product.save()

                    # Update or create variants
                    existing_sizes = set(variants.keys())
                    new_sizes = set(size for size, _, _ in valid_sizes)
                    for size, price, stock in valid_sizes:
                        variant = variants.get(size)
                        if variant:
                            variant.price = price
                            variant.stock = int(stock)
                            variant.save()
                        else:
                            ProductVariant.objects.create(
                                product=product,
                                size=size,
                                price=price,
                                stock=int(stock)
                            )

                    # Delete variants not in the new submission
                    for size in existing_sizes - new_sizes:
                        variants[size].delete()

                    # Delete selected images
                    for img_id in delete_ids:
                        try:
                            img = ProductImage.objects.get(id=img_id, product=product)
                            image_path = img.image.path
                            if os.path.exists(image_path):
                                os.remove(image_path)
                            img.delete()
                        except ProductImage.DoesNotExist:
                            messages.warning(request, f'Image ID {img_id} not found for this product')

                    # Add new images
                    if new_images:
                        max_order = ProductImage.objects.filter(product=product).aggregate(Max('order'))['order__max'] or 0
                        for idx, img in enumerate(new_images):
                            ProductImage.objects.create(
                                product=product,
                                image=img,
                                order=max_order + idx + 1
                            )

                messages.success(request, 'Product updated successfully')
                return redirect('product_management')
            except Category.DoesNotExist:
                messages.error(request, 'Invalid category selected')
            except IntegrityError as e:
                messages.error(request, f'Database error: {str(e)}')
            except Exception as e:
                messages.error(request, f'Unexpected error: {str(e)}')
            
            return render(request, 'admin_panel/edit_product.html', {
                'product': product,
                'categories': categories,
                'variant_list': variant_list,
                'form_data': request.POST,
                'images_count': len(new_images)
            })

        return render(request, 'admin_panel/edit_product.html', {
            'product': product,
            'categories': categories,
            'variant_list': variant_list
        })
    except Product.DoesNotExist:
        messages.error(request, 'Product not found')
        return redirect('product_management')
@login_required
@never_cache
@login_required
def softdelete_product(request,prod_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    product=Product.objects.get(id=prod_id)
    product.is_active=False
    product.save()
    return redirect('product_management')
@login_required
def softreturn_product(request,prod_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    product=Product.objects.get(id=prod_id)
    product.is_active=True
    product.save()
    return redirect('product_management')
@login_required
def delete_product(request,prod_id):
    if not request.user.is_superuser:
        return redirect('admin_login')
    try:
        product=Product.objects.get(id=prod_id)
        with transaction.atomic(): 
            for image in product.images.all():
                if os.path.exists(image.image.path):
                    os.remove(image.image.path)
                image.delete()
            product_name=product.name
            product.delete()
        messages.success(request,f'Product "{product_name}" and all variant deleted successfully')
        return redirect('product_management')
    except Product.DoesNotExist:
        messages.error(request,'Product not found')
        return redirect('product_management')
    except Exception as e:
        messages.error(request,f'Error deleting product: {str(e)}')
        return redirect('product_management')
@login_required
@never_cache
def delete_product_variant(request, prod_id, size):
    if not request.user.is_superuser:
        return redirect('admin_login')
    
    try:
        product = Product.objects.get(id=prod_id)
        if ProductVariant.objects.filter(product=product).count() <= 1:
            messages.error(request, f'Cannot delete the last variant ({size}) for product "{product.name}". Products must have at least one size variant.')
            return redirect('product_management')
        
        variant = ProductVariant.objects.get(product=product, size=size)
        with transaction.atomic():
            variant_name = f"{product.name} ({variant.size})"
            variant.delete()
        
        messages.success(request, f'Variant "{variant_name}" deleted successfully')
        return redirect('product_management')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found')
        return redirect('product_management')
    except ProductVariant.DoesNotExist:
        messages.error(request, f'Variant "{size}" for product not found')
        return redirect('product_management')
    except Exception as e:
        messages.error(request, f'Error deleting variant: {str(e)}')
        return redirect('product_management')
@login_required
def softdelete_product_variant(request,prod_id,size):
    if not request.user.is_superuser:
        return redirect('admin_login')
    product=Product.objects.get(id=prod_id)
    ProductVariant.objects.filter(product=product,size=size).update(is_active=False)
    return redirect('product_management')
def softreturn_product_variant(request,prod_id,size):
    if not request.user.is_superuser:
        return redirect('admin_login')
    product=Product.objects.get(id=prod_id)
    ProductVariant.objects.filter(product=product,size=size).update(is_active=True)
    return redirect('product_management')
@login_required
def order_list(request):
    qs = Order.objects.select_related('user', 'address').order_by('-created_at')
    
    # Search
    q = request.GET.get('q')
    if q:
        qs = qs.filter(
            models.Q(order_id__icontains=q) |
            models.Q(user__username__icontains=q) |
            models.Q(user__email__icontains=q) |
            models.Q(address__phone__icontains=q)
        )

    # Filters
    # if request.GET.get('status'):
    #     qs = qs.filter(status=request.GET['status'])
    # if request.GET.get('payment_method'):
    #     qs = qs.filter(payment_method=request.GET['payment_method'])

    # Pagination
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Status change
    # if request.method == "POST":
    #     order = get_object_or_404(Order, id=request.POST['order_id'], user__is_staff=False)
    #     order.status = request.POST['status']
    #     order.save()
    #     messages.success(request, f"Order {order.order_id} updated to {order.get_status_display()}")
    #     return redirect('order_lists')

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'admin_panel/orders_list.html', context)
@login_required
def admin_order_detail(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('order_management')
    
    order = get_object_or_404(Order, pk=pk)
    context = {
        'order': order,
        'items': order.items.select_related('variant__product').all(),
    }
    return render(request, 'admin_panel/order_detail.html', context)

def update_order_status(request, pk):  
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST['status']
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f"Order {order.order_id} updated to {order.get_status_display()}.")
        else:
            messages.error(request, "Invalid status.")
    
    return redirect('order_management')
@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'GET':
        reason = request.GET.get('reason')
        if reason:
            order.status = 'cancelled'
            order.cancel_reason = reason
            order.save()
            messages.success(request, f"Order {order.order_id} cancelled successfully.")
        else:
            messages.error(request, "Cancellation reason is required.")
    
    return redirect('order_management')
@login_required
def manage_return_requests(request):
    if not request.user.is_staff:
        raise PermissionError("Not allowed")

    returns = Order.objects.filter(status='return_requested').order_by('-return_requested_at')
    return render(request, 'admin_panel/return_requests.html', {'returns': returns})


@login_required
def approve_return(request, order_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized")
        return redirect('admin_dashboard')

    order = get_object_or_404(Order, id=order_id, status='return_requested')

    if request.method == 'POST':
        # Process return: restore stock + mark as returned
        for item in order.items.all():
            if item.return_requested:
                item.variant.stock += item.quantity
                item.variant.save()
                item.is_returned = True
                item.return_requested = False
                item.save()

        order.status = 'returned'
        order.return_approved_at = timezone.now()
        order.save()

        # Optional: Refund to wallet
        # from wallet.models import Wallet, Transaction
        # wallet, _ = Wallet.objects.get_or_create(user=order.user)
        # wallet.balance += order.total_amount
        # wallet.save()
        # Transaction.objects.create(...)

        messages.success(request, f"Return approved for order {order.order_id}")
        return redirect('manage_return_requests')

    return render(request, 'admin_panel/approve_return.html', {'order': order})


@login_required
def reject_return(request, order_id):
    if not request.user.is_staff:
        messages.error(request, "Unauthorized")
        return redirect('admin_dashboard')

    order = get_object_or_404(Order, id=order_id, status='return_requested')

    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, "Rejection reason is required.")
            return render(request, 'admin_panel/reject_return.html', {'order': order})

        order.status = 'delivered'  # back to delivered
        order.return_rejection_reason = reason
        order.return_rejected_at = timezone.now()
        order.save()

        order.items.update(return_requested=False)

        messages.success(request, f"Return rejected for order {order.order_id}")
        return redirect('manage_return_requests')

    return render(request, 'admin_panel/reject_return.html', {'order': order})


@staff_member_required
def product_offer_list(request):
    offers = ProductOffer.objects.select_related('product').order_by('-created_at')
    return render(request, 'admin_panel/offer_list.html', {
        'offers': offers,
        'title': 'Product Offers',
        'offer_type': 'product',
        'create_url_name': 'admin:product_offer_create',
        'update_url_name': 'admin:product_offer_update',
        'delete_url_name': 'admin:product_offer_delete',
    })


@staff_member_required
def product_offer_create(request):
    products = Product.objects.filter(is_active=True, is_delete=False).order_by('name')

    if request.method == 'POST':
        try:
            product_id = request.POST.get('product')
            discount_str = request.POST.get('discount_percentage', '').strip()
            active = request.POST.get('active') == 'on'
            valid_from = request.POST.get('valid_from') or None
            valid_until = request.POST.get('valid_until') or None

            if not product_id:
                raise ValidationError("Product is required.")

            product = get_object_or_404(Product, pk=product_id)

            if not discount_str:
                raise ValidationError("Discount percentage is required.")

            discount = Decimal(discount_str)
            if discount < 0 or discount > 100:
                raise ValidationError("Discount must be between 0 and 100.")

            offer = ProductOffer(
                product=product,
                discount_percentage=discount,
                active=active,
                valid_from=valid_from,
                valid_until=valid_until,
            )
            offer.full_clean()  # run model validation
            offer.save()

            messages.success(request, f"Offer created for {product.name} ({discount}%)")
            return redirect('admin:product_offer_list')

        except (ValidationError, InvalidOperation, ValueError) as e:
            messages.error(request, f"Error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'admin_panel/offer_form_manual.html', {
        'title': 'Create Product Offer',
        'products': products,
        'offer_type': 'product',
        'action_url': request.path,
        'back_url': reverse('product_offer_list'),
    })


@staff_member_required
def product_offer_update(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    products = Product.objects.filter(is_active=True, is_delete=False).order_by('name')

    if request.method == 'POST':
        try:
            product_id = request.POST.get('product')
            discount_str = request.POST.get('discount_percentage', '').strip()
            active = request.POST.get('active') == 'on'
            valid_from = request.POST.get('valid_from') or None
            valid_until = request.POST.get('valid_until') or None

            product = get_object_or_404(Product, pk=product_id)

            discount = Decimal(discount_str)
            if discount < 0 or discount > 100:
                raise ValidationError("Discount must be between 0 and 100.")

            offer.product = product
            offer.discount_percentage = discount
            offer.active = active
            offer.valid_from = valid_from
            offer.valid_until = valid_until

            offer.full_clean()
            offer.save()

            messages.success(request, f"Offer updated for {product.name} ({discount}%)")
            return redirect('product_offer_list')

        except (ValidationError, InvalidOperation, ValueError) as e:
            messages.error(request, f"Error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'admin_panel/offer_form_manual.html', {
        'title': 'Edit Product Offer',
        'offer': offer,
        'products': products,
        'offer_type': 'product',
        'action_url': request.path,
        'back_url': reverse('product_offer_list'),
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def product_offer_delete(request, pk):
    try:
        offer = ProductOffer.objects.get(pk=pk)
    except ProductOffer.DoesNotExist:
        messages.error(request, "The product offer you are trying to delete no longer exists.")
        return redirect('product_offer_list')

    if request.method == 'POST':
        product_name = offer.product.name if offer.product else "Unknown product"
        offer.delete()
        messages.warning(request, f"Product offer for {product_name} was deleted.")
        return redirect('product_offer_list')

    # GET → show confirmation
    return render(request, 'admin_panel/offer_confirm_delete.html', {
        'offer': offer,
        'title': 'Delete Product Offer',
        'offer_type': 'product',
        'back_url': reverse('product_offer_list'),
    })


# ─── Category Offers ─────────────────────────────────────────────────────────

@staff_member_required
def category_offer_list(request):
    offers = CategoryOffer.objects.select_related('category').order_by('-created_at')
    return render(request, 'admin_panel/offer_list.html', {
        'offers': offers,
        'title': 'Category Offers',
        'offer_type': 'category',
        'create_url_name': 'admin:category_offer_create',
        'update_url_name': 'admin:category_offer_update',
        'delete_url_name': 'admin:category_offer_delete',
    })


@staff_member_required
def category_offer_create(request):
    categories = Category.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        try:
            category_id = request.POST.get('category')
            discount_str = request.POST.get('discount_percentage', '').strip()
            active = request.POST.get('active') == 'on'
            valid_from = request.POST.get('valid_from') or None
            valid_until = request.POST.get('valid_until') or None

            if not category_id:
                raise ValidationError("Category is required.")

            category = get_object_or_404(Category, pk=category_id)

            if not discount_str:
                raise ValidationError("Discount percentage is required.")

            discount = Decimal(discount_str)
            if discount < 0 or discount > 100:
                raise ValidationError("Discount must be between 0 and 100.")

            offer = CategoryOffer(
                category=category,
                discount_percentage=discount,
                active=active,
                valid_from=valid_from,
                valid_until=valid_until,
            )
            offer.full_clean()
            offer.save()

            messages.success(request, f"Offer created for {category.name} ({discount}%)")
            return redirect('category_offer_list')

        except (ValidationError, InvalidOperation, ValueError) as e:
            messages.error(request, f"Error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'admin_panel/offer_form_manual.html', {
        'title': 'Create Category Offer',
        'categories': categories,
        'offer_type': 'category',
        'action_url': request.path,
        'back_url': reverse('category_offer_list'),
    })


@staff_member_required
def category_offer_update(request, pk):
    offer = get_object_or_404(CategoryOffer, pk=pk)
    categories = Category.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        try:
            category_id = request.POST.get('category')
            discount_str = request.POST.get('discount_percentage', '').strip()
            active = request.POST.get('active') == 'on'
            valid_from = request.POST.get('valid_from') or None
            valid_until = request.POST.get('valid_until') or None

            category = get_object_or_404(Category, pk=category_id)

            discount = Decimal(discount_str)
            if discount < 0 or discount > 100:
                raise ValidationError("Discount must be between 0 and 100.")

            offer.category = category
            offer.discount_percentage = discount
            offer.active = active
            offer.valid_from = valid_from
            offer.valid_until = valid_until

            offer.full_clean()
            offer.save()

            messages.success(request, f"Offer updated for {category.name} ({discount}%)")
            return redirect('admin:category_offer_list')

        except (ValidationError, InvalidOperation, ValueError) as e:
            messages.error(request, f"Error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'admin_panel/offer_form_manual.html', {
        'title': 'Edit Category Offer',
        'offer': offer,
        'categories': categories,
        'offer_type': 'category',
        'action_url': request.path,
        'back_url': reverse('admin:category_offer_list'),
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def category_offer_delete(request, pk):
    try:
        offer = CategoryOffer.objects.get(pk=pk)
    except CategoryOffer.DoesNotExist:
        messages.error(request, "The category offer you are trying to delete no longer exists or was already removed.")
        return redirect('category_offer_list')

    if request.method == 'POST':
        category_name = offer.category.name if offer.category else "Unknown category"
        offer.delete()
        messages.warning(request, f"Category offer for {category_name} was deleted.")
        return redirect('category_offer_list')

    # GET → confirmation page
    return render(request, 'admin_panel/offer_confirm_delete.html', {
        'offer': offer,
        'title': 'Delete Category Offer',
        'offer_type': 'category',
        'back_url': reverse('category_offer_list'),
    })


def approve_return_and_refund( request, queryset):
    for order in queryset.filter(status='return_requested'):
        with transaction.atomic():
            refund_amount = order.grand_total - order.wallet_amount_used  # or full amount
            order.refund_amount = refund_amount
            order.refund_status = 'completed'
            order.status = 'returned'
            order.save()

            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.credit(
                amount=refund_amount,
                description=f"Refund for returned order #{order.order_id}",
                related_order=order
            )

            messages.success(request, f"Return approved and ₹{refund_amount} refunded to wallet for order #{order.order_id}")
@login_required
@staff_member_required
def coupon_list(request):
    # Get all coupons (newest first)
    coupons = Coupon.objects.all().order_by('-valid_from')
    print("Total coupons in database:", coupons.count())     # ← check this in terminal
    print("Coupon codes:", [c.code for c in coupons])
    # Optional: simple search
    query = request.GET.get('q')
    if query:
        coupons = coupons.filter(code__icontains=query)

    # Pagination - 10 coupons per page (you can change number)
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # print("Coupons on this page:", page_obj.object_list.count())
    context = {
        'page_obj': page_obj,          # This name must match your template
        'query': query,                # For keeping search after pagination
    }

    return render(request, 'admin_panel/coupon_list.html', context)
@login_required
@staff_member_required
def coupon_form(request):
    if request.method == 'POST':
        try:
            code = request.POST.get('code', '').strip().upper()
            if not code:
                messages.error(request, "Coupon code is required")
                return redirect('coupon_list')

            # Check if code already exists
            if Coupon.objects.filter(code=code).exists():
                messages.error(request, f"Coupon code '{code}' already exists")
                return redirect('coupon_list')

            # Get values with defaults
            discount_percentage = int(request.POST.get('discount_percentage', 0))
            discount_amount = Decimal(request.POST.get('discount_amount', '0.00'))
            min_purchase = Decimal(request.POST.get('min_purchase_amount', '0.00'))
            max_discount = request.POST.get('max_discount_amount', None)
            if max_discount:
                max_discount = Decimal(max_discount)
            
            valid_from_str = request.POST.get('valid_from')
            valid_until_str = request.POST.get('valid_until')
            
            valid_from = timezone.now()
            valid_until = None
            
            if valid_from_str:
                from datetime import datetime
                valid_from = datetime.fromisoformat(valid_from_str)
            
            if valid_until_str:
                valid_until = datetime.fromisoformat(valid_until_str)

            usage_limit = int(request.POST.get('usage_limit', 0))
            is_one_time = request.POST.get('is_one_time_per_user') == 'on'
            active = request.POST.get('active') == 'on'

            # Create the coupon
            coupon = Coupon.objects.create(
                code=code,
                discount_percentage=discount_percentage,
                discount_amount=discount_amount,
                min_purchase_amount=min_purchase,
                max_discount_amount=max_discount,
                valid_from=valid_from,
                valid_until=valid_until,
                usage_limit=usage_limit,
                is_one_time_per_user=is_one_time,
                active=active,
            )

            messages.success(request, f"Coupon '{coupon.code}' created successfully!")
            return redirect('coupon_list')  # or 'admin:coupon_list' or your list view

        except Exception as e:
            messages.error(request, f"Error creating coupon: {str(e)}")
            return redirect('coupon_form')

    # GET request → show empty form
    return render(request, 'admin_panel/coupon_form.html', {
        'title': 'Create New Coupon'
    })
@login_required

def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':  # better to use POST for destructive actions
        coupon.delete()
        messages.success(request, f"Coupon '{coupon.code}' has been permanently deleted.")
        return redirect('coupon_list')
    
    # Optional: show confirmation page
    return render(request, 'admin_panel/confirm_delete.html', {
        'object': coupon,
        'object_type': 'Coupon',
        'back_url': 'coupon_list',
    })

def coupon_edit(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)

    if request.method == 'POST':
        try:
            # Get values from POST
            code = request.POST.get('code', '').strip().upper()
            if not code:
                messages.error(request, "Coupon code is required")
                return redirect('coupon_edit', pk=pk)

            # Prevent changing to an existing code (except itself)
            if Coupon.objects.filter(code=code).exclude(pk=pk).exists():
                messages.error(request, f"Coupon code '{code}' is already used by another coupon")
                return redirect('coupon_edit', pk=pk)

            discount_percentage = int(request.POST.get('discount_percentage', 0))
            discount_amount = Decimal(request.POST.get('discount_amount', '0.00'))
            min_purchase_amount = Decimal(request.POST.get('min_purchase_amount', '0.00'))
            max_discount_amount_str = request.POST.get('max_discount_amount', '')
            max_discount_amount = Decimal(max_discount_amount_str) if max_discount_amount_str else None

            valid_from_str = request.POST.get('valid_from')
            valid_until_str = request.POST.get('valid_until')

            valid_from = coupon.valid_from  # keep existing if not changed
            if valid_from_str:
                from datetime import datetime
                valid_from = datetime.fromisoformat(valid_from_str)

            valid_until = coupon.valid_until
            if valid_until_str:
                valid_until = datetime.fromisoformat(valid_until_str)

            usage_limit = int(request.POST.get('usage_limit', coupon.usage_limit))
            is_one_time_per_user = request.POST.get('is_one_time_per_user') == 'on'
            active = request.POST.get('active') == 'on'

            # Update the coupon
            coupon.code = code
            coupon.discount_percentage = discount_percentage
            coupon.discount_amount = discount_amount
            coupon.min_purchase_amount = min_purchase_amount
            coupon.max_discount_amount = max_discount_amount
            coupon.valid_from = valid_from
            coupon.valid_until = valid_until
            coupon.usage_limit = usage_limit
            coupon.is_one_time_per_user = is_one_time_per_user
            coupon.active = active

            coupon.save()

            messages.success(request, f"Coupon '{coupon.code}' updated successfully!")
            return redirect('coupon_list')

        except Exception as e:
            messages.error(request, f"Error updating coupon: {str(e)}")
            # fall through to show form again with entered values

    # GET request or error → show form with current values
    context = {
        'title': 'Edit Coupon',
        'coupon': coupon,
        # Pass current values so they appear in inputs
        'code': coupon.code,
        'discount_percentage': coupon.discount_percentage,
        'discount_amount': coupon.discount_amount,
        'min_purchase_amount': coupon.min_purchase_amount,
        'max_discount_amount': coupon.max_discount_amount or '',
        'valid_from': coupon.valid_from.strftime('%Y-%m-%dT%H:%M') if coupon.valid_from else '',
        'valid_until': coupon.valid_until.strftime('%Y-%m-%dT%H:%M') if coupon.valid_until else '',
        'usage_limit': coupon.usage_limit,
        'is_one_time_per_user': coupon.is_one_time_per_user,
        'active': coupon.active,
    }

    return render(request, 'admin_panel/coupon_form.html', context)

def coupon_toggle_status(request, coupon_id, action):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if action == 'activate':
        coupon.active = True
        msg = f"Coupon '{coupon.code}' is now active."
    elif action == 'deactivate':
        coupon.active = False
        msg = f"Coupon '{coupon.code}' is now inactive."
    else:
        messages.error(request, "Invalid action.")
        return redirect('coupon_list')

    coupon.save()
    messages.success(request, msg)
    
    return redirect('coupon_list')

def coupon_deactivate(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.active = False
    coupon.save()
    messages.success(request, f"Coupon '{coupon.code}' deactivated.")
    return redirect('coupon_list')


def coupon_activate(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.active = True
    coupon.save()
    messages.success(request, f"Coupon '{coupon.code}' activated.")
    return redirect('coupon_list')