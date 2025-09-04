from rest_framework.viewsets import ViewSet
from rest_framework import status
from learngaugeapis.const.clo_types import CLOType
from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.middlewares.authentication import UserAuthentication

class CLOTypeView(ViewSet):
    authentication_classes = [UserAuthentication]

    def list(self, request):
        clo_types = CLOType.all()
        return RestResponse(status=status.HTTP_200_OK, data=clo_types).response