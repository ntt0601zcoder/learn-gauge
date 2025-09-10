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
