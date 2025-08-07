import logging
import threading
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework import exceptions
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from learngaugeapis.errors.exceptions import UnVerifiedException
from learngaugeapis.helpers.otp import generate_otp, verify_otp
from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.send_html_email import send_html_template_email
from learngaugeapis.models.user import User, UserStatus
from learngaugeapis.serializers.user import VerifyUserSerializer

class AuthView(viewsets.ViewSet, TokenObtainPairView):
    authentication_classes = ()

    @action(methods=["POST"], detail=False, url_path="token")
    def get_token(self, request: Request, *args, **kwargs):
        try:
            logging.getLogger().info("AuthView.get_token req=%s", request.data)
            response = super().post(request, *args, **kwargs)
            logging.getLogger().info("AuthView.get_token res=%s", response.data)

            return RestResponse(
                data={
                    **response.data
                },
                status=status.HTTP_200_OK
            ).response
        except serializers.ValidationError as e:
            logging.getLogger().error("AuthView.get_token ValidationError err=%s", str(e))
            return RestResponse(message="Dữ liệu đầu vào không hợp lệ!", status=status.HTTP_400_BAD_REQUEST).response
        
        except UnVerifiedException as _:
            _email = request.data["email"]
            _otp = generate_otp(6, "verify_account", _email)
            self.__send_otp_mail(_email, _otp)
            return RestResponse(message="Tài khoản chưa được xác thực", code="account_unverify", status=status.HTTP_400_BAD_REQUEST).response
        
        except exceptions.AuthenticationFailed as _:
            return RestResponse(message="Thông tin tài khoản không chính xác!", status=status.HTTP_400_BAD_REQUEST).response
        
        except exceptions.PermissionDenied as _:
            return RestResponse(message="Tài khoản đã bị khóa!", status=status.HTTP_400_BAD_REQUEST).response

    def __send_otp_mail(self, email, otp):
        def send_mail():
            try:
                send_html_template_email(
                    to=[email],
                    subject="[Learn Gauge] Your verification code!",
                    template_name="otp.html",
                    context={
                        "otp": otp
                    }
                )
            except Exception as e:
                logging.getLogger().exception("AuthView.__send_otp_mail exc=%s", e)

        thread = threading.Thread(target=send_mail)
        thread.daemon = True
        thread.start()

    @action(methods=["POST"], detail=False, url_path="verify")
    @swagger_auto_schema(request_body=VerifyUserSerializer)
    def verify_account(self, request):
        try:
            logging.getLogger().info("AuthView.verify_account req=%s", request.data)
            validate = VerifyUserSerializer(data=request.data)

            if not validate.is_valid():
                return RestResponse(data=validate.errors, status=status.HTTP_400_BAD_REQUEST, message="Vui lòng kiểm tra lại dữ liệu!").response
            
            validated_data = validate.validated_data
            email = validated_data["email"]
            otp = validated_data["otp"]
            
            if not verify_otp("verify_account", email, otp):
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="OTP không chính xác hoặc đã hết hạn!").response

            try:
                account = User.objects.get(email=email)
                
                if account.status != UserStatus.UNVERIFIED:
                    return RestResponse(message="Không thể kích hoạt tài khoản đã được xác thực!", status=status.HTTP_400_BAD_REQUEST).response
            
                account.status = UserStatus.ACTIVATED
                account.save(update_fields=["status"])

                return RestResponse(status=status.HTTP_200_OK).response
            except User.DoesNotExist:
                return RestResponse(status=status.HTTP_404_NOT_FOUND).response

        except Exception as e:
            logging.getLogger().exception("AuthView.verify_account exc=%s, req=%s", e, request.data)
            return RestResponse(data={"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR).response