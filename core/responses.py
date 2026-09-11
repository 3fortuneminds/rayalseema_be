from rest_framework.response import Response


def success_response(data=None, message="Success", status=200, meta=None):
    body = {"success": True, "message": message, "data": data}
    if meta is not None:
        body["meta"] = meta
    return Response(body, status=status)


def error_response(message="Error", errors=None, status=400):
    return Response(
        {"success": False, "message": message, "errors": errors},
        status=status,
    )
