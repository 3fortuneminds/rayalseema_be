from django.contrib import admin

from .models import Food, FoodCategory, FoodVariant, FoodWishlist


class FoodVariantInline(admin.TabularInline):
    model = FoodVariant
    extra = 0


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "category", "base_price", "is_vegetarian", "is_available"]
    list_filter = ["is_vegetarian", "is_available", "restaurant"]
    search_fields = ["name", "restaurant__name"]
    inlines = [FoodVariantInline]


@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "display_order"]
    list_filter = ["restaurant"]


admin.site.register(FoodWishlist)
