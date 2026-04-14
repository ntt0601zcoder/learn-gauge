import os
import threading
import logging

_predict_pipeline = None
_analysis_pipeline = None
_pipeline_lock = threading.Lock()
_initialized = False


def get_predict_pipeline():
    return _predict_pipeline


def get_analysis_pipeline():
    return _analysis_pipeline


def is_initialized():
    return _initialized


def initialize_pipelines(model_path: str, data_dir: str):
    """Load PredictionPipeline and AnalysisPipeline once at startup.

    Thread-safe: pipelines are swapped atomically so in-flight requests
    always see a consistent pair.
    """
    global _predict_pipeline, _analysis_pipeline, _initialized

    try:
        from ml_clo import PredictionPipeline, AnalysisPipeline  # noqa: PLC0415

        audit_log_path = os.environ.get("AUDIT_LOG_PATH")
        if audit_log_path:
            from ml_clo.utils.audit_log import set_audit_log_path  # noqa: PLC0415
            set_audit_log_path(audit_log_path)

        new_predict = PredictionPipeline(
            model_path=model_path,
            exam_scores_path=os.path.join(data_dir, "DiemTong.xlsx"),
            demographics_path=os.path.join(data_dir, "nhankhau.xlsx"),
            teaching_methods_path=os.path.join(data_dir, "PPGDfull.xlsx"),
            assessment_methods_path=os.path.join(data_dir, "PPDGfull.xlsx"),
            conduct_scores_path=os.path.join(data_dir, "diemrenluyen.xlsx"),
            attendance_path=os.path.join(data_dir, "Dữ liệu điểm danh Khoa FIRA.xlsx"),
            study_hours_path=os.path.join(data_dir, "tuhoc.xlsx"),
        )
        new_predict.load_model()

        new_analysis = AnalysisPipeline(model_path=model_path)
        new_analysis.load_model()

        with _pipeline_lock:
            _predict_pipeline = new_predict
            _analysis_pipeline = new_analysis
            _initialized = True

        logging.getLogger().info(
            "ml_pipeline: initialized model_path=%s data_dir=%s", model_path, data_dir
        )
    except ImportError:
        logging.getLogger().warning(
            "ml_pipeline: ml_clo package not installed — prediction features disabled"
        )
    except Exception as e:
        logging.getLogger().error("ml_pipeline: initialization failed exc=%s", str(e))


def reload_pipelines(model_path: str, data_dir: str):
    """Hot-reload both pipelines after a model retrain (atomic swap)."""
    initialize_pipelines(model_path, data_dir)
