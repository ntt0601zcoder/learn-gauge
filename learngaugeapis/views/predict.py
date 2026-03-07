import os
import logging
from datetime import datetime
from rest_framework.viewsets import ViewSet
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.helpers.paginator import CustomPageNumberPagination
from learngaugeapis.middlewares.authentication import UserAuthentication
from learngaugeapis.models.exam_result import ExamResult

from ml_clo import PredictionPipeline

BASE_DIR = "/Users/thuan.nguyen.trong/Desktop/workspace/thuannt/learn-gauge/data"
MODEL_PATH = "/Users/thuan.nguyen.trong/Desktop/workspace/thuannt/modelAI/models/model.joblib"

class PredictView(ViewSet):
    
    @action(detail=False, methods=['get'], url_path=r'subject/(?P<subject_code>[a-zA-Z0-9]+)/student/(?P<student_code>\d+)')
    def predict_student(self, request, subject_code, student_code):
        try:
            logging.getLogger().info("PredictView.predict_student subject_code=%s, student_code=%s", subject_code, student_code)
            
            if not student_code.isdigit():
                return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Mã sinh viên không hợp lệ!").response
            
            results = ExamResult.objects.filter(student_code=student_code, exam__course_class__course__code=subject_code)
            if not results.exists():
                return RestResponse(status=status.HTTP_404_NOT_FOUND).response
            
            predcitor = PredictionPipeline(
                model_path=MODEL_PATH,
                
            )
            result = predcitor.predict(
                student_id=int(student_code),
                subject_id=subject_code,
                lecturer_id=results.first().exam.course_class.teacher.card_id,
                exam_scores_path=os.path.join(BASE_DIR, "DiemTong.xlsx"),
                conduct_scores_path=os.path.join(BASE_DIR, "diemrenluyen.xlsx"),
                demographics_path=os.path.join(BASE_DIR, "nhankhau.xlsx"),
                teaching_methods_path=os.path.join(BASE_DIR, "PPGDfull.xlsx"),
                assessment_methods_path=os.path.join(BASE_DIR, "PPDGfull.xlsx"),
                study_hours_path=os.path.join(BASE_DIR, "tuhoc.xlsx"),
            )
            return RestResponse(data=result.to_dict(), status=status.HTTP_200_OK).response
        except ValueError as e:
            logging.getLogger().exception("PredictView.predict_student exc=%s, subject_code=%s, student_code=%s", str(e), subject_code, student_code)
            return RestResponse(status=status.HTTP_400_BAD_REQUEST, message="Không đủ dữ liệu để dự đoán!").response
        except Exception as e:
            logging.getLogger().exception("PredictView.predict_student exc=%s, subject_code=%s, student_code=%s", str(e), subject_code, student_code)
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    