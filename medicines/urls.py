
from django.urls import path
from . import views

app_name = "medicines"

urlpatterns = [
    path("", views.medicine_directory, name="directory"),

    path("register/", views.medicine_create, name="register"),

    path(
        "<int:medicine_id>/",
        views.medicine_detail,
        name="detail"
    ),

    path(
        "<int:medicine_id>/edit/",
        views.medicine_update,
        name="update"
    ),

    path(
        "<int:medicine_id>/status/",
        views.medicine_change_status,
        name="change_status"
    ),
]
