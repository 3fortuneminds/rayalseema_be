import uuid

from django.conf import settings
from django.db import models

from restaurants.models import Restaurant


class FoodCategory(models.Model):
    """Menu section for a restaurant, e.g. Starters, Biryani, Desserts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="food_categories")
    name = models.CharField(max_length=80)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "food_categories"
        ordering = ["display_order", "name"]
        unique_together = ["restaurant", "name"]
        verbose_name_plural = "food categories"

    def __str__(self):
        return f"{self.restaurant.name} — {self.name}"


class Food(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="foods")
    category = models.ForeignKey(
        FoodCategory, on_delete=models.SET_NULL, related_name="foods", null=True, blank=True
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="foods/", blank=True, null=True)

    is_vegetarian = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "foods"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


class FoodVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=60)  # e.g. Half, Full, Regular, Large
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "food_variants"
        ordering = ["price"]

    def __str__(self):
        return f"{self.food.name} — {self.name}"


class FoodWishlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "food_wishlists"
        unique_together = ["user", "food"]
