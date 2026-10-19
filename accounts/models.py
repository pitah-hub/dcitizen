from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models

# Kenyan national IDs are 7 or 8 digits.
national_id_validator = RegexValidator(
    regex=r"^\d{7,8}$",
    message="Enter a valid national ID (7 or 8 digits).",
)

# Accepts 0712345678, 0112345678, 254712345678 and +254712345678.
phone_validator = RegexValidator(
    regex=r"^(?:\+254|254|0)[17]\d{8}$",
    message="Enter a valid Kenyan phone number, e.g. 0712345678 or +254712345678.",
)


class UserManager(BaseUserManager):
    """Manager for a user model that logs in with email instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Citizen or staff account.

    Citizens: is_staff=False. Admin officers: is_staff=True.
    Role checks everywhere in the project use is_staff, nothing else.
    """

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150)
    national_id = models.CharField(
        "national ID", max_length=8, unique=True, validators=[national_id_validator]
    )
    phone = models.CharField(max_length=15, validators=[phone_validator])
    posting_suspended = models.BooleanField(
        default=False,
        help_text="The citizen can sign in and read, but cannot report, message or rate.",
    )
    suspension_reason = models.CharField(max_length=200, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "national_id", "phone"]

    objects = UserManager()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0]

    def __str__(self):
        return self.email
