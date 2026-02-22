from django.urls import path, include

from dashboard import views

urlpatterns = [
    path("", views.home),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
]
