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


def _mock_exam_qs(exists=True, card_id="90316"):
    """Return a mock QuerySet for ExamResult."""
    qs = MagicMock()
    qs.exists.return_value = exists
    first = MagicMock()
    first.exam.course_class.teacher.card_id = card_id
    qs.first.return_value = first
    return qs


def _mock_exam_qs_with_metrics(rows):
    """Return an iterable mock QuerySet with annotated actual_score rows."""
    qs = MagicMock()
    qs.exists.return_value = bool(rows)
    qs.__iter__ = MagicMock(return_value=iter(rows))
    return qs


# ---------------------------------------------------------------------------
# predict_student
# ---------------------------------------------------------------------------

class PredictStudentTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PredictView.as_view({"get": "predict_student"})

    def _get(self, subject_code="INF0823", student_code="19050006"):
        request = self.factory.get(f"/predict/subject/{subject_code}/student/{student_code}")
        return self.view(request, subject_code=subject_code, student_code=student_code)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_success(self, mock_get_pipeline, mock_exam_result):
        mock_get_pipeline.return_value = MagicMock(predict=MagicMock(return_value=_make_predict_output()))
        mock_exam_result.objects.filter.return_value = _mock_exam_qs()

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("predicted_clo_score", response.data["data"])
        mock_get_pipeline.return_value.predict.assert_called_once_with(
            student_id="19050006",
            subject_id="INF0823",
            lecturer_id="90316",
        )

    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_pipeline_not_initialized(self, mock_get_pipeline):
        mock_get_pipeline.return_value = None

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_not_found(self, mock_get_pipeline, mock_exam_result):
        mock_get_pipeline.return_value = MagicMock()
        mock_exam_result.objects.filter.return_value = _mock_exam_qs(exists=False)

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_data_validation_error(self, mock_get_pipeline, mock_exam_result):
        from learngaugeapis.views.predict import DataValidationError

        pipeline = MagicMock()
        pipeline.predict.side_effect = DataValidationError("missing data")
        mock_get_pipeline.return_value = pipeline
        mock_exam_result.objects.filter.return_value = _mock_exam_qs()

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_prediction_error(self, mock_get_pipeline, mock_exam_result):
        from learngaugeapis.views.predict import PredictionError

        pipeline = MagicMock()
        pipeline.predict.side_effect = PredictionError("shap error")
        mock_get_pipeline.return_value = pipeline
        mock_exam_result.objects.filter.return_value = _mock_exam_qs()

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.get_predict_pipeline")
    def test_predict_student_unexpected_error(self, mock_get_pipeline, mock_exam_result):
        mock_get_pipeline.return_value = MagicMock(predict=MagicMock(side_effect=RuntimeError("boom")))
        mock_exam_result.objects.filter.return_value = _mock_exam_qs()

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------------
# analyze_class
# ---------------------------------------------------------------------------

class AnalyzeClassTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = PredictView.as_view({"get": "analyze_class"})

    def _get(self, subject_code="INF0823", class_id="1"):
        request = self.factory.get(f"/predict/subject/{subject_code}/class/{class_id}/analyze")
        return self.view(request, subject_code=subject_code, class_id=class_id)

    def _mock_class(self, card_id="90316"):
        course_class = MagicMock()
        course_class.teacher.card_id = card_id
        return course_class

    def _make_result_row(self, student_code, actual_score):
        row = MagicMock()
        row.student_code = student_code
        row.actual_score = actual_score
        return row

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.Class")
    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_success(self, mock_get_pipeline, mock_class, mock_exam_result):
        pipeline = MagicMock(analyze_class_from_scores=MagicMock(return_value=_make_analyze_output()))
        mock_get_pipeline.return_value = pipeline
        mock_class.objects.select_related.return_value.get.return_value = self._mock_class()

        rows = [
            self._make_result_row("19050001", 4.2),
            self._make_result_row("19050002", 3.8),
        ]
        qs_with_metrics = _mock_exam_qs_with_metrics(rows)
        mock_exam_result.objects.filter.return_value.with_metrics.return_value = qs_with_metrics

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_students", response.data["data"])
        pipeline.analyze_class_from_scores.assert_called_once_with(
            subject_id="INF0823",
            lecturer_id="90316",
            clo_scores={"19050001": 4.2, "19050002": 3.8},
        )

    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_pipeline_not_initialized(self, mock_get_pipeline):
        mock_get_pipeline.return_value = None

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("learngaugeapis.views.predict.Class")
    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_class_not_found(self, mock_get_pipeline, mock_class):
        mock_get_pipeline.return_value = MagicMock()
        mock_class.objects.select_related.return_value.get.side_effect = mock_class.DoesNotExist

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.Class")
    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_no_exam_results(self, mock_get_pipeline, mock_class, mock_exam_result):
        mock_get_pipeline.return_value = MagicMock()
        mock_class.objects.select_related.return_value.get.return_value = self._mock_class()
        mock_exam_result.objects.filter.return_value.with_metrics.return_value = (
            _mock_exam_qs_with_metrics([])
        )

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("learngaugeapis.views.predict.ExamResult")
    @patch("learngaugeapis.views.predict.Class")
    @patch("learngaugeapis.views.predict.get_analysis_pipeline")
    def test_analyze_class_aggregates_multiple_exams_per_student(
        self, mock_get_pipeline, mock_class, mock_exam_result
    ):
        """A student with two exams should have their scores summed."""
        pipeline = MagicMock(analyze_class_from_scores=MagicMock(return_value=_make_analyze_output()))
        mock_get_pipeline.return_value = pipeline
        mock_class.objects.select_related.return_value.get.return_value = self._mock_class()

        rows = [
            self._make_result_row("19050001", 2.0),
            self._make_result_row("19050001", 1.5),  # second exam, same student
        ]
        mock_exam_result.objects.filter.return_value.with_metrics.return_value = (
            _mock_exam_qs_with_metrics(rows)
        )

        self._get()

        _, kwargs = pipeline.analyze_class_from_scores.call_args
        self.assertAlmostEqual(kwargs["clo_scores"]["19050001"], 3.5)


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
