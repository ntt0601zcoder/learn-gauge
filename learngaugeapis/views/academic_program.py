import logging
from datetime import datetime
from rest_framework import status
from rest_framework.viewsets import ViewSet
from drf_yasg.utils import swagger_auto_schema

from learngaugeapis.models.academic_program import AcademicProgram
from learngaugeapis.serializers.academic_program import AcademicProgramSerializer, CreateAcademicProgramSerializer, UpdateAcademicProgramSerializer
from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.middlewares.permissions import IsRoot

class AcademicProgramView(ViewSet):
    authentication_classes = [UserAuthentication]

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsRoot()]
        return []

    def list(self, request):
        try:
            logging.getLogger().info("AcademicProgramView.list req=%s", request.query_params)
            academic_programs = AcademicProgram.objects.filter(deleted_at=None)
            serializer = AcademicProgramSerializer(academic_programs, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Exception as e:
            logging.getLogger().exception("AcademicProgramView.list exc=%s, req=%s", str(e), request.query_params)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
    
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("AcademicProgramView.retrieve pk=%s", pk)
            academic_program = AcademicProgram.objects.get(id=pk, deleted_at=None)
            serializer = AcademicProgramSerializer(academic_program)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except AcademicProgram.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("AcademicProgramView.retrieve exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
    
    @swagger_auto_schema(request_body=CreateAcademicProgramSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("AcademicProgramView.create req=%s", request.data)
            serializer = CreateAcademicProgramSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response

            validated_data = serializer.validated_data

            if AcademicProgram.objects.filter(code=validated_data.get('code'), deleted_at=None).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã chương trình đào tạo đã được sử dụng!").response

            academic_program = AcademicProgram.objects.create(**validated_data)
            return RestResponse(status=status.HTTP_201_CREATED, data=AcademicProgramSerializer(academic_program).data).response
        except Exception as e:
            logging.getLogger().exception("AcademicProgramView.create exc=%s, req=%s", str(e), request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=UpdateAcademicProgramSerializer)
    def update(self, request, pk=None):
        try:
            logging.getLogger().info("AcademicProgramView.update pk=%s, req=%s", pk, request.data)
            academic_program = AcademicProgram.objects.get(id=pk, deleted_at=None)
            serializer = UpdateAcademicProgramSerializer(academic_program, data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response

            validated_data = serializer.validated_data

            if 'code' in validated_data and AcademicProgram.objects.filter(code=validated_data.get('code'), deleted_at=None).exclude(id=pk).exists():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã chương trình đào tạo đã được sử dụng!").response
            
            for key, value in validated_data.items():
                setattr(academic_program, key, value)

            academic_program.save()
            return RestResponse(status=status.HTTP_200_OK, data=AcademicProgramSerializer(academic_program).data).response
        except AcademicProgram.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("AcademicProgramView.update exc=%s, pk=%s, req=%s", str(e), pk, request.data)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("AcademicProgramView.destroy pk=%s", pk)
            academic_program = AcademicProgram.objects.get(id=pk, deleted_at=None)
            academic_program.deleted_at = datetime.now()
            academic_program.save()
            return RestResponse(status=status.HTTP_200_OK).response
        except AcademicProgram.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().exception("AcademicProgramView.destroy exc=%s, pk=%s", str(e), pk)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response