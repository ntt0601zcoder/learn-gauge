from rest_framework import serializers

from learngaugeapis.models.essay_exam_result import EssayExamResult

class EssayExamResultSerializer(serializers.ModelSerializer):
    metadata = serializers.SerializerMethodField()
    class Meta:
        model = EssayExamResult
        fields = '__all__'

    def get_metadata(self, obj: EssayExamResult):
        return None