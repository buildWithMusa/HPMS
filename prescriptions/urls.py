from django.urls import path
from . import views

app_name = "prescriptions"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("list/", views.prescription_list, name="list"),
    path("create/", views.prescription_create, name="create"),
    path("paper/create/", views.paper_prescription_create, name="paper_create"),
    path("<int:pk>/", views.prescription_detail, name="detail"),
    path("<int:pk>/submit/", views.prescription_submit, name="submit"),
    path("<int:pk>/verify/", views.prescription_verify, name="verify"),
    path("<int:pk>/reject/", views.prescription_reject, name="reject"),
    path("<int:pk>/cancel/", views.prescription_cancel, name="cancel"),
]
