from rest_framework import serializers

from .models import OTPChannel, OTPPurpose


class SendOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    channel = serializers.ChoiceField(choices=OTPChannel.choices)
    purpose = serializers.ChoiceField(choices=OTPPurpose.choices)


class VerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    purpose = serializers.ChoiceField(choices=OTPPurpose.choices)
    code = serializers.CharField(max_length=6, min_length=6)
