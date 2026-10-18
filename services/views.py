"""Citizen service-request views."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils.http import urlencode

from .analytics import citizen_stats
from .forms import ReportForm
from .models import ServiceRequest, Status
from .notifications import send_submission_email
from .permissions import citizen_required, get_owned_request


@citizen_required
def dashboard(request):
    """Show a citizen's summary and five most recent requests."""
    recent_requests = (
        ServiceRequest.objects.for_user(request.user)
        .select_related("category", "county")[:5]
    )
    return render(
        request,
        "services/dashboard.html",
        {"stats": citizen_stats(request.user), "recent_requests": recent_requests},
    )


@citizen_required
def request_create(request):
    """Create a new public-service request for the signed-in citizen."""
    form = ReportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        service_request = form.save(commit=False)
        service_request.user = request.user
        service_request.save()
        send_submission_email(service_request)
        messages.success(
            request,
            f"Your request {service_request.reference} has been submitted successfully.",
        )
        return redirect("request_detail", pk=service_request.pk)
    return render(request, "services/request_create.html", {"form": form})


@citizen_required
def request_list(request):
    """List only the signed-in citizen's requests, newest first."""
    selected_status = request.GET.get("status", "")
    queryset = ServiceRequest.objects.for_user(request.user).select_related(
        "category", "county"
    )
    if selected_status in Status.values:
        queryset = queryset.filter(status=selected_status)
    query_params = request.GET.copy()
    query_params.pop("page", None)
    page_obj = Paginator(queryset, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "services/request_list.html",
        {
            "page_obj": page_obj,
            "statuses": Status,
            "selected_status": selected_status,
            "filter_query": urlencode(query_params),
        },
    )


@citizen_required
def request_detail(request, pk):
    """Show one request owned by the signed-in citizen and its timeline."""
    # 404, not 403, for a foreign request: never reveal that the id exists.
    service_request = get_owned_request(request.user, pk)
    history = service_request.history.select_related("changed_by").all()
    return render(
        request,
        "services/request_detail.html",
        {"service_request": service_request, "history": history},
    )