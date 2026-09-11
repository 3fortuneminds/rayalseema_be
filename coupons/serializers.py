from rest_framework import serializers


class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=8, decimal_places=2)
