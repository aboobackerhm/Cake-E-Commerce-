# admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Min, Count
from .models import (
    CustomUser, Category, Product, ProductImage,
    ProductVariant, Order, OrderItem, Address,
    ProductReview, CartItem, WishlistItem,Coupon
)

# 1. USER
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "phone", "is_staff", "date_joined")
    search_fields = ("username", "email", "phone")
    list_filter = ("is_staff", "is_active")


# 2. CATEGORY
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


# 3. PRODUCT & IMAGES (with inline)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "order", "alt_text", "image_preview")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:60px;"/>', obj.image.url)
        return "(no image)"
    image_preview.short_description = "Preview"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "min_price", "total_stock", "is_active", "created_at")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _min_price=Min("variants__price"),
            _total_stock=Count("variants")
        )

    def min_price(self, obj):
        return obj._min_price
    min_price.short_description = "Min Price"

    def total_stock(self, obj):
        total = sum(v.stock for v in obj.variants.all())
        return f"{total} units"
    total_stock.short_description = "Stock"


# 4. PRODUCT VARIANT – STOCK MANAGEMENT

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "price", "stock", "is_active", "updated_at")
    list_filter = ("size", "is_active", "product__category")
    search_fields = ("product__name", "size")
    list_editable = ("stock", "price", "is_active")
    ordering = ("product__name", "size")
    list_per_page = 50

    def stock(self, obj):
        color = "green" if obj.stock >= 10 else "orange" if obj.stock > 0 else "red"
        return format_html('<b style="color:{};">{}</b>', color, obj.stock)
    stock.short_description = "Stock"
    stock.admin_order_field = "stock"


# 5. ORDER MANAGEMENT (MAIN FEATURE)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("variant", "quantity", "price", "total", "is_returned")
    readonly_fields = ("total",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id_link", "user_link", "total_amount", "status",
        "payment_method", "created_at", "view_btn"
    )
    list_filter = (
        "status", "payment_method", "created_at",
        "address__city", "address__state"
    )
    search_fields = (
        "order_id", "user__username", "user__email",
        "address__full_name", "address__phone"
    )
    readonly_fields = ("order_id", "created_at", "updates_at")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    actions = ["mark_shipped", "mark_delivered", "mark_cancelled"]

    fieldsets = (
        (None, {
            "fields": ("order_id", "user", "address", "status", "payment_method")
        }),
        ("Money", {
            "fields": ("total_amount", "discount", "tax", "shipping")
        }),
        ("Reasons", {
            "fields": ("cancel_reason", "return_reason")
        }),
        ("Dates", {
            "fields": ("created_at", "updates_at"),
            "classes": ("collapse",)
        }),
    )

    # ---- Custom columns ----
    def order_id_link(self, obj):
        url = reverse("admin:%s_%s_change" % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order_id)
    order_id_link.short_description = "Order ID"

    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"

    def view_btn(self, obj):
        url = reverse("admin:%s_%s_change" % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk])
        return format_html('<a class="button" href="{}">View</a>', url)
    view_btn.short_description = "Detail"

    # ---- Bulk status actions ----
    def mark_shipped(self, request, queryset):
        updated = queryset.update(status="shipped")
        self.message_user(request, f"{updated} order(s) → Shipped")
    mark_shipped.short_description = "Mark as Shipped"

    def mark_delivered(self, request, queryset):
        updated = queryset.update(status="delivered")
        self.message_user(request, f"{updated} order(s) → Delivered")
    mark_delivered.short_description = "Mark as Delivered"

    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} order(s) → Cancelled")
    mark_cancelled.short_description = "Mark as Cancelled"

    # ---- Clear search link ----
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        if request.GET.get("q"):
            clear_url = reverse("admin:%s_%s_changelist" % (self.opts.app_label, self.opts.model_name))
            extra_context["clear_search_url"] = clear_url
        return super().changelist_view(request, extra_context=extra_context)


# ----------------------------------------------------------------------
# 6. OTHER MODELS (optional – keep them clean)
# ----------------------------------------------------------------------
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "city", "is_default")
    list_filter = ("is_default", "city")
    search_fields = ("user__username", "full_name")


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "variant", "quantity", "total_price")
    search_fields = ("user__username", "variant__product__name")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product")
    search_fields = ("user__username", "product__name")

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_percentage',
        'discount_amount',
        'min_purchase_amount',
        'max_discount_amount',
        'valid_from',
        'valid_until',
        'usage_limit',
        'used_count',
        'active',
        'is_one_time_per_user',
    )
    
    list_filter = (
        'active',
        'is_one_time_per_user',
        'valid_from',
        'valid_until',
    )
    
    search_fields = ('code',)
    
    readonly_fields = ('used_count',)  # if you add created_at field later
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'code',
                'active',
            )
        }),
        ('Discount Type', {
            'fields': (
                'discount_percentage',
                'discount_amount',
                ('min_purchase_amount', 'max_discount_amount'),
            ),
            'description': 'Fill either percentage OR fixed amount — not both.'
        }),
        ('Validity & Usage', {
            'fields': (
                ('valid_from', 'valid_until'),
                ('usage_limit', 'used_count'),
                'is_one_time_per_user',
            )
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        # Optional: prevent changing code after creation
        if obj:  # editing existing coupon
            return self.readonly_fields + ('code',)
        return self.readonly_fields