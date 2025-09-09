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
from learngaugeapis.models.course import Course
from learngaugeapis.serializers.course import CourseSerializer, CreateCourseSerializer, UpdateCourseSerializer

class CourseView(ViewSet):
    authentication_classes = [UserAuthentication]
    paginator = CustomPageNumberPagination()

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsRoot()]
        return []
    
    @swagger_auto_schema(
        responses={200: CourseSerializer(many=True)},
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
                name="major_id",
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
            logging.getLogger().info("CourseView.list req=%s", request.data)
            courses = Course.objects.filter(deleted_at=None).order_by("-created_at")

            major_id = request.query_params.get("major_id", None)
            if major_id:
                courses = courses.filter(major_id=major_id)

            name = request.query_params.get("name", None)
            if name:
                courses = courses.filter(name__icontains=name)

            courses = self.paginator.paginate_queryset(courses, request)
            serializer = CourseSerializer(courses, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=self.paginator.get_paginated_data(serializer.data)).response
        except Exception as e:
            logging.getLogger().exception("CourseView.list exc=%s, req=%s", str(e), request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("CourseView.retrieve pk=%s, req=%s", pk, request.data)
            course = Course.objects.get(id=pk, deleted_at=None)
            serializer = CourseSerializer(course)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Course.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("CourseView.retrieve exc=%s, pk=%s, req=%s", str(e), pk, request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=CreateCourseSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("CourseView.create req=%s", request.data)
            serializer = CreateCourseSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
                
            validated_data = serializer.validated_data

            if Course.objects.filter(code=validated_data.get('code'), deleted_at=None).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã khóa học đã tồn tại!").response

            course = Course.objects.create(**validated_data)

            return RestResponse(status=status.HTTP_201_CREATED, data=CourseSerializer(course).data).response
        except Exception as e:
            logging.getLogger().exception("CourseView.create exc=%s, req=%s", str(e), request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=UpdateCourseSerializer)
    def update(self, request, pk=None):
        try:
            logging.getLogger().info("CourseView.update pk=%s, req=%s", pk, request.data)
            course = Course.objects.get(id=pk, deleted_at=None)
            serializer = UpdateCourseSerializer(course, data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            validated_data = serializer.validated_data

            if "code" in validated_data and Course.objects.filter(code=validated_data.get('code'), deleted_at=None).exclude(id=course.id).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã khóa học đã tồn tại!").response
            
            for key, value in validated_data.items():
                setattr(course, key, value)

            course.save()

            return RestResponse(status=status.HTTP_200_OK, data=CourseSerializer(course).data).response
        except Course.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("CourseView.update exc=%s, pk=%s, req=%s", str(e), pk, request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("CourseView.destroy pk=%s", pk)
            course = Course.objects.get(id=pk, deleted_at=None)
            course.deleted_at = datetime.datetime.now()
            course.save()
            return RestResponse(status=status.HTTP_200_OK).response
        except Course.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("CourseView.destroy exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response