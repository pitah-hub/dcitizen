from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models, transaction


# ---------------------------------------------------------------------------
# Shared logic: the status workflow lives here and nowhere else.
# ---------------------------------------------------------------------------

class Status(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"


ALLOWED_TRANSITIONS = {
    Status.PENDING: [Status.IN_PROGRESS],
    Status.IN_PROGRESS: [Status.RESOLVED],
    Status.RESOLVED: [],
}


# Rough bounding box of Kenya, used to reject pins dropped far outside the country.
KENYA_LAT_RANGE = (-5.0, 5.5)
KENYA_LNG_RANGE = (33.5, 42.5)


def is_valid_transition(current, new):
    """True only if moving from `current` to `new` follows the workflow."""
    return new in ALLOWED_TRANSITIONS.get(current, [])


def validate_image_size(file):
    limit_mb = 5
    if file.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image must be {limit_mb} MB or smaller.")


# ---------------------------------------------------------------------------
# Lookup tables (seeded once, managed by staff)
# ---------------------------------------------------------------------------

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Bootstrap icon class, e.g. bi-lightbulb"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class County(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "counties"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Main records
# ---------------------------------------------------------------------------

class ServiceRequestQuerySet(models.QuerySet):
    def for_user(self, user):
        """Citizen views must always go through this. Prevents seeing others' data."""
        return self.filter(user=user)

    def open_cases(self):
        return self.exclude(status=Status.RESOLVED)

    def resolved(self):
        return self.filter(status=Status.RESOLVED)


class ServiceRequest(models.Model):
    reference = models.CharField(
        max_length=20, unique=True, null=True, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_requests",
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="requests")
    county = models.ForeignKey(County, on_delete=models.PROTECT, related_name="requests")
    area = models.CharField("area / landmark", max_length=150)
    description = models.TextField(validators=[MinLengthValidator(20)])
    image = models.ImageField(
        upload_to="requests/%Y/%m/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png"]),
            validate_image_size,
        ],
    )
    latitude = models.FloatField(
        blank=True, null=True, validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        blank=True, null=True, validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ServiceRequestQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference or 'NEW'} - {self.category}"

    def clean(self):
        """A map pin needs both coordinates, and must be inside Kenya."""
        super().clean()
        has_lat, has_lng = self.latitude is not None, self.longitude is not None
        if has_lat != has_lng:
            raise ValidationError("The map pin is incomplete. Click the map again to place it.")
        if has_lat and not (
            KENYA_LAT_RANGE[0] <= self.latitude <= KENYA_LAT_RANGE[1]
            and KENYA_LNG_RANGE[0] <= self.longitude <= KENYA_LNG_RANGE[1]
        ):
            raise ValidationError("The map pin must be inside Kenya.")

    def save(self, *args, **kwargs):
        """
        On first save: generate the reference (SR-<year>-<id>) and write the
        first history entry, so every request always has a timeline.
        """
        creating = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                self.reference = f"SR-{self.created_at.year}-{self.pk:04d}"
                super().save(update_fields=["reference"])
                StatusUpdate.objects.create(
                    request=self,
                    old_status="",
                    new_status=self.status,
                    changed_by=self.user,
                    note="Request submitted.",
                )

    @property
    def is_open(self):
        return self.status != Status.RESOLVED

    @property
    def can_receive_feedback(self):
        """True when the request is Resolved and has not been rated yet."""
        return (
            self.status == Status.RESOLVED
            and not Feedback.objects.filter(request_id=self.pk).exists()
        )

    def change_status(self, new_status, by, note=""):
        """
        The ONLY way status should change. Views call this, nothing else.
        Raises ValidationError on an illegal move; otherwise saves the new
        status and appends a StatusUpdate. Returns the StatusUpdate.
        """
        if new_status not in Status.values:
            raise ValidationError("Unknown status.")
        if not is_valid_transition(self.status, new_status):
            raise ValidationError(
                f"Cannot move from {self.get_status_display()} to "
                f"{Status(new_status).label}."
            )
        with transaction.atomic():
            old_status = self.status
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])
            return StatusUpdate.objects.create(
                request=self,
                old_status=old_status,
                new_status=new_status,
                changed_by=by,
                note=note,
            )


class StatusUpdate(models.Model):
    """Append-only history. Never edited, never deleted by app code."""

    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="history"
    )
    old_status = models.CharField(max_length=20, choices=Status.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.request.reference}: {self.old_status or '-'} -> {self.new_status}"


class Feedback(models.Model):
    """
    A citizen's rating of how their resolved request was handled.

    One per request: the OneToOneField makes the database refuse a second one.
    A rating from 1 to 5 is checked by validators and by a database constraint.
    Only resolved requests can be rated: clean() checks it, and the view
    checks ownership (see views.request_feedback).
    """

    request = models.OneToOneField(
        ServiceRequest, on_delete=models.CASCADE, related_name="feedback"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(
        blank=True, max_length=500, validators=[MaxLengthValidator(500)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="feedback_rating_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.request.reference}: {self.rating}/5"

    def clean(self):
        if self.request_id and self.request.status != Status.RESOLVED:
            raise ValidationError("Feedback can only be given on a resolved request.")


class Comment(models.Model):
    """
    A message on a request, from the citizen who filed it or from staff.

    Separate from StatusUpdate: status changes are the official record, comments
    are the conversation. The thread closes once the request is Resolved.
    """

    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    body = models.TextField(max_length=1000, validators=[MaxLengthValidator(1000)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.request.reference}: message {self.pk}"

    def clean(self):
        if self.request_id and self.request.status == Status.RESOLVED:
            raise ValidationError("This request is resolved, so the conversation is closed.")