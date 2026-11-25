
from django.urls import path
from . import views

app_name = "patients"

urlpatterns = [
    path(
        "register/",
        views.register_patient_view,
        name="register",
    ),

    path(
        "registration-success/<int:patient_id>/",
        views.registration_success,
        name="registration_success",
    ),

    path(
        "directory/",
        views.patient_directory,
        name="directory",
    ),

    path(
        "<int:patient_id>/",
        views.patient_profile,
        name="profile",
    ),
    path(
    "<int:patient_id>/update/",
    views.update_patient_view,
    name="update",
),
path(
    "<int:patient_id>/status/",
    views.change_patient_status_view,
    name="change_status",
),
]
