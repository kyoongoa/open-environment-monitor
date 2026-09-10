import json
import time
from pathlib import Path

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import UserProfile


def _parse_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


@csrf_exempt
def register_view(request):
    if request.method != "POST":
        return JsonResponse({"message": "Only POST is allowed."}, status=405)
    data = _parse_body(request)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    if not username or not password:
        return JsonResponse({"message": "用户名和密码不能为空"}, status=400)
    if len(password) < 6:
        return JsonResponse({"message": "密码至少6位"}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"message": "用户名已存在"}, status=400)
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.get_or_create(user=user)
    return JsonResponse({"message": "注册成功", "username": user.username, "is_staff": bool(user.is_staff), "is_superuser": bool(user.is_superuser)})


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return JsonResponse({"message": "Only POST is allowed."}, status=405)
    data = _parse_body(request)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    if not username or not password:
        return JsonResponse({"message": "用户名和密码不能为空"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"message": "用户名或密码错误"}, status=400)
    UserProfile.objects.get_or_create(user=user)
    return JsonResponse({"message": "登录成功", "username": user.username, "is_staff": bool(user.is_staff), "is_superuser": bool(user.is_superuser)})


@csrf_exempt
def admin_login_view(request):
    if request.method != "POST":
        return JsonResponse({"message": "Only POST is allowed."}, status=405)
    data = _parse_body(request)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    if not username or not password:
        return JsonResponse({"message": "用户名和密码不能为空"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"message": "用户名或密码错误"}, status=400)
    if not (user.is_staff or user.is_superuser):
        return JsonResponse({"message": "该账号无管理员权限"}, status=403)
    return JsonResponse({"message": "管理员登录成功", "username": user.username, "is_staff": bool(user.is_staff), "is_superuser": bool(user.is_superuser)})


def _find_user(username):
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def _avatar_url(request, profile):
    if not profile.avatar:
        return ""
    try:
        return request.build_absolute_uri(profile.avatar.url)
    except Exception:
        return profile.avatar.url


@csrf_exempt
@require_http_methods(["GET", "POST"])
def profile_view(request):
    if request.method == "GET":
        username = str(request.GET.get("username", "")).strip()
    else:
        data = _parse_body(request)
        username = str(data.get("username", "")).strip()
    user = _find_user(username)
    if user is None:
        return JsonResponse({"message": "用户不存在"}, status=404)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == "POST":
        data = _parse_body(request)
        profile.display_name = str(data.get("display_name", profile.display_name or "")).strip()[:64]
        profile.phone = str(data.get("phone", profile.phone or "")).strip()[:32]
        profile.bio = str(data.get("bio", profile.bio or "")).strip()[:255]
        user.email = str(data.get("email", user.email or "")).strip()[:254]
        profile.updated_at = timezone.now()
        user.save(update_fields=["email"])
        profile.save(update_fields=["display_name", "phone", "bio", "updated_at"])
    return JsonResponse({"message": "ok", "data": {"username": user.username, "email": user.email or "", "display_name": profile.display_name or "", "phone": profile.phone or "", "bio": profile.bio or "", "avatar_url": _avatar_url(request, profile), "is_staff": bool(user.is_staff), "is_superuser": bool(user.is_superuser)}})


@csrf_exempt
@require_http_methods(["POST"])
def change_password_view(request):
    data = _parse_body(request)
    username = str(data.get("username", "")).strip()
    old_password = str(data.get("old_password", "")).strip()
    new_password = str(data.get("new_password", "")).strip()
    if not username or not old_password or not new_password:
        return JsonResponse({"message": "参数不完整"}, status=400)
    if len(new_password) < 6:
        return JsonResponse({"message": "新密码至少6位"}, status=400)
    user = authenticate(request, username=username, password=old_password)
    if user is None:
        return JsonResponse({"message": "原密码错误"}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return JsonResponse({"message": "密码修改成功"})


@csrf_exempt
@require_http_methods(["POST"])
def upload_avatar_view(request):
    username = str(request.POST.get("username", "")).strip()
    avatar = request.FILES.get("avatar")
    if not username or avatar is None:
        return JsonResponse({"message": "参数不完整"}, status=400)
    user = _find_user(username)
    if user is None:
        return JsonResponse({"message": "用户不存在"}, status=404)
    content_type = str(getattr(avatar, "content_type", ""))
    if not content_type.startswith("image/"):
        return JsonResponse({"message": "仅支持图片格式"}, status=400)
    if avatar.size > 4 * 1024 * 1024:
        return JsonResponse({"message": "图片大小不能超过4MB"}, status=400)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    ext = Path(avatar.name).suffix.lower() or ".png"
    file_name = f"avatars/{username}_{int(time.time())}{ext}"
    saved_path = default_storage.save(file_name, avatar)
    if profile.avatar and default_storage.exists(profile.avatar.name):
        try:
            default_storage.delete(profile.avatar.name)
        except Exception:
            pass
    profile.avatar = saved_path
    profile.updated_at = timezone.now()
    profile.save(update_fields=["avatar", "updated_at"])
    return JsonResponse({"message": "头像上传成功", "data": {"avatar_url": _avatar_url(request, profile)}})


@csrf_exempt
@require_http_methods(["POST"])
def aqi_index_predict_view(request):
    return JsonResponse({"message": "insufficient data: prediction is disabled until a model is trained from persisted provider observations."}, status=503)
