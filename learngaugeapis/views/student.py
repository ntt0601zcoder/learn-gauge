import logging
import random
import string
import threading
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets, status
from rest_framework.decorators import action

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.send_html_email import send_html_template_email
from learngaugeapis.models.user import User, UserRole, UserStatus
from learngaugeapis.serializers.user import CreateUserSerializer, UpdateUserSerializer, UserSerializer


class StudentView(viewsets.ViewSet):
    @swagger_auto_schema(request_body=CreateUserSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("StudentView.create req=%s", request.data)
            serializer = CreateUserSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(message="Vui lòng kiểm tra lại thông tin!", data=serializer.errors, status=status.HTTP_400_BAD_REQUEST).response
            
            validated_data = serializer.validated_data

            if User.objects.filter(email=validated_data["email"]).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Email đã được sử dụng bởi một tài khoản khác!").response
            
            if User.objects.filter(card_id=validated_data["card_id"]).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã sinh viên đã được sử dụng bởi một tài khoản khác!").response
            
            _password: str = validated_data.pop("password")
            
            user = User(**validated_data)
            user.role = UserRole.STUDENT
            user.status = UserStatus.UNVERIFIED
            user.set_password(_password)
            user.save()
            
            return RestResponse(message="Thành công!", status=status.HTTP_201_CREATED).response
        except Exception as e:
            logging.getLogger().exception("StudentView.create exc=%s, req=%s", e, request.data)
            return RestResponse(data={"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

