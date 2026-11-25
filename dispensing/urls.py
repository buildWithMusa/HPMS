from django.urls import path
from . import views

app_name = "dispensing"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("history/", views.dispensing_history, name="history"),
    path("prescription/<int:prescription_id>/", views.dispense, name="dispense"),
]
