import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send(user, subject, body):
    """
    Send one email. A mail failure must never break the request the citizen
    just submitted or the status change the officer just made, so errors are
    logged instead of raised.
    """
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        logger.exception("Could not send email to %s", user.email)


def send_submission_email(service_request):
    """Call right after a citizen's request is saved."""
    user = service_request.user
    body = (
        f"Hello {user.get_short_name()},\n\n"
        f"We have received your request.\n\n"
        f"Reference: {service_request.reference}\n"
        f"Category: {service_request.category}\n"
        f"County: {service_request.county}\n"
        f"Status: {service_request.get_status_display()}\n\n"
        f"You can track it any time with your reference number."
    )
    _send(user, f"Request received: {service_request.reference}", body)


def send_status_email(service_request, update):
    """Call right after change_status(); `update` is the StatusUpdate it returned."""
    user = service_request.user
    lines = [
        f"Hello {user.get_short_name()},\n",
        f"Your request {service_request.reference} is now: {update.get_new_status_display()}.",
    ]
    if update.note:
        lines.append(f"\nNote from the officer:\n{update.note}")
    _send(user, f"Update on {service_request.reference}: {update.get_new_status_display()}", "\n".join(lines))


def send_comment_email(comment):
    """Tell the citizen about a message from an officer. Call after a staff comment is saved."""
    service_request = comment.request
    user = service_request.user
    body = (
        f"Hello {user.get_short_name()},\n\n"
        f"An officer left a message on your request {service_request.reference}:\n\n"
        f"{comment.body}\n\n"
        f"Sign in to reply."
    )
    _send(user, f"New message on {service_request.reference}", body)