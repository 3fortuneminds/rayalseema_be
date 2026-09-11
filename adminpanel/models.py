from django.db import models


class PlatformSettings(models.Model):
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    delivery_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    support_email = models.EmailField(default="support@rayalseema.local")
    support_phone = models.CharField(max_length=20, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Platform settings"
