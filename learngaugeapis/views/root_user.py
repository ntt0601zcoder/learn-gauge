import logging
from tkinter import NO
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets, status

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.paginator import CustomPageNumberPagination
from learngaugeapis.middlewares.permissions import IsRoot
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.models.user import User, UserRole, UserStatus
from learngaugeapis.serializers.user import CreateUserSerializer, UserSerializer

class RootUserView(viewsets.ViewSet):
    authentication_classes = (UserAuthentication, )
    permission_classes = (IsRoot, )
    paginator = CustomPageNumberPagination()

    @swagger_auto_schema(request_body=CreateUserSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("RootUserView.create req=%s", request.data)
            validate = CreateUserSerializer(data=request.data)

            if not validate.is_valid():
                return RestResponse(validate.errors, status=status.HTTP_400_BAD_REQUEST, message="Vui lòng kiểm tra lại dữ liệu của bạn!").response
            
            validated_data = validate.validated_data
            
            if User.objects.filter(email=validated_data["email"]).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Email đã được sử dụng bởi một tài khoản khác!").response
            
            if User.objects.filter(card_id=validated_data["card_id"]).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã nhân viên đã được sử dụng bởi một tài khoản khác!").response
            
            _password: str = validated_data.pop("password")

            user = User(**validated_data)
            user.set_password(_password)
            user.status = UserStatus.UNVERIFIED
            user.role = UserRole.TEACHER
            user.save() 
                
            return RestResponse(message="Thành công!", status=status.HTTP_201_CREATED).response
        except Exception as e:
            logging.getLogger().exception("RootUserView.create exc=%s, req=%s", e, request.data)
            return RestResponse(data={"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    @swagger_auto_schema(
        responses={200: UserSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                name="role",
                in_="query",
                type=openapi.TYPE_STRING,
                required=False
            ),
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
            logging.getLogger().info("RootUserView.list req=%s", request.query_params)
            users = User.objects.all().order_by("-created_at")
            role = request.query_params.get("role", None)

            if role:
                users = users.filter(role=role)

            users = self.paginator.paginate_queryset(users, request)

            serializer = UserSerializer(users, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=self.paginator.get_paginated_data(serializer.data)).response
        except Exception as e:
            logging.getLogger().exception("RootUserView.list exc=%s, req=%s", e, request.query_params)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("RootUserView.retrieve pk=%s, req=%s", pk, request.query_params)
            user = User.objects.get(pk=pk)
            serializer = UserSerializer(user)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except User.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("RootUserView.retrieve exc=%s, pk=%s, req=%s", e, pk, request.query_params)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response