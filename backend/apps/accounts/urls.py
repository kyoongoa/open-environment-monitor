from django.urls import path

from .views import (
    admin_login_view,
    analysis_visualization_view,
    aqi_index_predict_view,
    air_quality_data_list_view,
    change_password_view,
    login_view,
    profile_view,
    register_view,
    upload_avatar_view,
    weather_filter_options_view,
    weather_data_list_view,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("admin-login/", admin_login_view, name="admin-login"),
    path("profile/", profile_view, name="profile"),
    path("change-password/", change_password_view, name="change-password"),
    path("upload-avatar/", upload_avatar_view, name="upload-avatar"),
    path("weather-data/", weather_data_list_view, name="weather-data-list"),
    path("weather-options/", weather_filter_options_view, name="weather-options"),
    path("air-quality-data/", air_quality_data_list_view, name="air-quality-data-list"),
    path("aqi-index-predict/", aqi_index_predict_view, name="aqi-index-predict"),
    path("analysis-visualization/", analysis_visualization_view, name="analysis-visualization"),
]
