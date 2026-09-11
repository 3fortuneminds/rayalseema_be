from .responses import success_response


class EnvelopeMixin:
    """Wraps retrieve/create/update responses in the standard success envelope.

    DRF's ListModelMixin is already wrapped via StandardResultsPagination; destroy()
    is left as a bare 204 (no body to envelope, and that's standard REST practice).
    """

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return success_response(data=response.data)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return success_response(data=response.data, message="Created", status=response.status_code)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return success_response(data=response.data, message="Updated")
