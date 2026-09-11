import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("otp")


def send_email_otp(email, code):
    if settings.OTP_STUB_MODE:
        logger.info("[STUB] Email OTP to %s: %s", email, code)
        return
    send_mail(
        subject="Your verification code",
        message=f"Your verification code is {code}. It expires in {settings.OTP_TTL_MINUTES} minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def send_sms_otp(phone_number, code):
    if settings.OTP_STUB_MODE:
        logger.info("[STUB] SMS OTP to %s: %s", phone_number, code)
        return
    from twilio.rest import Client

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=f"Your verification code is {code}.",
        from_=settings.TWILIO_FROM_NUMBER,
        to=phone_number,
    )


class OTPError(Exception):
    pass


def consume_otp(identifier, purpose, code):
    from .models import OTP

    otp = (
        OTP.objects.filter(identifier=identifier, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )

    if otp is None or not otp.is_valid():
        raise OTPError("OTP invalid or expired")

    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise OTPError("Incorrect OTP")

    otp.is_used = True
    otp.save(update_fields=["is_used"])
