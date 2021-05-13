from decimal import Decimal
from django.conf import settings
from shop.models import Product
from coupons.models import Coupon


class Cart(object):
    """ Manage shopping cart. """

    def __init__(self, request):
        """
        Initialize the cart.
        """
        # store the current session
        self.session = request.session
        # try to get the cart from th current user session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
        # store current applied coupon
        self.coupon_id = self.session.get('coupon_id')

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products
        from the database.
        """
        # Retrieve the product instances using their keys
        product_ids = self.cart.keys()
        # get the product objects and add them to the cart
        products = Product.objects.filter(id__in=product_ids)
        # copy the current cart and add products to it
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            # convert each item price back to decimal
            item['price'] = Decimal(item['price'])
            # adds a total price attribute to each item
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        # reeturn the sum of  the quantities of all items in thee cart
        return sum(item['quantity'] for item in self.cart.values())

    def add(self, product, quantity=1, override_quantity=False):
        """
        Add a product to the cart or update its quantity.
        params:
            product:  The product instance to add or update in the cart.
            quantity: An optional integer with the product quantity.
            override_quantity: A Boolean that indicates whether the quantity
              needs to be overridden with the given quantity (True), or if the
              new quantity has to be added to the existing quantity (False).
        """
        product_id = str(product.id)  # Serialize to JSON
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0,
                                     'price': str(product.price)}
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        # mark the session as "modified" to make sure it gets saved
        self.session.modified = True

    def remove(self, product):
        """
        Remove a product from the cart.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def get_total_price(self):
        # calculate the total costs of all items in the cart
        return sum(Decimal(item['price']) * item['quantity']
                   for item in self.cart.values())

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                pass
        return None

    def get_discount(self):
        if self.coupon:
            return (self.coupon.discount / Decimal(100)) \
                * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()
