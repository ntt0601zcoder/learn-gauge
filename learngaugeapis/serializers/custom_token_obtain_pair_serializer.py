import json
from typing import Any, Dict
from django.core.cache import cache
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.settings import api_settings as jwt_configs

from learngaugeapis.errors.exceptions import UnVerifiedException
from learngaugeapis.models.user import UserStatus
from learngaugeapis.serializers.user import UserSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    __prefix_key = "web_session"

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        try:
            validated_data = super().validate(attrs)
            refresh_jti = self.token_class(validated_data["refresh"]).payload["jti"]
            access_jti = self.token_class.access_token_class(validated_data["access"]).payload["jti"]
            _session_data = UserSerializer(self.user, many=False, exclude=["password"]).data
            self.__save_session(self.user.id, _session_data, access_jti, refresh_jti)
            return {**validated_data, "user_info": _session_data}
        except AuthenticationFailed as e:
            if self.user is None:
                raise e
            
            if self.user.status == UserStatus.BLOCKED:
                raise PermissionDenied("Non activated account!")
            elif self.user.status == UserStatus.UNVERIFIED:
                raise UnVerifiedException("Unverified account!")
            
            raise e
        
    def __save_session(self, key: Any, data: Any, access_jti: str, refresh_jti: str):
        self.__remove_session(key, "access")
        self.__remove_session(key, "refresh")
        cache.set(f"{self.__prefix_key}:{str(key)}:access:{access_jti}", json.dumps(data), jwt_configs.ACCESS_TOKEN_LIFETIME.seconds)
        cache.set(f"{self.__prefix_key}:{str(key)}:refresh:{refresh_jti}", json.dumps(data), jwt_configs.ACCESS_TOKEN_LIFETIME.seconds)

    def __remove_session(self, key: Any, type):
        cache.delete_many(cache.keys(f"{self.__prefix_key}:{str(key)}:{type}:*"))
        