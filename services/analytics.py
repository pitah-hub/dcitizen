from django.db.models import Count, Q

from .models import Category, ServiceRequest, Status


def _status_counts(queryset):
    """Total and per-status counts for any ServiceRequest queryset, in one query."""
    counts = queryset.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Status.PENDING)),
        in_progress=Count("id", filter=Q(status=Status.IN_PROGRESS)),
        resolved=Count("id", filter=Q(status=Status.RESOLVED)),
    )
    counts["open"] = counts["pending"] + counts["in_progress"]
    return counts


def citizen_stats(user):
    """Numbers for a citizen's dashboard strip. Only that user's requests."""
    return _status_counts(ServiceRequest.objects.for_user(user))


def dashboard_stats():
    """
    Numbers for the admin dashboard.

    Returns the status counts (total, pending, in_progress, resolved, open)
    plus `by_category`: a list of {"name", "total"} including categories with
    zero requests, busiest first.
    """
    stats = _status_counts(ServiceRequest.objects.all())
    stats["by_category"] = list(
        Category.objects.annotate(total=Count("requests"))
        .values("name", "total")
        .order_by("-total", "name")
    )
    return stats
