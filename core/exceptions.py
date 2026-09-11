from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        message = "Error"
        if isinstance(errors, dict):
            detail = errors.get("detail")
            if detail is not None:
                message = str(detail)
                errors = None
        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
        }

    return response
