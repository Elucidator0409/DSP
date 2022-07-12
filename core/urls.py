from django.urls import path
from .views import (
    HomeView, CheckoutView, ItemDetailView, add_to_cart, remove_from_cart,
    OrderSummaryView, remove_single_from_cart, add_single_to_cart,
    PaymentView, AddCouponView
)

app_name = 'core'
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order_summary/', OrderSummaryView.as_view(), name='order_summary'),
    path('product/<slug>', ItemDetailView.as_view(), name='product'),
    path('add_to_cart/<slug>', add_to_cart, name='add_to_cart'),
    path('add_coupon/', AddCouponView.as_view(), name='add_coupon'),
    path('remove_from_cart/<slug>', remove_from_cart, name='remove_from_cart'),
    path('remove_item_from_cart/<slug>', remove_single_from_cart,
         name='remove_single_from_cart'),
    path('add_item_to_cart/<slug>', add_single_to_cart,
         name='add_single_to_cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment')

]
