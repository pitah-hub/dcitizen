"""Citizen service-request routes."""
from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/feedback/", views.request_feedback, name="request_feedback"),
    path("requests/<int:pk>/comments/", views.request_comment, name="request_comment"),
    path("requests/<int:pk>/receipt/", views.request_receipt, name="request_receipt"),
    path("requests/<int:pk>/comments/", views.request_comment, name="request_comment"),
    path("requests/<int:pk>/receipt/", views.request_receipt, name="request_receipt"),
]
