from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class AppAPIException(APIException):
    """Raise with a stable error code for the FoodApp envelope."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'error'
    default_detail = 'An error occurred.'

    def __init__(self, code=None, message=None, details=None, status_code=None):
        self.detail_code = code or self.default_code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=message or self.default_detail)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, AppAPIException):
        response.data = {
            'error': {
                'code': exc.detail_code,
                'message': str(exc.detail),
                'details': exc.details,
            }
        }
        return response

    # Normalize DRF validation / auth errors into the envelope.
    data = response.data
    if isinstance(data, dict) and 'error' in data and isinstance(data['error'], dict):
        return response

    message = 'Request failed.'
    details = data
    code = getattr(exc, 'default_code', None) or 'error'

    if isinstance(data, dict):
        if 'detail' in data and len(data) == 1:
            message = str(data['detail'])
            details = {}
        elif 'non_field_errors' in data:
            errs = data['non_field_errors']
            message = str(errs[0]) if isinstance(errs, list) and errs else str(errs)
    elif isinstance(data, list) and data:
        message = str(data[0])
        details = {}

    response.data = {
        'error': {
            'code': str(code).upper() if isinstance(code, str) else 'ERROR',
            'message': message,
            'details': details if isinstance(details, dict) else {},
        }
    }
    return response
