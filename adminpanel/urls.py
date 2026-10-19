"""Staff-panel routes."""
from django.urls import path

from . import views

app_name = "panel"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/comments/", views.request_comment, name="request_comment"),
]
