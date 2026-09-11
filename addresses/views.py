from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from core.mixins import EnvelopeMixin
from core.responses import success_response

from .models import Address
from .serializers import AddressSerializer


class AddressViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        address = self.get_object()
        address.is_default = True
        address.save()
        return success_response(data=AddressSerializer(address).data, message="Default address updated")
