from django.urls import path
from . import views



urlpatterns = [
    path('',views.AdminLoginView.as_view(),name='admin_login'),
    path('admin/logout/',views.admin_logout,name='admin_logout'),
    path('admin/dashboard/',views.admin_dashboard,name='admin_dashboard'),
    path('admin/user',views.user_management,name='user_management'),
    path('block-user/<int:user_id>/',views.block_user,name='block_user'),
    path('unblock-user/<int:user_id>/',views.unblock_user,name='unblock_user'),
    path('admin/categories',views.category_management,name='category_management'),
    path('admin/add-categories',views.add_category,name='add_category'),
    path('admin/edit-categories/<int:cat_id>/',views.edit_category,name='edit_category'),
    path('admin/delete-categories/<int:cat_id>/',views.delete_category,name='delete_category'),
    path('softdelete_category/<int:cat_id>/',views.softdelete_category,name='softdelete_category'),
    path('softreturn_category/<int:cat_id>/',views.softreturn_category,name='softreturn_category'),
    path('admin/products/',views.product_management,name='product_management'),
    path('admin/add-product',views.add_product,name='add_product'),
    path('admin/edit_product/<int:prod_id>',views.edit_product,name='edit_product'),
    path('admin/delet-product/<int:prod_id>',views.delete_product,name='delete_product'),
    path('softdelete_product/<int:prod_id>/',views.softdelete_product,name='softdelete_product'),
    path('softreturn_product/<int:prod_id>/',views.softreturn_product,name='softreturn_product'), 
    path('admin/delete-product-variant/<int:prod_id>/<str:size>/',views.delete_product_variant,name='delete_product_variant'),
    path('softdelete_product_variant/<int:prod_id>/<str:size>/',views.softdelete_product_variant,name='softdelete_product_variant'),
    path('softreturn_product_variant/<int:prod_id>/<str:size>/',views.softreturn_product_variant,name='softreturn_product_variant'),
    path('admin_orders/', views.order_list, name='order_management'),
    path('update-order-status/<int:pk>/', views.update_order_status, name='update_order_status'),
    path('cancel_order/<int:pk>/', views.cancel_order, name='cancel_order'),
    path('returns/', views.manage_return_requests, name='manage_return_requests'),
    path('return/approve/<int:order_id>/', views.approve_return, name='approve_return'),
    path('return/reject/<int:order_id>/', views.reject_return, name='reject_return'),
    path('orders/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),
    
    path('offers/product/', views.product_offer_list, name='product_offer_list'),
    path('offers/product/create/', views.product_offer_create, name='product_offer_create'),
    path('offers/product/<int:pk>/update/', views.product_offer_update, name='product_offer_update'),
    path('offers/product/<int:pk>/delete/', views.product_offer_delete, name='product_offer_delete'),

    # Category Offers
    path('offers/category/', views.category_offer_list, name='category_offer_list'),
    path('offers/category/create/', views.category_offer_create, name='category_offer_create'),
    path('offers/category/<int:pk>/update/', views.category_offer_update, name='category_offer_update'),
    path('offers/category/<int:pk>/delete/', views.category_offer_delete, name='category_offer_delete'),
    path('coupon/',views.coupon_form,name='coupon_form'),
    path('admin/coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/delete/<int:coupon_id>/', views.coupon_delete, name='coupon_delete'),
    path('admin/coupons/edit/<int:pk>/', views.coupon_edit, name='coupon_edit'),
    path('admin/coupons/status/<int:coupon_id>/<str:action>/', views.coupon_toggle_status,name='coupon_status_toggle'),
    path('admin/coupons/deactivate/<int:coupon_id>/', views.coupon_deactivate, name='deactivate_coupon'),
    path('admin/coupons/activate/<int:coupon_id>/', views.coupon_activate, name='activate_coupon'),
]
