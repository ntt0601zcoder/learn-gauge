from rest_framework import serializers

from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.models.course_class import Class
from learngaugeapis.models.exam import Exam
from learngaugeapis.models.clo_type import CLOType
from learngaugeapis.serializers.exam_result import ExamResultSerializer

class ExamSerializer(serializers.ModelSerializer):
    exam_results = ExamResultSerializer(many=True, read_only=True)
    class Meta:
        model = Exam
        fields = '__all__'

class CreateExamSerializer(serializers.Serializer):
    course_class = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None))
    name = serializers.CharField()
    description = serializers.CharField()
    clo_type = serializers.PrimaryKeyRelatedField(queryset=CLOType.objects.filter(deleted_at=None))
    exam_format = serializers.ChoiceField(choices=ExamFormat.all())
    chapters = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=100))
    
class UpdateExamSerializer(serializers.Serializer):
    course_class = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None), required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    clo_type = serializers.PrimaryKeyRelatedField(queryset=CLOType.objects.filter(deleted_at=None), required=False)
    exam_format = serializers.ChoiceField(choices=ExamFormat.all(), required=False)
    chapters = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=100), required=False)