from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "user", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["user__email", "restaurant__name"]
