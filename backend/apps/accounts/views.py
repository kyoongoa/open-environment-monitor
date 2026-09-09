import json
import re
import time
import datetime as dt
from pathlib import Path
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, Paginator
from django.core.files.storage import default_storage
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import AirQualityData, UserProfile, WeatherData


ANALYSIS_DEFINITIONS = [
    {
        "key": "analysis_city_diff",
        "title": "城市空气质量差异分析",
        "charts": [
            {"key": "chart_01", "title": "城市平均 AQI 对比柱状图", "table": "part1", "type": "bar"},
            {"key": "chart_02", "title": "城市平均 PM2.5 占比环形图", "table": "part2", "type": "bar"},
            {"key": "chart_03", "title": "城市 AQI 等级占比堆叠柱状图", "table": "part3", "type": "stack_bar"},
            {"key": "chart_04", "title": "城市污染天数对比图", "table": "part4", "type": "bar"},
            {"key": "chart_05", "title": "城市月均 PM2.5 趋势折线图", "table": "part5", "type": "line_multi"},
        ],
    },
    {
        "key": "analysis_time_series",
        "title": "空气质量时序变化分析",
        "charts": [
            {"key": "chart_06", "title": "AQI 日序列趋势图", "table": "part6", "type": "line_multi"},
            {"key": "chart_07", "title": "PM2.5 日序列趋势图", "table": "part7", "type": "line_multi"},
            {"key": "chart_08", "title": "AQI 年均对比柱状图", "table": "part8", "type": "line"},
            {"key": "chart_09", "title": "PM2.5 年均散点图", "table": "part9", "type": "line"},
            {"key": "chart_10", "title": "年度优良天占比变化图", "table": "part10", "type": "line"},
        ],
    },
    {
        "key": "analysis_season_cycle",
        "title": "空气质量季节周期分析",
        "charts": [
            {"key": "chart_11", "title": "AQI 月均季节曲线图", "table": "part11", "type": "line"},
            {"key": "chart_12", "title": "PM2.5 月均季节曲线图", "table": "part12", "type": "line"},
            {"key": "chart_13", "title": "AQI 季度均值对比图", "table": "part13", "type": "bar"},
            {"key": "chart_14", "title": "PM2.5 季度均值环形图", "table": "part14", "type": "bar"},
            {"key": "chart_15", "title": "月份-污染物浓度热力图", "table": "part15", "type": "line_multi"},
        ],
    },
    {
        "key": "analysis_weather_impact",
        "title": "气象条件影响分析",
        "charts": [
            {"key": "chart_16", "title": "天气类型-PM2.5 分组图", "table": "part16", "type": "bar"},
            {"key": "chart_17", "title": "天气类型-AQI 分布环形图", "table": "part17", "type": "bar"},
            {"key": "chart_18", "title": "风向-平均 PM2.5 雷达图", "table": "part18", "type": "bar"},
            {"key": "chart_19", "title": "风力-平均 PM2.5 分组图", "table": "part19", "type": "bar"},
            {"key": "chart_20", "title": "温度-PM2.5 散点图", "table": "part20", "type": "scatter"},
        ],
    },
    {
        "key": "analysis_pollutant_relation",
        "title": "污染物协同关系分析",
        "charts": [
            {"key": "chart_21", "title": "六项污染物多指标趋势图", "table": "part21", "type": "line_multi"},
            {"key": "chart_22", "title": "污染物相关性热力图", "table": "part22", "type": "heatmap"},
            {"key": "chart_23", "title": "PM2.5-PM10 散点图", "table": "part23", "type": "scatter"},
            {"key": "chart_24", "title": "PM2.5-NO2 气泡散点图", "table": "part24", "type": "line"},
            {"key": "chart_25", "title": "PM2.5-O3 对比柱状图", "table": "part25", "type": "bar"},
        ],
    },
]

