from django import forms

from accounts.forms import BootstrapFormMixin

from .models import ALLOWED_TRANSITIONS, Category, Comment, Feedback, ServiceRequest


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
        fields = ["category", "county", "area", "description", "image", "latitude", "longitude"]
        widgets = {
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
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

    def clean_latitude(self):
        value = self.cleaned_data.get("latitude")
        return None if value is None else round(value, 6)

    def clean_longitude(self):
        value = self.cleaned_data.get("longitude")
        return None if value is None else round(value, 6)


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


class FeedbackForm(BootstrapFormMixin, forms.ModelForm):
    """
    Star rating plus optional comment. Build it with the request attached so
    the model's clean() can check the request is resolved:

        FeedbackForm(request.POST, instance=Feedback(request=service_request))
    """

    rating = forms.TypedChoiceField(
        label="Your rating",
        choices=[(star, star) for star in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={"required": "Please choose a rating from 1 to 5 stars."},
    )

    class Meta:
        model = Feedback
        fields = ["rating", "comment"]
        labels = {"comment": "Comment (optional)"}
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 500,
                    "placeholder": "What went well, or what could be better?",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The stars are styled by CSS; Bootstrap's input class would break them.
        self.fields["rating"].widget.attrs.pop("class", None)


class CommentForm(BootstrapFormMixin, forms.ModelForm):
    """
    One message. Build it with the request and author attached so the model's
    clean() can refuse messages on a resolved request:

        CommentForm(request.POST, instance=Comment(request=service_request, author=user))
    """

    class Meta:
        model = Comment
        fields = ["body"]
        labels = {"body": "Write a message"}
        widgets = {
            "body": forms.Textarea(
                attrs={"rows": 3, "maxlength": 1000, "placeholder": "Add an update or question (up to 1000 characters)."}
            ),
        }