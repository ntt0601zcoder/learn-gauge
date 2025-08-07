from django.urls import path, include
from rest_framework import permissions

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.generators import OpenAPISchemaGenerator

class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema

schema_view = get_schema_view(
    openapi.Info(
        title="Learn Gauge",
        default_version='v1',
        description="Learn Gauge",
        contact=openapi.Contact(email="ntthuan060102.work@gmail.com"),
    ),
    generator_class=BothHttpAndHttpsSchemaGenerator,
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=()
)

urlpatterns = [
    path('apis/', include('learngaugeapis.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
