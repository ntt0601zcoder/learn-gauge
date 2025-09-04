import logging
import datetime
from rest_framework import status
from rest_framework.viewsets import ViewSet
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.paginator import CustomPageNumberPagination
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.middlewares.permissions import IsRoot
from learngaugeapis.models.course_class import Class
from learngaugeapis.serializers.course_class import ClassSerializer, CreateClassSerializer, UpdateClassSerializer

class ClassView(ViewSet):
    authentication_classes = [UserAuthentication]
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsRoot()]
        return []
    
    @swagger_auto_schema(
        responses={200: ClassSerializer(many=True)},
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
            )
        ]
    )
    def list(self, request):
        try:
            logging.getLogger().info("ClassView.list req=%s", request.query_params)
            classes = Class.objects.filter(deleted_at=None).order_by("-created_at")
            classes = self.paginator.paginate_queryset(classes, request)
            serializer = ClassSerializer(classes, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=self.paginator.get_paginated_data(serializer.data)).response
        except Exception as e:
            logging.getLogger().exception("ClassView.list exc=%s, req=%s", str(e), request.query_params)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("ClassView.retrieve pk=%s", pk)
            class_ = Class.objects.get(id=pk, deleted_at=None)
            serializer = ClassSerializer(class_)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Class.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("ClassView.retrieve exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=CreateClassSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("ClassView.create req=%s", request.data)
            serializer = CreateClassSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response

            validated_data = serializer.validated_data

            if Class.objects.filter(code=validated_data.get('code'), deleted_at=None).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã lớp đã tồn tại!").response

            _class = Class.objects.create(**validated_data)
            return RestResponse(status=status.HTTP_201_CREATED, data=ClassSerializer(_class).data).response
        except Exception as e:
            logging.getLogger().exception("ClassView.create exc=%s, req=%s", str(e), request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=UpdateClassSerializer)
    def update(self, request, pk=None):
        try:
            logging.getLogger().info("ClassView.update pk=%s, req=%s", pk, request.data)
            _class = Class.objects.get(id=pk, deleted_at=None)
            serializer = UpdateClassSerializer(_class, data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response

            validated_data = serializer.validated_data

            if "code" in validated_data and Class.objects.filter(code=validated_data.get('code'), deleted_at=None).exclude(id=_class.id).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã lớp đã tồn tại!").response
            
            for key, value in validated_data.items():
                setattr(_class, key, value)

            _class.save()

            return RestResponse(status=status.HTTP_200_OK, data=ClassSerializer(_class).data).response
        except Class.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("ClassView.update exc=%s, pk=%s, req=%s", str(e), pk, request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("ClassView.destroy pk=%s", pk)
            _class = Class.objects.get(id=pk, deleted_at=None)
            _class.deleted_at = datetime.datetime.now()
            _class.save()
            return RestResponse(status=status.HTTP_200_OK).response
        except Class.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("ClassView.destroy exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response