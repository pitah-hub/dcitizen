"""Password reset by emailed link, using Django's built-in (tested) views."""
from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import BootstrapPasswordResetForm, BootstrapSetPasswordForm

urlpatterns = [
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=BootstrapPasswordResetForm,
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=BootstrapSetPasswordForm,
            template_name="accounts/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
