from rest_framework import serializers


class PredictStudentSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    subject_id = serializers.CharField()
    lecturer_id = serializers.CharField()


class AnalyzeClassSerializer(serializers.Serializer):
    subject_id = serializers.CharField()
    lecturer_id = serializers.CharField()
    # Hỗ trợ 3 dạng theo guideline ml_clo:
    #   dict {student_id: score}
    #   list [score, score, ...]
    #   list [[student_id, score], ...]
    clo_scores = serializers.JSONField()

    def validate_clo_scores(self, value):
        if isinstance(value, dict):
            if not value:
                raise serializers.ValidationError("clo_scores không được rỗng")
            return value
        if isinstance(value, list):
            if not value:
                raise serializers.ValidationError("clo_scores không được rỗng")
            return value
        raise serializers.ValidationError(
            "clo_scores phải là dict {student_id: score} hoặc list điểm"
        )
