import logging
from datetime import datetime
from rest_framework import status
from rest_framework.viewsets import ViewSet
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.paginator import CustomPageNumberPagination
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.middlewares.permissions import IsRoot
from learngaugeapis.models.major import Major
from learngaugeapis.serializers.major import MajorSerializer, CreateMajorSerializer, UpdateMajorSerializer

class MajorView(ViewSet):
    # authentication_classes = [UserAuthentication]
    paginator = CustomPageNumberPagination()

    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'destroy']:
    #         return [IsRoot()]
    #     return []
    
    @swagger_auto_schema(
        responses={200: MajorSerializer(many=True)},
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
                name="academic_program_id",
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
            logging.getLogger().info("MajorView.list req=%s", request.query_params)
            majors = Major.objects.filter(deleted_at=None).order_by("-created_at")

            academic_program_id = request.query_params.get("academic_program_id", None)
            if academic_program_id:
                majors = majors.filter(academic_program_id=academic_program_id)

            name = request.query_params.get("name", None)
            if name:
                majors = majors.filter(name__icontains=name)

            majors = self.paginator.paginate_queryset(majors, request)
            serializer = MajorSerializer(majors, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=self.paginator.get_paginated_data(serializer.data)).response
        except Exception as e:
            logging.getLogger().exception("MajorView.list exc=%s, req=%s", str(e), request.query_params)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("MajorView.retrieve pk=%s", pk)
            major = Major.objects.get(id=pk, deleted_at=None)
            serializer = MajorSerializer(major)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Major.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("MajorView.retrieve exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
    
    @swagger_auto_schema(request_body=CreateMajorSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("MajorView.create req=%s", request.data)
            serializer = CreateMajorSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            validated_data = serializer.validated_data

            if Major.objects.filter(code=validated_data.get('code'), deleted_at=None).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã ngành đào tạo đã được sử dụng!").response
            
            major = Major.objects.create(**validated_data)

            return RestResponse(status=status.HTTP_201_CREATED, data=MajorSerializer(major).data).response
        except Exception as e:
            logging.getLogger().exception("MajorView.create exc=%s, req=%s", str(e), request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    @swagger_auto_schema(request_body=UpdateMajorSerializer)
    def update(self, request, pk=None):
        try:
            logging.getLogger().info("MajorView.update pk=%s, req=%s", pk, request.data)
            major = Major.objects.get(id=pk, deleted_at=None)
            serializer = UpdateMajorSerializer(major, data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            validated_data = serializer.validated_data

            if 'code' in validated_data and Major.objects.filter(code=validated_data.get('code'), deleted_at=None).exclude(id=pk).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã ngành đào tạo đã được sử dụng!").response
            
            for key, value in validated_data.items():
                setattr(major, key, value)

            major.save()

            return RestResponse(status=status.HTTP_200_OK, data=MajorSerializer(major).data).response
        except Major.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("MajorView.update exc=%s, pk=%s, req=%s", str(e), pk, request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("MajorView.destroy pk=%s", pk)
            major = Major.objects.get(id=pk, deleted_at=None)
            major.deleted_at = datetime.now()
            major.save()
            return RestResponse(status=status.HTTP_200_OK).response
        except Major.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("MajorView.destroy exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response