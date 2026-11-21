
from django.db import DatabaseError, connection
from django.http import JsonResponse

def health(request):
    """Liveness: Django process can respond."""
    return JsonResponse({
        "status": "ok",
        "service": "nicat-api",
    })

def readiness(request):
    """Readiness: Django can query PostgreSQL."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse(
            {"status": "unavailable"},
            status=503,
        )

    return JsonResponse({"status": "ready"})