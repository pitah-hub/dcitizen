from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from .models import ServiceRequest


def citizen_required(view):
    """
    Citizen-only page. Anonymous users go to login; staff are sent to the
    admin panel instead (staff do not file requests).
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect("panel:dashboard")
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def staff_required(view):
    """Admin-panel page. Anonymous users go to login; non-staff get a 403."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def get_owned_request(user, pk):
    """
    Fetch a request that belongs to `user`, or raise 404.
    404 rather than 403 on purpose: it does not reveal that the id exists.
    """
    return get_object_or_404(ServiceRequest.objects.for_user(user), pk=pk)
