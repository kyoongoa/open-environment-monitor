from django.urls import path
from .environment_views import air_quality_observations_view, analysis_visualization_view, dashboard_summary_view, history_view, realtime_view, trend_view, weather_observations_view

urlpatterns = [
    path("dashboard-summary/", dashboard_summary_view, name="environment-dashboard-summary"),
    path("analysis-visualization/", analysis_visualization_view, name="environment-analysis-visualization"),
    path("weather-observations/", weather_observations_view, name="weather-observations"),
    path("air-quality-observations/", air_quality_observations_view, name="air-quality-observations"),
    path("realtime/", realtime_view, name="environment-realtime"),
    path("history/", history_view, name="environment-history"),
    path("trend/", trend_view, name="environment-trend"),
]
