from rest_framework import serializers

from learngaugeapis.const.clo_types import CLOType
from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.models.course_class import Class
from learngaugeapis.models.exam import Exam

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'

class CreateExamSerializer(serializers.Serializer):
    class_id = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None))
    name = serializers.CharField()
    description = serializers.CharField()
    clo_type = serializers.ListField(child=serializers.ChoiceField(choices=CLOType.all()))
    exam_format = serializers.ChoiceField(choices=ExamFormat.all())
    chapters = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=100))
    
class UpdateExamSerializer(serializers.Serializer):
    class_id = serializers.PrimaryKeyRelatedField(queryset=Class.objects.filter(deleted_at=None), required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    clo_type = serializers.ListField(child=serializers.ChoiceField(choices=CLOType.all()), required=False)
    exam_format = serializers.ChoiceField(choices=ExamFormat.all(), required=False)
    chapters = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=100), required=False)