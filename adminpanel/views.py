"""Staff-facing request management views."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode

from services.analytics import dashboard_stats
from services.forms import StatusChangeForm
from services.models import Category, County, ServiceRequest, Status
from services.notifications import send_status_email
from services.permissions import staff_required


@staff_required
def dashboard(request):
    """Show service-wide counts, charts, and the oldest pending requests."""
    # Oldest first: these have been waiting the longest and need attention first.
    pending_requests = (
        ServiceRequest.objects.filter(status=Status.PENDING)
        .select_related("category", "county", "user")
        .order_by("created_at")[:10]
    )
    return render(
        request,
        "adminpanel/dashboard.html",
        {"stats": dashboard_stats(), "pending_requests": pending_requests},
    )


@staff_required
def request_list(request):
    """List requests with staff filters, search, and pagination."""
    queryset = ServiceRequest.objects.select_related("category", "county", "user")
    selected_status = request.GET.get("status", "")
    category_id = request.GET.get("category", "")
    county_id = request.GET.get("county", "")
    query = request.GET.get("q", "").strip()
    if selected_status in Status.values:
        queryset = queryset.filter(status=selected_status)
    if category_id.isdigit():
        queryset = queryset.filter(category_id=category_id)
    if county_id.isdigit():
        queryset = queryset.filter(county_id=county_id)
    if query:
        queryset = queryset.filter(
            Q(reference__icontains=query) | Q(user__full_name__icontains=query)
        )
    query_params = request.GET.copy()
    query_params.pop("page", None)
    page_obj = Paginator(queryset, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "adminpanel/request_list.html",
        {
            "page_obj": page_obj,
            "statuses": Status,
            "categories": Category.objects.all(),
            "counties": County.objects.all(),
            "selected_status": selected_status,
            "category_id": category_id,
            "county_id": county_id,
            "query": query,
            "filter_query": urlencode(query_params),
        },
    )


@staff_required
def request_detail(request, pk):
    """Display and safely advance one request through the status workflow."""
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related("category", "county", "user"), pk=pk
    )
    form = StatusChangeForm(request.POST or None, service_request=service_request)
    if request.method == "POST" and form.is_valid():
        try:
            update = service_request.change_status(
                form.cleaned_data["new_status"],
                by=request.user,
                note=form.cleaned_data["note"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            send_status_email(service_request, update)
            messages.success(request, "Request status updated and citizen notified.")
            return redirect("panel:request_detail", pk=service_request.pk)
    history = service_request.history.select_related("changed_by").all()
    return render(
        request,
        "adminpanel/request_detail.html",
        {"service_request": service_request, "history": history, "form": form},
    )