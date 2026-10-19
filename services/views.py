"""Citizen service-request views."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from .analytics import citizen_stats
from .forms import CommentForm, FeedbackForm, ReportForm
from .models import Comment, Feedback, ServiceRequest, Status
from .notifications import send_submission_email
from .permissions import citizen_required, get_owned_request, posting_allowed


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
@posting_allowed
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
    can_give_feedback = service_request.can_receive_feedback
    return render(
        request,
        "services/request_detail.html",
        {
            "service_request": service_request,
            "history": history,
            "can_give_feedback": can_give_feedback,
            "feedback_form": FeedbackForm() if can_give_feedback else None,
            "comments": service_request.comments.select_related("author"),
            "comment_form": CommentForm(),
            "can_comment": service_request.is_open,
        },
    )


@citizen_required
@posting_allowed
@require_POST
def request_feedback(request, pk):
    """Save the citizen's single rating for their own resolved request."""
    service_request = get_owned_request(request.user, pk)
    if not service_request.can_receive_feedback:
        messages.error(
            request, "Feedback can only be given once, after a request is resolved."
        )
        return redirect("request_detail", pk=pk)
    form = FeedbackForm(request.POST, instance=Feedback(request=service_request))
    if not form.is_valid():
        # Only reachable by tampering (the page enforces a rating): no need to re-render.
        messages.error(request, "Please choose a rating from 1 to 5 stars.")
        return redirect("request_detail", pk=pk)
    try:
        with transaction.atomic():
            form.save()
    except IntegrityError:
        # Two submits raced: the database allows only one rating per request.
        messages.error(request, "This request has already been rated.")
    else:
        messages.success(request, "Thank you for your feedback.")
    return redirect("request_detail", pk=pk)


@citizen_required
@posting_allowed
@require_POST
def request_comment(request, pk):
    """Post a message on the citizen's own request while it is still open."""
    service_request = get_owned_request(request.user, pk)
    if not service_request.is_open:
        messages.error(request, "This request is resolved, so the conversation is closed.")
        return redirect("request_detail", pk=pk)
    form = CommentForm(
        request.POST, instance=Comment(request=service_request, author=request.user)
    )
    if form.is_valid():
        form.save()
        messages.success(request, "Your message was posted.")
    else:
        messages.error(request, "Write a message of up to 1000 characters.")
    return redirect("request_detail", pk=pk)


@citizen_required
def request_receipt(request, pk):
    """Printable submission receipt for the citizen's own request."""
    service_request = get_owned_request(request.user, pk)
    track_url = (
        request.build_absolute_uri(reverse("track"))
        + "?"
        + urlencode({"ref": service_request.reference})
    )
    return render(
        request,
        "services/request_receipt.html",
        {"service_request": service_request, "track_url": track_url},
    )
