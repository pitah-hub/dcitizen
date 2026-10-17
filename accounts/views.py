"""Public and account-facing views."""
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from services.models import Category, ServiceRequest

from .forms import ProfileForm, RegistrationForm


def landing(request):
    """Show the public landing page and active service categories."""
    return render(request, "public/landing.html", {"categories": Category.objects.filter(is_active=True)})


def about(request):
    """Show an overview of the service."""
    return render(request, "public/about.html")


def contact(request):
    """Show placeholder support contacts."""
    return render(request, "public/contact.html")


def track(request):
    """Find a request by reference without revealing private request details."""
    reference = request.GET.get("ref", "").strip().upper()
    service_request = None
    not_found = False
    if reference:
        service_request = ServiceRequest.objects.select_related("category", "county").filter(reference=reference).first()
        not_found = service_request is None
    return render(
        request,
        "public/track.html",
        {"reference": reference, "service_request": service_request, "not_found": not_found},
    )


def register(request):
    """Register a citizen and sign them in immediately."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account has been created. Welcome to Huduma Requests.")
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})


def profile(request):
    """Allow a citizen to update their contact details."""
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})