ALLOWED_PART_TABLES = {
    chart["table"] for analysis in ANALYSIS_DEFINITIONS for chart in analysis["charts"]
}
_AQI_MODEL = None

# 简单进程内缓存：按城市分别缓存实时、小时趋势、近几日数据
_LIVE_CACHE = {}
_CACHE_TTL_LIVE = 60          # 实时卡片 60 秒
_CACHE_TTL_TREND = 180        # 小时趋势 3 分钟
_CACHE_TTL_RECENT_DAYS = 900  # 近几日列表 15 分钟
_LIVE_MIN_TABLE_READY = False


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
    return JsonResponse(
        {
            "message": "注册成功",
            "username": user.username,
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
        }
    )


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
    return JsonResponse(
        {
            "message": "登录成功",
            "username": user.username,
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
        }
    )


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

    return JsonResponse(
        {
            "message": "管理员登录成功",
            "username": user.username,
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
        }
    )


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

    return JsonResponse(
        {
            "message": "ok",
            "data": {
                "username": user.username,
                "email": user.email or "",
                "display_name": profile.display_name or "",
                "phone": profile.phone or "",
                "bio": profile.bio or "",
                "avatar_url": _avatar_url(request, profile),
                "is_staff": bool(user.is_staff),
                "is_superuser": bool(user.is_superuser),
            },
        }
    )


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

    return JsonResponse(
        {
            "message": "头像上传成功",
            "data": {
                "avatar_url": _avatar_url(request, profile),
            },
        }
    )


def _safe_int(value, default=None, min_value=None, max_value=None):
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    if min_value is not None:
        num = max(min_value, num)
    if max_value is not None:
        num = min(max_value, num)
    return num


def _pagination_meta(paginator, page_obj):
    return {
        "total": paginator.count,
        "page": page_obj.number,
        "page_size": paginator.per_page,
        "total_pages": paginator.num_pages,
    }


def _fetch_part_rows(table_name):
    if table_name not in ALLOWED_PART_TABLES:
        raise ValueError("非法表名")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        raise ValueError("非法表名")

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id, name, value FROM `{table_name}` ORDER BY id")
        rows = cursor.fetchall()

    return [
        {
            "id": int(item[0]),
            "name": item[1],
            "value": float(item[2]) if item[2] is not None else None,
        }
        for item in rows
    ]


def _weather_to_dict(item):
    return {
        "id": item.id,
        "record_date": item.record_date.isoformat() if item.record_date else None,
        "max_temperature": item.max_temperature,
        "min_temperature": item.min_temperature,
        "weather": item.weather,
        "wind_direction": item.wind_direction,
        "city": item.city,
        "weekday": item.weekday,
        "aqi": item.aqi,
        "aqi_level": item.aqi_level,
        "wind_power": item.wind_power,
    }


