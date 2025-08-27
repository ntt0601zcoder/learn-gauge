import logging
from datetime import datetime
from rest_framework.viewsets import ViewSet
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.middlewares.permissions import IsRoot
from learngaugeapis.models.exam import Exam
from learngaugeapis.serializers.exam import CreateExamSerializer, ExamSerializer, UpdateExamSerializer

class ExamView(ViewSet):
    authentication_classes = [UserAuthentication]

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            return [IsRoot()]
        return []
    
    def list(self, request):
        try:
            logging.getLogger().info("ExamView.list params=%s", request.query_params)
            exams = Exam.objects.filter(deleted_at=None)
            serializer = ExamSerializer(exams, many=True)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Exception as e:
            logging.getLogger().error("ExamView.list exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def retrieve(self, request, pk=None):
        try:
            logging.getLogger().info("ExamView.retrieve pk=%s", pk)
            exam = Exam.objects.get(id=pk, deleted_at=None)
            serializer = ExamSerializer(exam)
            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Exam.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().error("ExamView.retrieve exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=CreateExamSerializer)
    def create(self, request):
        try:
            logging.getLogger().info("ExamView.create req=%s", request.data)
            serializer = CreateExamSerializer(data=request.data)

            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            exam = Exam.objects.create(**serializer.validated_data)
            serializer = ExamSerializer(exam)
            return RestResponse(status=status.HTTP_201_CREATED, data=serializer.data).response
        except Exception as e:
            logging.getLogger().error("ExamView.create exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    @swagger_auto_schema(request_body=UpdateExamSerializer)
    def update(self, request, pk=None):
        try:
            logging.getLogger().info("ExamView.update pk=%s, req=%s", pk, request.data)
            exam = Exam.objects.get(id=pk, deleted_at=None)
            serializer = UpdateExamSerializer(exam, data=request.data)
            
            if not serializer.is_valid():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors).response
            
            validated_data = serializer.validated_data

            for key, value in validated_data.items():
                setattr(exam, key, value)

            exam.save()
            serializer = ExamSerializer(exam)

            return RestResponse(status=status.HTTP_200_OK, data=serializer.data).response
        except Exam.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().error("ExamView.update exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        
    def destroy(self, request, pk=None):
        try:
            logging.getLogger().info("ExamView.destroy pk=%s", pk)
            exam = Exam.objects.get(id=pk, deleted_at=None)
            exam.deleted_at = datetime.now()
            exam.save()
            return RestResponse(status=status.HTTP_204_NO_CONTENT).response
        except Exam.DoesNotExist:
            return RestResponse(status=status.HTTP_404_NOT_FOUND).response
        except Exception as e:
            logging.getLogger().error("ExamView.destroy exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response