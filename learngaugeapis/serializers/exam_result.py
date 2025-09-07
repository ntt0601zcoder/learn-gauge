from rest_framework import serializers

from learngaugeapis.models.exam_result import ExamResult

class ExamResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamResult
        fields = '__all__'