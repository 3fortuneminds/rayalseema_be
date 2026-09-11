"""
Seeds the database with the demo accounts + sample data every API needs to
show something real instead of an empty state.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --flush   # wipe previously seeded demo data first, then reseed

Idempotent: safe to run repeatedly. Existing rows are matched and updated
rather than duplicated, and the four required accounts always end up with
the password below regardless of what they had before.
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User, UserRole
from addresses.models import Address
from coupons.models import Coupon, DiscountType
from core.services import log_action
from delivery.models import AssignmentStatus, DeliveryAssignment, DeliveryPartner, VehicleType
from foods.models import Food, FoodCategory, FoodVariant
from notifications.models import Notification, NotificationType
from orders.models import Order, OrderItem, OrderPaymentStatus, OrderStatus
from payments.models import Payment, PaymentStatus
from restaurants.models import OpeningHours, Restaurant, RestaurantCategory
from reviews.models import Review
from tracking.models import LocationUpdate

PASSWORD = "Password@123"

REQUIRED_EMAILS = [
    "user1@yopmail.com",
    "restaurant1@yopmail.com",
    "delivery1@yopmail.com",
    "admin1@yopmail.com",
]
FILLER_RESTAURANT_NAMES = ["Andhra Ruchulu", "Coastal Curry House"]
COUPON_CODE = "WELCOME50"


class Command(BaseCommand):
    help = "Seed demo users (customer/restaurant/delivery/admin) and sample data across every API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data (the required accounts and everything that "
            "cascades from them, plus the filler restaurants/coupon) before reseeding.",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options["flush"]:
                self._flush()
            self._run()
        self.stdout.write(self.style.SUCCESS("\nSeed complete. Demo logins (password for all: Password@123):"))
        for email in REQUIRED_EMAILS:
            self.stdout.write(f"  {email}")

    # ---------- flush ----------

    def _flush(self):
        self.stdout.write("Flushing previously seeded demo data...")
        users = User.objects.filter(email__in=REQUIRED_EMAILS)
        # Order.restaurant is PROTECT, so any order touching the seeded restaurant
        # (or placed by the seeded customer) must go before the Restaurant/User rows do.
        Order.objects.filter(restaurant__owner__in=users).delete()
        Order.objects.filter(user__in=users).delete()
        Restaurant.objects.filter(name__in=FILLER_RESTAURANT_NAMES).delete()
        Coupon.objects.filter(code=COUPON_CODE).delete()
        users.delete()

    # ---------- main ----------

    def _run(self):
        customer = self._seed_user("user1@yopmail.com", UserRole.CUSTOMER, "Demo Customer", "9876543210")
        owner = self._seed_user("restaurant1@yopmail.com", UserRole.RESTAURANT, "Restaurant One Owner", "9876543211")
        delivery_user = self._seed_user("delivery1@yopmail.com", UserRole.DELIVERY, "Delivery One", "9876543212")
        admin = self._seed_user(
            "admin1@yopmail.com", UserRole.ADMIN, "Platform Admin", "9876543213", is_staff=True, is_superuser=True
        )
        self.stdout.write(self.style.SUCCESS("Users ready."))

        home, work = self._seed_addresses(customer)
        self.stdout.write(self.style.SUCCESS("Addresses ready."))

        restaurant, foods = self._seed_restaurant(owner)
        self._seed_filler_restaurants()
        self.stdout.write(self.style.SUCCESS("Restaurants + menu ready."))

        partner = self._seed_delivery_partner(delivery_user)
        self.stdout.write(self.style.SUCCESS("Delivery partner ready."))

        coupon = self._seed_coupon()
        self.stdout.write(self.style.SUCCESS("Coupon ready."))

        delivered_order, active_order, placed_order, cancelled_order = self._seed_orders(
            customer, restaurant, foods, home, work, partner, coupon
        )
        self.stdout.write(self.style.SUCCESS("Orders, payments, deliveries, and a review ready."))

        self._seed_notifications(customer, owner, delivery_user, delivered_order, active_order, placed_order)
        self.stdout.write(self.style.SUCCESS("Notifications ready."))

        self._seed_audit_log(admin, restaurant, partner, cancelled_order)
        self.stdout.write(self.style.SUCCESS("Audit log ready."))

    # ---------- users ----------

    def _seed_user(self, email, role, full_name, phone, is_staff=False, is_superuser=False):
        user, _ = User.objects.get_or_create(email=email, defaults={"role": role})
        user.role = role
        user.full_name = full_name
        user.phone_number = phone
        user.is_verified = True
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(PASSWORD)
        user.save()
        return user

    def _seed_addresses(self, customer):
        home, _ = Address.objects.get_or_create(
            user=customer,
            label="Home",
            defaults={
                "line1": "45 Lake View Colony",
                "line2": "Near City Park",
                "city": "Kadapa",
                "state": "Andhra Pradesh",
                "postal_code": "516001",
                "country": "India",
                "latitude": Decimal("14.4700"),
                "longitude": Decimal("78.8200"),
                "is_default": True,
            },
        )
        work, _ = Address.objects.get_or_create(
            user=customer,
            label="Work",
            defaults={
                "line1": "8 Tech Park Road",
                "city": "Kadapa",
                "state": "Andhra Pradesh",
                "postal_code": "516002",
                "country": "India",
                "latitude": Decimal("14.4750"),
                "longitude": Decimal("78.8300"),
                "is_default": False,
            },
        )
        return home, work

    # ---------- restaurant + menu ----------

    def _seed_restaurant(self, owner):
        restaurant, _ = Restaurant.objects.get_or_create(
            owner=owner,
            defaults={
                "name": "Rayalseema Spice Kitchen",
                "description": "Authentic Rayalseema cuisine, fiery curries, tamarind rice, and slow-cooked mutton.",
                "address_line": "12 MG Road",
                "city": "Kadapa",
                "latitude": Decimal("14.4674"),
                "longitude": Decimal("78.8241"),
            },
        )
        restaurant.is_approved = True
        restaurant.is_active = True
        restaurant.save()

        biryani_cat, _ = RestaurantCategory.objects.get_or_create(name="Biryani", defaults={"icon": "🍛"})
        south_indian_cat, _ = RestaurantCategory.objects.get_or_create(name="South Indian", defaults={"icon": "🥘"})
        restaurant.categories.add(biryani_cat, south_indian_cat)

        hours = [
            (0, "10:00", "22:30"), (1, "10:00", "22:30"), (2, "10:00", "22:30"),
            (3, "10:00", "22:30"), (4, "10:00", "23:00"), (5, "10:00", "23:00"), (6, "11:00", "22:00"),
        ]
        for weekday, opens, closes in hours:
            OpeningHours.objects.get_or_create(
                restaurant=restaurant, weekday=weekday,
                defaults={"opens_at": opens, "closes_at": closes, "is_closed": False},
            )

        starters, _ = FoodCategory.objects.get_or_create(restaurant=restaurant, name="Starters", defaults={"display_order": 1})
        mains, _ = FoodCategory.objects.get_or_create(restaurant=restaurant, name="Mains", defaults={"display_order": 2})
        biryanis, _ = FoodCategory.objects.get_or_create(restaurant=restaurant, name="Biryani", defaults={"display_order": 3})
        desserts, _ = FoodCategory.objects.get_or_create(restaurant=restaurant, name="Desserts", defaults={"display_order": 4})

        menu = [
            (starters, "Guntur Chilli Chicken", "Fiery double-fried chicken tossed with Guntur chillies.", "249.00", False, None),
            (starters, "Paneer Tikka", "Grilled cottage cheese with spices.", "199.00", True, None),
            (mains, "Natu Kodi Pulusu", "Free-range chicken curry, Rayalseema style.", "329.00", False, None),
            (mains, "Gongura Mutton", "Slow-cooked mutton with sorrel leaves.", "399.00", False, None),
            (biryanis, "Chicken Biryani", "Layered basmati rice with spiced chicken.", "249.00", False, [("Half", "249.00"), ("Full", "429.00")]),
            (biryanis, "Veg Biryani", "Layered basmati rice with mixed vegetables.", "199.00", True, [("Half", "199.00"), ("Full", "349.00")]),
            (desserts, "Bobbatlu", "Sweet flatbread stuffed with jaggery and lentils.", "89.00", True, None),
        ]
        foods = {}
        for category, name, desc, price, is_veg, variants in menu:
            food, _ = Food.objects.get_or_create(
                restaurant=restaurant, name=name,
                defaults={
                    "category": category, "description": desc, "base_price": Decimal(price),
                    "is_vegetarian": is_veg, "is_available": True,
                },
            )
            variant_objs = []
            if variants:
                for i, (vname, vprice) in enumerate(variants):
                    variant, _ = FoodVariant.objects.get_or_create(
                        food=food, name=vname, defaults={"price": Decimal(vprice), "is_default": i == 0}
                    )
                    variant_objs.append(variant)
            foods[name] = {"food": food, "variants": variant_objs}

        return restaurant, foods

    def _seed_filler_restaurants(self):
        south_indian_cat, _ = RestaurantCategory.objects.get_or_create(name="South Indian", defaults={"icon": "🥘"})
        chinese_cat, _ = RestaurantCategory.objects.get_or_create(name="Chinese", defaults={"icon": "🥡"})
        desserts_cat, _ = RestaurantCategory.objects.get_or_create(name="Desserts", defaults={"icon": "🍰"})

        fillers = [
            ("Andhra Ruchulu", "Traditional Andhra thalis and tiffins.", "Kurnool", [south_indian_cat]),
            ("Coastal Curry House", "Seafood and coastal Andhra specialities.", "Anantapur", [chinese_cat, desserts_cat]),
        ]
        for name, desc, city, categories in fillers:
            restaurant, _ = Restaurant.objects.get_or_create(
                name=name, owner=None,
                defaults={"description": desc, "city": city, "is_approved": True, "is_active": True},
            )
            restaurant.is_approved = True
            restaurant.is_active = True
            restaurant.save()
            restaurant.categories.add(*categories)
            menu, _ = FoodCategory.objects.get_or_create(restaurant=restaurant, name="Popular", defaults={"display_order": 1})
            Food.objects.get_or_create(
                restaurant=restaurant, name=f"{name} Special Thali",
                defaults={"category": menu, "description": "Chef's daily special.", "base_price": Decimal("229.00"), "is_vegetarian": True},
            )

    # ---------- delivery partner ----------

    def _seed_delivery_partner(self, delivery_user):
        partner, _ = DeliveryPartner.objects.get_or_create(
            user=delivery_user,
            defaults={"vehicle_type": VehicleType.BIKE, "vehicle_number": "AP01AB1234", "license_number": "DL1234567890"},
        )
        partner.is_approved = True
        partner.is_active = True
        partner.is_online = True
        partner.save()
        return partner

    # ---------- coupon ----------

    def _seed_coupon(self):
        coupon, _ = Coupon.objects.get_or_create(
            code=COUPON_CODE,
            defaults={
                "description": "50% off up to Rs.100 on your first order",
                "discount_type": DiscountType.PERCENTAGE,
                "discount_value": Decimal("50.00"),
                "max_discount_amount": Decimal("100.00"),
                "min_order_amount": Decimal("199.00"),
                "usage_limit": 1000,
                "per_user_limit": 1,
                "valid_from": timezone.now() - timedelta(days=30),
                "valid_until": timezone.now() + timedelta(days=365),
                "is_active": True,
            },
        )
        return coupon

    # ---------- orders (one per interesting status) ----------

    def _make_order(self, stub_id, user, restaurant, address, line_items, status, payment_status, days_ago, coupon=None, discount=Decimal("0")):
        # idempotency anchor: each demo order is tied 1:1 to a stable stub payment id,
        # so re-running the seed command without --flush reuses the existing order
        # instead of creating a duplicate.
        existing = Payment.objects.filter(razorpay_order_id=stub_id).select_related("order").first()
        if existing:
            return existing.order

        delivery_fee = Decimal(str(settings.DELIVERY_FLAT_FEE))
        subtotal = sum((price * qty for _, price, qty, _ in line_items), Decimal("0"))
        total = subtotal + delivery_fee - discount

        order = Order.objects.create(
            user=user,
            restaurant=restaurant,
            coupon=coupon,
            address_label=address.label,
            address_line1=address.line1,
            address_line2=address.line2,
            address_city=address.city,
            address_state=address.state,
            address_postal_code=address.postal_code,
            latitude=address.latitude,
            longitude=address.longitude,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            discount_amount=discount,
            total_amount=total,
            status=status,
            payment_status=payment_status,
        )
        placed_at = timezone.now() - timedelta(days=days_ago)
        Order.objects.filter(pk=order.pk).update(placed_at=placed_at, updated_at=timezone.now() - timedelta(days=max(days_ago - 0.01, 0)))
        order.refresh_from_db()

        for food, price, qty, variant in line_items:
            OrderItem.objects.create(
                order=order,
                food=food,
                variant=variant,
                food_name=food.name,
                variant_name=variant.name if variant else "",
                unit_price=price,
                quantity=qty,
                line_total=price * qty,
            )
        return order

    def _seed_orders(self, customer, restaurant, foods, home, work, partner, coupon):
        chicken_biryani = foods["Chicken Biryani"]
        veg_biryani = foods["Veg Biryani"]
        guntur_chilli = foods["Guntur Chilli Chicken"]
        bobbatlu = foods["Bobbatlu"]
        paneer_tikka = foods["Paneer Tikka"]
        natu_kodi = foods["Natu Kodi Pulusu"]

        chicken_biryani_full = next(v for v in chicken_biryani["variants"] if v.name == "Full")
        veg_biryani_half = next(v for v in veg_biryani["variants"] if v.name == "Half")

        # 1. Delivered, paid, reviewed — 5 days ago
        delivered_order = self._make_order(
            "order_stub_delivered",
            customer, restaurant, home,
            [
                (chicken_biryani["food"], chicken_biryani_full.price, 2, chicken_biryani_full),
                (guntur_chilli["food"], guntur_chilli["food"].base_price, 1, None),
            ],
            OrderStatus.DELIVERED, OrderPaymentStatus.PAID, days_ago=5,
        )
        Payment.objects.get_or_create(
            order=delivered_order,
            defaults={
                "razorpay_order_id": "order_stub_delivered", "razorpay_payment_id": "pay_stub_delivered",
                "amount": delivered_order.total_amount, "status": PaymentStatus.SUCCESS, "is_stub": True,
            },
        )
        assignment = DeliveryAssignment.objects.get_or_create(
            order=delivered_order,
            defaults={
                "delivery_partner": partner,
                "status": AssignmentStatus.DELIVERED,
                "earning_amount": Decimal(str(settings.DELIVERY_PARTNER_EARNING_PER_ORDER)),
            },
        )[0]
        now = timezone.now()
        DeliveryAssignment.objects.filter(pk=assignment.pk).update(
            assigned_at=now - timedelta(days=5, minutes=45),
            picked_up_at=now - timedelta(days=5, minutes=30),
            delivered_at=now - timedelta(days=5, minutes=5),
        )
        Review.objects.get_or_create(
            order=delivered_order,
            defaults={
                "user": customer, "restaurant": restaurant, "rating": 5,
                "comment": "Great taste and careful packaging. The biryani was perfectly spiced!",
            },
        )

        # 2. Out for delivery, paid, live tracking pings — right now
        active_order = self._make_order(
            "order_stub_active",
            customer, restaurant, work,
            [
                (veg_biryani["food"], veg_biryani_half.price, 1, veg_biryani_half),
                (bobbatlu["food"], bobbatlu["food"].base_price, 2, None),
            ],
            OrderStatus.OUT_FOR_DELIVERY, OrderPaymentStatus.PAID, days_ago=0,
        )
        Payment.objects.get_or_create(
            order=active_order,
            defaults={
                "razorpay_order_id": "order_stub_active", "razorpay_payment_id": "pay_stub_active",
                "amount": active_order.total_amount, "status": PaymentStatus.SUCCESS, "is_stub": True,
            },
        )
        active_assignment = DeliveryAssignment.objects.get_or_create(
            order=active_order,
            defaults={
                "delivery_partner": partner,
                "status": AssignmentStatus.PICKED_UP,
                "earning_amount": Decimal(str(settings.DELIVERY_PARTNER_EARNING_PER_ORDER)),
            },
        )[0]
        DeliveryAssignment.objects.filter(pk=active_assignment.pk).update(
            assigned_at=now - timedelta(minutes=25), picked_up_at=now - timedelta(minutes=15),
        )
        route = [
            (Decimal("14.4674"), Decimal("78.8241")),
            (Decimal("14.4700"), Decimal("78.8260")),
            (Decimal("14.4730"), Decimal("78.8280")),
            (Decimal("14.4750"), Decimal("78.8300")),
        ]
        if not LocationUpdate.objects.filter(order=active_order).exists():
            for lat, lng in route:
                LocationUpdate.objects.create(order=active_order, latitude=lat, longitude=lng)

        # 3. Just placed, paid, waiting for the restaurant to accept
        placed_order = self._make_order(
            "order_stub_placed",
            customer, restaurant, home,
            [(paneer_tikka["food"], paneer_tikka["food"].base_price, 1, None)],
            OrderStatus.PLACED, OrderPaymentStatus.PAID, days_ago=0,
        )
        Payment.objects.get_or_create(
            order=placed_order,
            defaults={
                "razorpay_order_id": "order_stub_placed", "razorpay_payment_id": "pay_stub_placed",
                "amount": placed_order.total_amount, "status": PaymentStatus.SUCCESS, "is_stub": True,
            },
        )

        # 4. Cancelled + refunded — 2 days ago
        cancelled_order = self._make_order(
            "order_stub_cancelled",
            customer, restaurant, home,
            [(natu_kodi["food"], natu_kodi["food"].base_price, 1, None)],
            OrderStatus.CANCELLED, OrderPaymentStatus.REFUNDED, days_ago=2,
        )
        payment = Payment.objects.get_or_create(
            order=cancelled_order,
            defaults={
                "razorpay_order_id": "order_stub_cancelled", "razorpay_payment_id": "pay_stub_cancelled",
                "amount": cancelled_order.total_amount, "status": PaymentStatus.SUCCESS, "is_stub": True,
            },
        )[0]
        payment.refunds.get_or_create(
            amount=cancelled_order.total_amount, defaults={"reason": "Customer requested cancellation"}
        )

        return delivered_order, active_order, placed_order, cancelled_order

    # ---------- notifications ----------

    def _seed_notifications(self, customer, owner, delivery_user, delivered_order, active_order, placed_order):
        Notification.objects.get_or_create(
            user=customer, title="Welcome to Rayalseema!",
            defaults={"body": "Fiery Rayalseema flavours, delivered to your door.", "notification_type": NotificationType.SYSTEM},
        )
        Notification.objects.get_or_create(
            user=customer, title="Your order was delivered", related_order=delivered_order,
            defaults={"body": "Hope you enjoyed your meal from Rayalseema Spice Kitchen!", "notification_type": NotificationType.ORDER_STATUS, "is_read": True},
        )
        Notification.objects.get_or_create(
            user=customer, title="Your order is on the way", related_order=active_order,
            defaults={"body": "Your delivery partner has picked up your order.", "notification_type": NotificationType.ORDER_STATUS},
        )
        Notification.objects.get_or_create(
            user=owner, title="New order received", related_order=placed_order,
            defaults={"body": "You've received a new order — accept it from Incoming Orders.", "notification_type": NotificationType.ORDER_STATUS},
        )
        Notification.objects.get_or_create(
            user=delivery_user, title="New delivery assigned", related_order=active_order,
            defaults={"body": "You've been assigned a delivery. Head to the restaurant to pick it up.", "notification_type": NotificationType.ORDER_STATUS, "is_read": True},
        )

    # ---------- audit log ----------

    def _seed_audit_log(self, admin, restaurant, partner, cancelled_order):
        log_action(admin, "restaurant.approve", "Restaurant", restaurant.id, {"name": restaurant.name})
        log_action(admin, "delivery_partner.approve", "DeliveryPartner", partner.id, {"email": partner.user.email})
        log_action(
            admin, "payment.refund", "Order", cancelled_order.id,
            {"amount": str(cancelled_order.total_amount), "reason": "Customer requested cancellation"},
        )
