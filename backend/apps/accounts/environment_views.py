from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .environment import CityResolutionError, ProviderError, get_realtime, history, resolve_city


@require_GET
def realtime_view(request):
    try:
        return JsonResponse({"data": get_realtime(request.GET.get("city"))})
    except CityResolutionError as exc:
        return JsonResponse({"error": {"code": "invalid_city", "message": str(exc)}}, status=400)
    except ProviderError as exc:
        return JsonResponse({"error": {"code": "environment_unavailable", "message": str(exc)}}, status=503)


@require_GET
def history_view(request):
    try:
        city = resolve_city(request.GET.get("city"))
    except CityResolutionError as exc:
        return JsonResponse({"error": {"code": "invalid_city", "message": str(exc)}}, status=400)
    try:
        limit = min(max(int(request.GET.get("limit", 100)), 1), 500)
    except ValueError:
        return JsonResponse({"error": {"code": "invalid_request", "message": "limit must be an integer."}}, status=400)
    return JsonResponse({"data": history(city, limit)})


@require_GET
def trend_view(request):
    try:
        city = resolve_city(request.GET.get("city"))
    except CityResolutionError as exc:
        return JsonResponse({"error": {"code": "invalid_city", "message": str(exc)}}, status=400)
    return JsonResponse({"data": list(reversed(history(city, 48)))})
