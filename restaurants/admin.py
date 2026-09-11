from django.contrib import admin

from .models import FavoriteRestaurant, OpeningHours, Restaurant, RestaurantCategory


class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "avg_rating", "is_approved", "is_active"]
    list_filter = ["is_approved", "is_active", "categories"]
    search_fields = ["name", "city"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OpeningHoursInline]


@admin.register(RestaurantCategory)
class RestaurantCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon"]
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(FavoriteRestaurant)
