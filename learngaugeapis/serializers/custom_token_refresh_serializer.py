import json
from typing import Any, Dict
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ValidationError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_configs

from learngaugeapis.models.user import User
from learngaugeapis.serializers.user import UserSerializer

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    __prefix_key = "session"

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        refresh = attrs["refresh"]
        _validated_data = super().validate(attrs)
        user_id = RefreshToken(token=refresh).payload.get("user_id", None)
        jti = RefreshToken(token=refresh).payload.get("jti", None)

        if not cache.has_key(f"{self.__prefix_key}:{user_id}:refresh:{jti}"):
            raise ValidationError("Token expired!")

        refresh_payload = self.token_class(_validated_data["refresh"]).payload
        refresh_jti = refresh_payload["jti"]

        access_jti = self.token_class.access_token_class(_validated_data["access"]).payload["jti"]

        user_id = refresh_payload["user_id"]
        user = User.objects.get(id=user_id)
        _session_data = UserSerializer(user, many=False, exclude=["password"]).data
        self.__save_session(user.id, _session_data, access_jti, refresh_jti)
        
        return _validated_data
    
    def __save_session(self, key: Any, data: Any, access_jti: str, refresh_jti: str):
        self.__remove_session(key, "access")
        self.__remove_session(key, "refresh")
        cache.set(f"{self.__prefix_key}:{str(key)}:access:{access_jti}", json.dumps(data), jwt_configs.ACCESS_TOKEN_LIFETIME.seconds)
        cache.set(f"{self.__prefix_key}:{str(key)}:refresh:{refresh_jti}", json.dumps(data), jwt_configs.ACCESS_TOKEN_LIFETIME.seconds)

    def __remove_session(self, key: Any, type):
        cache.delete_many(cache.keys(f"{self.__prefix_key}:{str(key)}:{type}:*"))