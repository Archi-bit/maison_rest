from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def health(request):
    return JsonResponse({"status": "ok", "project": "MAISON Restaurant"})


@extend_schema(
    responses=inline_serializer(
        name="HealthResponse",
        fields={
            "status": serializers.CharField(),
            "project": serializers.CharField(),
        },
    )
)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_health(request):
    return Response({"status": "ok", "project": "MAISON Restaurant"})
