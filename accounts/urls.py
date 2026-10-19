"""Public and authentication routes."""
from django.contrib.auth import views as auth_views
from django.urls import path

from services.permissions import citizen_required

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("track/", views.track, name="track"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html", redirect_authenticated_user=True
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", citizen_required(views.profile), name="profile"),
    path(
        "password-change/",
        citizen_required(auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html", success_url="/profile/"
        )),
        name="password_change",
    ),
]