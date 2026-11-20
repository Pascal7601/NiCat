from django.http import JsonResponse

def health(request):
    # Liveness, not DB readiness; doesn't expose internal configuration.
    return JsonResponse({"status": "ok", "service": "nicat-api"})
