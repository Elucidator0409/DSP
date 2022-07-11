from django.conf import settings
from calendar import c
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from .models import Item, Order, OrderItem, BillingAddress, Payment
from .forms import CheckoutForm
# Create your views here.

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutView(View):
    def get(self, *args, **kwargs):
        # form
        form = CheckoutForm()
        context = {
            'form': form
        }
        return render(self.request, "checkout.html", context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data['street_address']
                apartment_address = form.cleaned_data['apartment_address']
                country = form.cleaned_data['country']

                zip = form.cleaned_data['zip']
                # same_shipping_address = form.cleaned_data('same_billing_address')
                # save_info = form.cleaned_data('save_info')
                payment_option = form.cleaned_data['payment_option']
                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected"
                    )
                return redirect("core:checkout")
            messages.warning(self.request, "Failed checkout")
            return redirect("core:checkout")

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have any order!")
            return redirect('"core:order_summary"')


class PaymentView(View):
    def get(self, *args, **kwargs):
        # order
        order = Order.objects.get(user=self.request.user, ordered=False)
        context = {
            'order': order
        }
        return render(self.request, 'payment.html', context)

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)
        try:
            charge = stripe.Charge.create(
                source=token,
                amount=amount,  # cent
                currency='usd',
            )
            # create payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign the payment to order

            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Your order was successful!")
            return redirect("core:home")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect("core:home")

        except stripe.error.InvalidRequestError as e:
            messages.error(self.request, "InvalidRequestError")
            return redirect("core:home")

        except stripe.error.RareLimitError as e:
            messages.error(self.request, "RareLimitError")
            return redirect("core:home")

        except stripe.error.AuthenticationError as e:
            messages.error(self.request, "Not authenticated")
            return redirect("core:home")

        except stripe.error.APIConnectionError as e:
            messages.error(self.request, "Network error")
            return redirect("core:home")

        except stripe.error.StripeError as e:
            messages.error(self.request, "Please try again")
            return redirect("core:home")

        except Exception as e:
            messages.error(
                self.request, "A serious  error occurred. We have been notified.")
            return redirect("core:home")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have any order!")
            return redirect('/')


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.item.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item was updated")
            return redirect("core:product", slug=slug)

        else:
            order.item.add(order_item)
            messages.info(request, "This item was added to your cart")
            return redirect("core:product", slug=slug)

    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.item.add(order_item)
        messages.info(request, "This item was added to your cart")

        return redirect("core:product", slug=slug)


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.item.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]

            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                messages.info(request, "This card was removed from your cart")
                return redirect("core:product", slug=slug)
            # if only 1, then delete the item from the cart.
            else:
                order_item.delete()
                messages.info(request, "Your cart is now empty")
                return redirect("core:product", slug=slug)

        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)

    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)

    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.item.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]

            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                messages.info(request, "This card was removed from your cart")
                return redirect("core:order_summary")
            # if only 1, then delete the item from the cart.
            else:
                order_item.delete()
                messages.info(request, "Your cart is now empty")
                return redirect("core:order_summary")

        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:order_summary")

    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:order_summary")


@login_required
def add_single_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.item.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item was updated")
            return redirect("core:order_summary")

        else:
            order.item.add(order_item)
            messages.info(request, "This item was added to your cart")
            return redirect("core:order_summary")

    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.item.add(order_item)
        messages.info(request, "This item was added to your cart")

        return redirect("core:order_summary")
