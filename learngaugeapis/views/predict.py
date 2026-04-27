import logging
import os
import threading

from decouple import config
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

from learngaugeapis.helpers.response import RestResponse
from learngaugeapis.ml_pipeline import (
    get_analysis_pipeline,
    get_predict_pipeline,
    reload_pipelines,
)
from learngaugeapis.serializers.predict import (
    AnalyzeClassSerializer,
    PredictStudentSerializer,
)

# ---------------------------------------------------------------------------
# Graceful import of ml_clo exceptions so the module loads even when the
# package is not yet installed.
# ---------------------------------------------------------------------------
try:
    from ml_clo.utils.exceptions import (  # noqa: PLC0415
        DataValidationError,
        ModelLoadError,
        PredictionError,
    )
except ImportError:
    ModelLoadError = Exception
    DataValidationError = ValueError
    PredictionError = RuntimeError


_503_MESSAGE = "Mô hình AI chưa sẵn sàng, vui lòng thử lại sau!"


class PredictView(ViewSet):
    # ------------------------------------------------------------------
    # 1. Predict individual student
    # ------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Dự đoán điểm CLO cho một sinh viên theo môn học và giảng viên",
        request_body=PredictStudentSerializer,
        responses={
            200: openapi.Response("Kết quả dự đoán"),
            400: openapi.Response("Dữ liệu không hợp lệ"),
            503: openapi.Response("Mô hình chưa sẵn sàng"),
        },
    )
    @action(detail=False, methods=["post"], url_path="student")
    def predict_student(self, request):
        try:
            serializer = PredictStudentSerializer(data=request.data)
            if not serializer.is_valid():
                return RestResponse(
                    status=status.HTTP_400_BAD_REQUEST, data=serializer.errors
                ).response

            data = serializer.validated_data
            student_id = data["student_id"]
            subject_id = data["subject_id"]
            lecturer_id = data["lecturer_id"]

            logging.getLogger().info(
                "PredictView.predict_student student_id=%s subject_id=%s lecturer_id=%s",
                student_id,
                subject_id,
                lecturer_id,
            )

            pipeline = get_predict_pipeline()
            if pipeline is None:
                return RestResponse(
                    status=status.HTTP_503_SERVICE_UNAVAILABLE, message=_503_MESSAGE
                ).response

            output = pipeline.predict(
                student_id=student_id,
                subject_id=subject_id,
                lecturer_id=lecturer_id,
            )
            return RestResponse(data=output.to_dict(), status=status.HTTP_200_OK).response

        except DataValidationError as e:
            logging.getLogger().warning(
                "PredictView.predict_student validation exc=%s data=%s",
                str(e),
                request.data,
            )
            return RestResponse(
                status=status.HTTP_400_BAD_REQUEST, message="Không đủ dữ liệu để dự đoán!"
            ).response
        except (ModelLoadError, PredictionError) as e:
            logging.getLogger().error(
                "PredictView.predict_student pipeline exc=%s data=%s",
                str(e),
                request.data,
            )
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response
        except Exception as e:
            logging.getLogger().exception(
                "PredictView.predict_student exc=%s data=%s",
                str(e),
                request.data,
            )
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    # ------------------------------------------------------------------
    # 2. Analyze class performance
    # ------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Phân tích kết quả học tập toàn lớp theo môn học và giảng viên",
        request_body=AnalyzeClassSerializer,
        responses={
            200: openapi.Response("Kết quả phân tích lớp"),
            400: openapi.Response("Dữ liệu không hợp lệ"),
            503: openapi.Response("Mô hình chưa sẵn sàng"),
        },
    )
    @action(detail=False, methods=["post"], url_path="class")
    def analyze_class(self, request):
        try:
            serializer = AnalyzeClassSerializer(data=request.data)
            if not serializer.is_valid():
                return RestResponse(
                    status=status.HTTP_400_BAD_REQUEST, data=serializer.errors
                ).response

            data = serializer.validated_data
            subject_id = data["subject_id"]
            lecturer_id = data["lecturer_id"]
            clo_scores = data["clo_scores"]

            logging.getLogger().info(
                "PredictView.analyze_class subject_id=%s lecturer_id=%s n_scores=%s",
                subject_id,
                lecturer_id,
                len(clo_scores),
            )

            pipeline = get_analysis_pipeline()
            if pipeline is None:
                return RestResponse(
                    status=status.HTTP_503_SERVICE_UNAVAILABLE, message=_503_MESSAGE
                ).response

            output = pipeline.analyze_class_from_scores(
                subject_id=subject_id,
                lecturer_id=lecturer_id,
                clo_scores=clo_scores,
            )
            return RestResponse(data=output.to_dict(), status=status.HTTP_200_OK).response

        except DataValidationError as e:
            logging.getLogger().warning(
                "PredictView.analyze_class validation exc=%s data=%s",
                str(e),
                request.data,
            )
            return RestResponse(
                status=status.HTTP_400_BAD_REQUEST, message="Không đủ dữ liệu để phân tích!"
            ).response
        except Exception as e:
            logging.getLogger().exception(
                "PredictView.analyze_class exc=%s data=%s",
                str(e),
                request.data,
            )
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response

    # ------------------------------------------------------------------
    # 3. Trigger model retraining  (root / admin only)
    # ------------------------------------------------------------------

    @swagger_auto_schema(
        operation_description="Kích hoạt huấn luyện lại mô hình AI (chỉ dành cho admin)",
        responses={
            202: openapi.Response("Bắt đầu huấn luyện"),
            400: openapi.Response("Chưa cấu hình đường dẫn mô hình"),
            500: openapi.Response("Lỗi hệ thống"),
        },
    )
    @action(detail=False, methods=["post"], url_path="train")
    def train(self, request):
        try:
            logging.getLogger().info("PredictView.train triggered by user=%s", getattr(request.user, "id", "anonymous"))

            model_path = config("ML_MODEL_PATH", default=None)
            data_dir = config("ML_DATA_DIR", default=None)

            if not model_path or not data_dir:
                return RestResponse(
                    status=status.HTTP_400_BAD_REQUEST,
                    message="Chưa cấu hình ML_MODEL_PATH hoặc ML_DATA_DIR!",
                ).response

            thread = threading.Thread(
                target=_run_training,
                args=(model_path, data_dir),
                daemon=True,
            )
            thread.start()

            return RestResponse(
                status=status.HTTP_202_ACCEPTED,
                message="Quá trình huấn luyện đã bắt đầu!",
            ).response

        except Exception as e:
            logging.getLogger().exception("PredictView.train exc=%s", str(e))
            return RestResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR).response


# ---------------------------------------------------------------------------
# Internal training runner (executed in a background thread)
# ---------------------------------------------------------------------------

def _run_training(model_path: str, data_dir: str):
    try:
        from ml_clo import TrainingPipeline  # noqa: PLC0415

        pipeline = TrainingPipeline()
        result = pipeline.run(
            exam_scores_path=os.path.join(data_dir, "DiemTong.xlsx"),
            output_path=model_path,
            conduct_scores_path=os.path.join(data_dir, "diemrenluyen.xlsx"),
            demographics_path=os.path.join(data_dir, "nhankhau.xlsx"),
            teaching_methods_path=os.path.join(data_dir, "PPGDfull.xlsx"),
            assessment_methods_path=os.path.join(data_dir, "PPDGfull.xlsx"),
            study_hours_path=os.path.join(data_dir, "tuhoc.xlsx"),
            attendance_path=os.path.join(data_dir, "Dữ liệu điểm danh Khoa FIRA.xlsx"),
        )
        logging.getLogger().info("PredictView._run_training completed result=%s", result)

        # Hot-reload prediction / analysis pipelines with the new model
        reload_pipelines(model_path, data_dir)
    except Exception as e:
        logging.getLogger().exception("PredictView._run_training failed exc=%s", str(e))
