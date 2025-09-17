from rest_framework import serializers

from learngaugeapis.models.exam_result import ExamResult

class ExamResultSerializer(serializers.ModelSerializer):
    metadata = serializers.SerializerMethodField()
    class Meta:
        model = ExamResult
        fields = '__all__'

    def get_metadata(self, obj: ExamResult):
        max_score = 10 * obj.exam.clo_type.weight
        actual_score = (obj.total_correct_easy_questions + obj.total_correct_medium_questions)*0.25
        score_on_scale_10 = actual_score / max_score * 10 if max_score != 0 else 0
        letter_grade = "A" if score_on_scale_10 >= 8.5 else "B" if score_on_scale_10 >= 7 else "C" if score_on_scale_10 >= 5.5 else "D" if score_on_scale_10 >= 4 else "F"

        return {
            "max_score": max_score,
            "actual_score": actual_score,
            "score_on_scale_10": score_on_scale_10,
            "letter_grade": letter_grade
        }