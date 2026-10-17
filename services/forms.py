from django import forms

from accounts.forms import BootstrapFormMixin

from .models import ALLOWED_TRANSITIONS, Category, ServiceRequest


class ReportForm(BootstrapFormMixin, forms.ModelForm):
    """
    Citizen report form. The view must set the owner itself:

        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()

    The template needs enctype="multipart/form-data" for the image upload.
    """

    class Meta:
        model = ServiceRequest
        fields = ["category", "county", "area", "description", "image"]
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Describe the problem (at least 20 characters)."}
            ),
            "area": forms.TextInput(attrs={"placeholder": "e.g. Kenyatta Avenue, near the market"}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["category"].empty_label = "Select a category"
        self.fields["county"].empty_label = "Select a county"


class StatusChangeForm(BootstrapFormMixin, forms.Form):
    """
    Staff form for moving a request forward. The dropdown only offers the
    statuses the workflow allows next, so illegal moves cannot even be picked.
    The model re-checks anyway inside change_status().
    """

    new_status = forms.ChoiceField(label="New status")
    note = forms.CharField(
        label="Note to citizen (optional)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, service_request, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_request = service_request
        allowed = ALLOWED_TRANSITIONS[service_request.status]
        self.fields["new_status"].choices = [(s.value, s.label) for s in allowed]

    @property
    def can_change(self):
        """False once a request is Resolved: the template should hide the form."""
        return bool(self.fields["new_status"].choices)
