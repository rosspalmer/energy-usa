from django.shortcuts import render

# Import so the Dash app is registered
from dashboard.dash_app import app  # noqa: F401


def home(request):
    """Home page with the State electricity Dash app."""
    return render(request, "dashboard/home.html")
