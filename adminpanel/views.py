"""Staff-facing request management views."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from services.analytics import dashboard_stats, feedback_stats
from services.forms import CommentForm, StatusChangeForm
from services.models import Category, Comment, County, ServiceRequest, Status
from services.notifications import send_comment_email, send_status_email
from services.permissions import staff_required

User = get_user_model()


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
        {
            "stats": dashboard_stats(),
            "feedback": feedback_stats(),
            "pending_requests": pending_requests,
        },
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
        ServiceRequest.objects.select_related(
            "category", "county", "user", "feedback"
        ),
        pk=pk,
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
        {
            "service_request": service_request,
            "history": history,
            "form": form,
            "comments": service_request.comments.select_related("author"),
            "comment_form": CommentForm(),
            "can_comment": service_request.is_open,
        },
    )


@staff_required
@require_POST
def request_comment(request, pk):
    """Post an officer's message on any open request and email the citizen."""
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    if not service_request.is_open:
        messages.error(request, "This request is resolved, so the conversation is closed.")
        return redirect("panel:request_detail", pk=pk)
    form = CommentForm(
        request.POST, instance=Comment(request=service_request, author=request.user)
    )
    if form.is_valid():
        comment = form.save()
        send_comment_email(comment)
        messages.success(request, "Message posted and citizen notified.")
    else:
        messages.error(request, "Write a message of up to 1000 characters.")
    return redirect("panel:request_detail", pk=pk)


def _back_to_request(request):
    """Return to the request page the officer came from, else the dashboard."""
    request_pk = request.POST.get("request", "")
    if request_pk.isdigit():
        return redirect("panel:request_detail", pk=int(request_pk))
    return redirect("panel:dashboard")


@staff_required
@require_POST
def citizen_posting(request, pk):
    """Suspend or reinstate a citizen's right to report, message and rate."""
    citizen = get_object_or_404(User, pk=pk, is_staff=False)
    action = request.POST.get("action")
    if action == "suspend":
        citizen.posting_suspended = True
        citizen.suspension_reason = request.POST.get("reason", "").strip()[:200]
        messages.success(request, f"{citizen.full_name} can no longer post.")
    elif action == "reinstate":
        citizen.posting_suspended = False
        citizen.suspension_reason = ""
        messages.success(request, f"{citizen.full_name} can post again.")
    else:
        messages.error(request, "Unknown action.")
        return _back_to_request(request)
    citizen.save(update_fields=["posting_suspended", "suspension_reason"])
    return _back_to_request(request)
