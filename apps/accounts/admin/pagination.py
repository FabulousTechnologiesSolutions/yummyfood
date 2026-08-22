from core.pagination import StandardResultsSetPagination


def paginated_admin_response(request, queryset, serialize_item):
    """Page-number envelope: count, next, previous, results.

    Query params: ``page`` (default 1), ``page_size`` (default 10, max 100).
    """
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([serialize_item(obj) for obj in page])
