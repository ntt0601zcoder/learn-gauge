import logging
from datetime import datetime
from rest_framework.viewsets import ViewSet
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from learngaugeapis.models.clo_type import CLOType
from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.serializers.clo_type import CreateCLOTypeSerializer, CLOTypeSerializer, UpdateCLOTypeSerializer
from learngaugeapis.middlewares.permissions import IsRoot
from learngaugeapis.helpers.paginator import CustomPageNumberPagination


class CLOTypeView(ViewSet):
    authentication_classes = [UserAuthentication]
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsRoot()]
        return []

    @swagger_auto_schema(
        responses={200: CLOTypeSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                name="size",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="page",
                in_="query",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                name="name",
                in_="query",
                type=openapi.TYPE_STRING,
                required=False
            )
        ]
    )   
    def list(self, request):
        try:
            logging.getLogger().info("CLOTypeView.list req=%s", request.query_params)
            clo_types = CLOType.objects.filter(deleted_at=None).order_by("-created_at")

            name = request.query_params.get("name", None)
            if name:
                clo_types = clo_types.filter(name__icontains=name)

            clo_types = self.paginator.paginate_queryset(clo_types, request)
            return RestResponse(status=status.HTTP_200_OK, data=CLOTypeSerializer(clo_types, many=True).data).response
        except Exception as e:
            logging.getLogger().exception("CLOTypeView.list exc=%s, req=%s", str(e), request.query_params)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("CLOTypeView.retrieve pk=%s", pk)
            clo_type : CLOType = CLOType.objects.get(pk=pk, deleted_at=None)
            return RestResponse(status=status.HTTP_200_OK, data=CLOTypeSerializer(clo_type).data).response
        except CLOType.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("CLOTypeView.retrieve exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    @swagger_auto_schema(request_body=CreateCLOTypeSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("CLOTypeView.create req=%s", request.data)
            serializer = CreateCLOTypeSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            clo_type : CLOType = CLOType.objects.create(**serializer.validated_data)
            
            return RestResponse(status=status.HTTP_201_CREATED, data=CLOTypeSerializer(clo_type).data).response
        except Exception as e:
            logging.getLogger().exception("CLOTypeView.create exc=%s, req=%s", str(e), request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    @swagger_auto_schema(request_body=UpdateCLOTypeSerializer)
    def update(self, request, pk=None):
        try:
            logging.getLogger().info("CLOTypeView.update pk=%s, req=%s", pk, request.data)
            clo_type : CLOType = CLOType.objects.get(pk=pk, deleted_at=None)
            serializer = UpdateCLOTypeSerializer(clo_type, data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            for key, value in serializer.validated_data.items():
                setattr(clo_type, key, value)

            clo_type.save()
            
            return RestResponse(status=status.HTTP_200_OK, data=CLOTypeSerializer(clo_type).data).response
        except CLOType.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("CLOTypeView.update exc=%s, pk=%s, req=%s", str(e), pk, request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("CLOTypeView.destroy pk=%s", pk)
            clo_type : CLOType = CLOType.objects.get(pk=pk, deleted_at=None)
            clo_type.deleted_at = datetime.now()
            clo_type.save()
            return RestResponse(status=status.HTTP_204_NO_CONTENT).response
        except CLOType.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("CLOTypeView.destroy exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response