
from django.urls import path

from . import views


app_name = "staff"

urlpatterns = [

    path(
        "register/",
        views.register_staff_view,
        name="register"
    ),

    path(
        "activate/<uidb64>/<token>/",
        views.activate_staff_account,
        name="activate"
    ),

    path(
        "activation-success/",
        views.activation_success,
        name="activation_success"
    ),

    path(
        "login/",
        views.staff_login,
        name="login"
    ),

    path(
        "dashboard/",
        views.staff_dashboard,
        name="dashboard"
    ),

    path(
        "logout/",
        views.staff_logout,
        name="logout"
    ),
    path(
    "directory/",
    views.staff_directory,
    name="directory",
),

]
