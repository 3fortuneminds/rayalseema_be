import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class OTPPurpose(models.TextChoices):
    REGISTER = "register", "Registration"
    LOGIN = "login", "Login"
    PASSWORD_RESET = "password_reset", "Password Reset"
    PHONE_VERIFY = "phone_verify", "Phone Verification"


class OTPChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"


class OTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier = models.CharField(max_length=255, db_index=True)  # email or phone number
    channel = models.CharField(max_length=10, choices=OTPChannel.choices)
    purpose = models.CharField(max_length=20, choices=OTPPurpose.choices)
    code = models.CharField(max_length=6)

    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "otps"
        indexes = [models.Index(fields=["identifier", "purpose", "is_used"])]

    @staticmethod
    def generate_code():
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def create_for(cls, identifier, channel, purpose, ttl_minutes=None):
        ttl = ttl_minutes or getattr(settings, "OTP_TTL_MINUTES", 10)
        return cls.objects.create(
            identifier=identifier,
            channel=channel,
            purpose=purpose,
            code=cls.generate_code(),
            expires_at=timezone.now() + timedelta(minutes=ttl),
        )

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired() and self.attempts < self.max_attempts

    def __str__(self):
        return f"{self.identifier} [{self.purpose}]"
