from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.core.cache import cache

from learngaugeapis.models.user import User

class UserAuthentication(BaseAuthentication):
    def authenticate(self, request):
        bearer_token = request.headers.get("Authorization", None)

        if bearer_token is None:
            raise NotAuthenticated("Missing token!")
        
        token = bearer_token.replace("Bearer ", "")

        try:
            user_id = AccessToken(token=token).payload.get("user_id", None)
            jti = AccessToken(token=token).payload["jti"]
        except TokenError:
            raise AuthenticationFailed("Verify token failed!")

        if not bool(cache.has_key(f"web_session:{user_id}:access:{jti}")):
            raise AuthenticationFailed("Verify token failed!")
        
        account = User.objects.get(id=user_id)
        
        return (account, token)