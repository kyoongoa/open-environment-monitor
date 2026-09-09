from django.urls import path
from .environment_views import history_view, realtime_view, trend_view

urlpatterns = [
    path("realtime/", realtime_view, name="environment-realtime"),
    path("history/", history_view, name="environment-history"),
    path("trend/", trend_view, name="environment-trend"),
]
