import logging
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from learngaugeapis.helpers.response import RestResponse

class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description='System is healthy',
            ),
            503: openapi.Response(
                description='Service Unavailable',
            )
        }
    )
    def get(self, request):
        logging.getLogger().info("HealthCheckView.get")
        
        return RestResponse(
            status=status.HTTP_200_OK
        ).response
