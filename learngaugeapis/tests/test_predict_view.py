"""Unit tests for PredictView.

All DB queries and ml_clo pipeline calls are mocked so no real database
or model file is required.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from learngaugeapis.views.predict import PredictView


def _make_predict_output(score=3.85):
    """Return a mock IndividualAnalysisOutput."""
    out = MagicMock()
    out.to_dict.return_value = {
        "predicted_clo_score": score,
        "actual_clo_score": None,
        "summary": "Test summary",
        "reasons": [],
        "student_id": "19050006",
        "subject_id": "INF0823",
        "lecturer_id": "90316",
    }
    return out


def _make_analyze_output():
    """Return a mock ClassAnalysisOutput."""
    out = MagicMock()
    out.to_dict.return_value = {
        "summary": "Class summary",
        "subject_id": "INF0823",
        "lecturer_id": "90316",
        "total_students": 30,
        "common_reasons": [],
    }
    return out


# ---------------------------------------------------------------------------
# predict_student
# ---------------------------------------------------------------------------

class PredictStudentTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PredictView.as_view({"post": "predict_student"})

    def _post(self, body=None):
        if body is None:
            body = {
                "student_id": "19050006",
                "subject_id": "INF0823",
                "lecturer_id": "90316",
            }
        request = self.factory.post("/predict/student", body, format="json")
        return self.view(request)

    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_success(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(predict=MagicMock(return_value=_make_predict_output()))

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("predicted_clo_score", response.data["data"])
        mock_get_pipeline.return_value.predict.assert_called_once_with(
            student_id="19050006",
            subject_id="INF0823",
            lecturer_id="90316",
        )

    def test_predict_student_invalid_body_returns_400(self):
        response = self._post(body={"student_id": "19050006"})  # missing fields

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_pipeline_not_initialized(self, mock_get_pipeline):
        mock_get_pipeline.return_value = None

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_data_validation_error(self, mock_get_pipeline):
        from learngaugeapis.views.predict import DataValidationError

        pipeline = MagicMock()
        pipeline.predict.side_effect = DataValidationError("missing data")
        mock_get_pipeline.return_value = pipeline

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_prediction_error(self, mock_get_pipeline):
        from learngaugeapis.views.predict import PredictionError

        pipeline = MagicMock()
        pipeline.predict.side_effect = PredictionError("shap error")
        mock_get_pipeline.return_value = pipeline

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_unexpected_error(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(predict=MagicMock(side_effect=RuntimeError("boom")))

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# analyze_class
# ---------------------------------------------------------------------------

class AnalyzeClassTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PredictView.as_view({"post": "analyze_class"})

    def _post(self, body=None):
        if body is None:
            body = {
                "subject_id": "INF0823",
                "lecturer_id": "90316",
                "clo_scores": {"19050001": 4.2, "19050002": 3.8},
            }
        request = self.factory.post("/predict/class", body, format="json")
        return self.view(request)

    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_success_with_dict(self, mock_get_pipeline):
        pipeline = MagicMock(analyze_class_from_scores=MagicMock(return_value=_make_analyze_output()))
        mock_get_pipeline.return_value = pipeline

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_students", response.data["data"])
        pipeline.analyze_class_from_scores.assert_called_once_with(
            subject_id="INF0823",
            lecturer_id="90316",
            clo_scores={"19050001": 4.2, "19050002": 3.8},
        )

    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_success_with_list(self, mock_get_pipeline):
        pipeline = MagicMock(analyze_class_from_scores=MagicMock(return_value=_make_analyze_output()))
        mock_get_pipeline.return_value = pipeline

        response = self._post(body={
            "subject_id": "INF0823",
            "lecturer_id": "90316",
            "clo_scores": [4.2, 3.8, 5.1],
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        _, kwargs = pipeline.analyze_class_from_scores.call_args
        self.assertEqual(kwargs["clo_scores"], [4.2, 3.8, 5.1])

    def test_analyze_class_invalid_body_returns_400(self):
        response = self._post(body={"subject_id": "INF0823"})  # missing fields

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analyze_class_empty_clo_scores_returns_400(self):
        response = self._post(body={
            "subject_id": "INF0823",
            "lecturer_id": "90316",
            "clo_scores": {},
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analyze_class_invalid_clo_scores_type_returns_400(self):
        response = self._post(body={
            "subject_id": "INF0823",
            "lecturer_id": "90316",
            "clo_scores": "not a dict or list",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_pipeline_not_initialized(self, mock_get_pipeline):
        mock_get_pipeline.return_value = None

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_data_validation_error(self, mock_get_pipeline):
        from learngaugeapis.views.predict import DataValidationError

        pipeline = MagicMock()
        pipeline.analyze_class_from_scores.side_effect = DataValidationError("missing")
        mock_get_pipeline.return_value = pipeline

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_unexpected_error(self, mock_get_pipeline):
        pipeline = MagicMock()
        pipeline.analyze_class_from_scores.side_effect = RuntimeError("boom")
        mock_get_pipeline.return_value = pipeline

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# train
# ---------------------------------------------------------------------------

class TrainTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PredictView.as_view({"post": "train"})

    def _post(self):
        request = self.factory.post("/predict/train")
        request.user = MagicMock(id=1)
        return self.view(request)

    @patch("learngaugeapis.views.predict.threading.Thread")
    @patch("learngaugeapis.views.predict.config")
    def test_train_starts_background_thread(self, mock_config, mock_thread_cls):
        mock_config.side_effect = lambda key, default=None: (
            "/models/model.joblib" if key == "ML_MODEL_PATH" else "/data"
        )
        mock_thread_instance = MagicMock()
        mock_thread_cls.return_value = mock_thread_instance

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_thread_instance.start.assert_called_once()

    @patch("learngaugeapis.views.predict.config")
    def test_train_missing_config_returns_400(self, mock_config):
        mock_config.return_value = None

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
