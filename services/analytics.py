from django.db.models import Avg, Count, Q

from .models import Category, Feedback, ServiceRequest, Status


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


def feedback_stats():
    """
    Citizen satisfaction summary for the admin dashboard.

    Keys:
      count           how many ratings exist
      average         mean rating to 1 decimal, or None when there are none
      average_stars   the average rounded half-up to a whole number, for drawing stars
      low_count       ratings of 1 or 2 (the ones worth reading first)
      latest_comments the five newest ratings that include a comment
      by_category     {"name", "avg", "total"} per category, lowest average first;
                      categories without any rating are left out
    """
    summary = Feedback.objects.aggregate(
        count=Count("id"),
        average=Avg("rating"),
        low_count=Count("id", filter=Q(rating__lte=2)),
    )
    average = summary["average"]
    summary["average"] = round(average, 1) if average is not None else None
    summary["average_stars"] = int(average + 0.5) if average is not None else 0
    summary["latest_comments"] = list(
        Feedback.objects.exclude(comment="").select_related("request__category")[:5]
    )
    summary["by_category"] = list(
        Category.objects.annotate(
            avg=Avg("requests__feedback__rating"),
            total=Count("requests__feedback"),
        )
        .filter(total__gt=0)
        .values("name", "avg", "total")
        .order_by("avg", "name")
    )
    return summary