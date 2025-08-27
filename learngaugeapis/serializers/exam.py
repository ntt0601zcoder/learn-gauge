from rest_framework import serializers

from learngaugeapis.const.clo_types import CLOType
from learngaugeapis.const.exam_formats import ExamFormat
from learngaugeapis.models.course import Course
from learngaugeapis.models.exam import Exam

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'

class CreateExamSerializer(serializers.Serializer):
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None))
    name = serializers.CharField()
    description = serializers.CharField()
    clo_type = serializers.ChoiceField(choices=CLOType.all())
    exam_format = serializers.ChoiceField(choices=ExamFormat.all())
    chapters = serializers.ListField(child=serializers.IntegerField())
    
    def validate_chapters(self, value):
        for chapter in value:
            if chapter < 1:
                raise serializers.ValidationError("Chapter number must be greater than 0")
        return value

class UpdateExamSerializer(serializers.Serializer):
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.filter(deleted_at=None), required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    clo_type = serializers.ChoiceField(choices=CLOType.all(), required=False)
    exam_format = serializers.ChoiceField(choices=ExamFormat.all(), required=False)
    chapters = serializers.ListField(child=serializers.IntegerField(), required=False)

    def validate_chapters(self, value):
        if value is not None:
            for chapter in value:
                if chapter < 1:
                    raise serializers.ValidationError("Chapter number must be greater than 0")
        return value