def _air_to_dict(item):
    return {
        "id": item.id,
        "record_date": item.record_date.isoformat() if item.record_date else None,
        "quality_level": item.quality_level,
        "aqi_index": item.aqi_index,
        "aqi_rank": item.aqi_rank,
        "pm25": float(item.pm25) if item.pm25 is not None else None,
        "pm10": float(item.pm10) if item.pm10 is not None else None,
        "so2": float(item.so2) if item.so2 is not None else None,
        "no2": float(item.no2) if item.no2 is not None else None,
        "co": float(item.co) if item.co is not None else None,
        "o3": float(item.o3) if item.o3 is not None else None,
        "city": item.city,
    }


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def weather_data_list_view(request):
    if request.method == "POST":
        data = _parse_body(request)
        item = WeatherData.objects.create(
            record_date=_parse_iso_date(data.get("record_date")),
            max_temperature=_safe_int(data.get("max_temperature")),
            min_temperature=_safe_int(data.get("min_temperature")),
            weather=str(data.get("weather", "")).strip()[:64],
            wind_direction=str(data.get("wind_direction", "")).strip()[:32],
            city=str(data.get("city", "")).strip()[:64],
            weekday=str(data.get("weekday", "")).strip()[:16],
            aqi=_safe_int(data.get("aqi")),
            aqi_level=str(data.get("aqi_level", "")).strip()[:32],
            wind_power=str(data.get("wind_power", "")).strip()[:32],
        )
        return JsonResponse({"message": "新增成功", "data": _weather_to_dict(item)})

    if request.method == "PUT":
        data = _parse_body(request)
        item_id = _safe_int(data.get("id"))
        item = WeatherData.objects.filter(id=item_id).first()
        if item is None:
            return JsonResponse({"message": "记录不存在"}, status=404)
        item.record_date = _parse_iso_date(data.get("record_date"))
        item.max_temperature = _safe_int(data.get("max_temperature"))
        item.min_temperature = _safe_int(data.get("min_temperature"))
        item.weather = str(data.get("weather", "")).strip()[:64]
        item.wind_direction = str(data.get("wind_direction", "")).strip()[:32]
        item.city = str(data.get("city", "")).strip()[:64]
        item.weekday = str(data.get("weekday", "")).strip()[:16]
        item.aqi = _safe_int(data.get("aqi"))
        item.aqi_level = str(data.get("aqi_level", "")).strip()[:32]
        item.wind_power = str(data.get("wind_power", "")).strip()[:32]
        item.save()
        return JsonResponse({"message": "更新成功", "data": _weather_to_dict(item)})

    if request.method == "DELETE":
        item_id = _safe_int(request.GET.get("id"))
        item = WeatherData.objects.filter(id=item_id).first()
        if item is None:
            return JsonResponse({"message": "记录不存在"}, status=404)
        item.delete()
        return JsonResponse({"message": "删除成功"})

    city = str(request.GET.get("city", "")).strip()
    weather = str(request.GET.get("weather", "")).strip()
    aqi_level = str(request.GET.get("aqi_level", "")).strip()
    start_date = str(request.GET.get("start_date", "")).strip()
    end_date = str(request.GET.get("end_date", "")).strip()

    page = _safe_int(request.GET.get("page"), default=1, min_value=1) or 1
    page_size = _safe_int(request.GET.get("page_size"), default=20, min_value=1, max_value=200) or 20

    queryset = WeatherData.objects.all().order_by("-record_date", "id")
    if city:
        queryset = queryset.filter(city__icontains=city)
    if weather:
        queryset = queryset.filter(weather__icontains=weather)
    if aqi_level:
        queryset = queryset.filter(aqi_level__icontains=aqi_level)
    if start_date:
        queryset = queryset.filter(record_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(record_date__lte=end_date)

    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    results = [_weather_to_dict(item) for item in page_obj.object_list]

    return JsonResponse({"results": results, **_pagination_meta(paginator, page_obj)})


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def air_quality_data_list_view(request):
    if request.method == "POST":
        data = _parse_body(request)
        item = AirQualityData.objects.create(
            record_date=_parse_iso_date(data.get("record_date")),
            quality_level=str(data.get("quality_level", "")).strip()[:32],
            aqi_index=_safe_int(data.get("aqi_index")),
            aqi_rank=_safe_int(data.get("aqi_rank")),
            pm25=data.get("pm25") or None,
            pm10=data.get("pm10") or None,
            so2=data.get("so2") or None,
            no2=data.get("no2") or None,
            co=data.get("co") or None,
            o3=data.get("o3") or None,
            city=str(data.get("city", "")).strip()[:64],
        )
        return JsonResponse({"message": "新增成功", "data": _air_to_dict(item)})

    if request.method == "PUT":
        data = _parse_body(request)
        item_id = _safe_int(data.get("id"))
        item = AirQualityData.objects.filter(id=item_id).first()
        if item is None:
            return JsonResponse({"message": "记录不存在"}, status=404)
        item.record_date = _parse_iso_date(data.get("record_date"))
        item.quality_level = str(data.get("quality_level", "")).strip()[:32]
        item.aqi_index = _safe_int(data.get("aqi_index"))
        item.aqi_rank = _safe_int(data.get("aqi_rank"))
        item.pm25 = data.get("pm25") or None
        item.pm10 = data.get("pm10") or None
        item.so2 = data.get("so2") or None
        item.no2 = data.get("no2") or None
        item.co = data.get("co") or None
        item.o3 = data.get("o3") or None
        item.city = str(data.get("city", "")).strip()[:64]
        item.save()
        return JsonResponse({"message": "更新成功", "data": _air_to_dict(item)})

    if request.method == "DELETE":
        item_id = _safe_int(request.GET.get("id"))
        item = AirQualityData.objects.filter(id=item_id).first()
        if item is None:
            return JsonResponse({"message": "记录不存在"}, status=404)
        item.delete()
        return JsonResponse({"message": "删除成功"})

    city = str(request.GET.get("city", "")).strip()
    quality_level = str(request.GET.get("quality_level", "")).strip()
    start_date = str(request.GET.get("start_date", "")).strip()
    end_date = str(request.GET.get("end_date", "")).strip()
    min_aqi = _safe_int(request.GET.get("min_aqi"))
    max_aqi = _safe_int(request.GET.get("max_aqi"))

    page = _safe_int(request.GET.get("page"), default=1, min_value=1) or 1
    page_size = _safe_int(request.GET.get("page_size"), default=20, min_value=1, max_value=200) or 20

    queryset = AirQualityData.objects.all().order_by("-record_date", "id")
    if city:
        queryset = queryset.filter(city__icontains=city)
    if quality_level:
        queryset = queryset.filter(quality_level__icontains=quality_level)
    if start_date:
        queryset = queryset.filter(record_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(record_date__lte=end_date)
    if min_aqi is not None:
        queryset = queryset.filter(aqi_index__gte=min_aqi)
    if max_aqi is not None:
        queryset = queryset.filter(aqi_index__lte=max_aqi)

    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    results = [_air_to_dict(item) for item in page_obj.object_list]

    return JsonResponse({"results": results, **_pagination_meta(paginator, page_obj)})


@csrf_exempt
@require_http_methods(["POST"])
def aqi_index_predict_view(request):
    return JsonResponse({"message": "insufficient data: prediction is disabled until a model is trained from persisted provider observations."}, status=503)


@require_http_methods(["GET"])
def analysis_visualization_view(request):
    analyses_payload = []
    for analysis in ANALYSIS_DEFINITIONS:
        charts_payload = []
        for chart in analysis["charts"]:
            charts_payload.append(
                {
                    "key": chart["key"],
                    "title": chart["title"],
                    "table": chart["table"],
                    "type": chart["type"],
                    "rows": _fetch_part_rows(chart["table"]),
                }
            )
        analyses_payload.append(
            {
                "key": analysis["key"],
                "title": analysis["title"],
                "charts": charts_payload,
            }
        )

    return JsonResponse({"analyses": analyses_payload})


@require_http_methods(["GET"])
def weather_filter_options_view(request):
    cities = (
        WeatherData.objects.exclude(city__isnull=True)
        .exclude(city__exact="")
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    weathers = (
        WeatherData.objects.exclude(weather__isnull=True)
        .exclude(weather__exact="")
        .values_list("weather", flat=True)
        .distinct()
        .order_by("weather")
    )
    aqi_levels = (
        WeatherData.objects.exclude(aqi_level__isnull=True)
        .exclude(aqi_level__exact="")
        .values_list("aqi_level", flat=True)
        .distinct()
        .order_by("aqi_level")
    )
    return JsonResponse(
        {
            "cities": list(cities),
            "weathers": list(weathers),
            "aqi_levels": list(aqi_levels),
        }
    )

