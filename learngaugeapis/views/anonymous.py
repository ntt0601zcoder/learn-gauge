import logging
import random
import string
import threading
from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets, status
from rest_framework.decorators import action

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.send_html_email import send_html_template_email
from learngaugeapis.models.user import User

class AnonymousView(viewsets.ViewSet):
    def __generate_random_password(self, length=12):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def __send_password_reset_email(self, user: User, new_password: str):
        def send_mail():
            try:
                send_html_template_email(
                    to=[user.email],
                    subject="[Learn Gauge] Password reset notification",
                    template_name="password_reset.html",
                    context={
                        "user_name": user.fullname,
                        "new_password": new_password
                    }
                )
            except Exception as e:
                logging.getLogger().exception("AnonymousView.__send_password_reset_email exc=%s", e)

        thread = threading.Thread(target=send_mail)
        thread.daemon = True
        thread.start()

    @swagger_auto_schema(
        responses={
            200: 'Success',
            404: 'User not found',
            500: 'Internal Server Error'
        }
    )
    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        try:
            logging.getLogger().info("AnonymousView.reset_password pk=%s", pk)
            
            try:
                user = User.objects.get(pk=pk)
            except User.DoesNotExist:
                return RestResponse(
                    status=status.HTTP_404_NOT_FOUND,
                    message="Không tìm thấy người dùng!"
                ).response

            new_password = self.__generate_random_password()
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            self.__send_password_reset_email(user, new_password)
            
            return RestResponse(
                status=status.HTTP_200_OK,
                message="Mật khẩu đã được đặt lại và gửi đến email của người dùng!"
            ).response
            
        except Exception as e:
            logging.getLogger().exception("AnonymousView.reset_password exc=%s, pk=%s", e, pk)
            return RestResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Lỗi hệ thống khi đặt lại mật khẩu!"
            ).response