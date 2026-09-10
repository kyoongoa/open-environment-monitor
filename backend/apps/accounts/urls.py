from django.urls import path

from .views import (
    admin_login_view,
    aqi_index_predict_view,
    change_password_view,
    login_view,
    profile_view,
    register_view,
    upload_avatar_view,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("admin-login/", admin_login_view, name="admin-login"),
    path("profile/", profile_view, name="profile"),
    path("change-password/", change_password_view, name="change-password"),
    path("upload-avatar/", upload_avatar_view, name="upload-avatar"),
    path("aqi-index-predict/", aqi_index_predict_view, name="aqi-index-predict"),
]
