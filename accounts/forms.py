from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, UserCreationForm

from .models import User


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to every widget so templates can just render the form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Citizen sign-up. Password rules come from Django's validators in settings."""

    class Meta:
        model = User
        fields = ("full_name", "national_id", "email", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Citizen self-service edit. National ID is deliberately not editable."""

    class Meta:
        model = User
        fields = ("full_name", "email", "phone")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        taken = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class BootstrapPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    """Step 1 of a password reset: ask for the account email."""


class BootstrapSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    """Step 2: choose a new password after following the emailed link."""
